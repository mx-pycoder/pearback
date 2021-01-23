#!/usr/bin/env python3

''' _pearback.py - module to interact with iOS 5+ backups

Copyright (c) 2017 Marnix Kaart

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

# TODO: replace generic exceptions with PearBackError derived
#       exceptions where appropriate
# TODO: early abort in diff function as soon as first difference is
#       detected, instead of always hashing full contents


import sqlite3
import plistlib as _plistlib
from collections import namedtuple as _nt
from collections import OrderedDict as _OD
from enum import Enum as _Enum
from binascii import hexlify as _hexlify
from datetime import datetime as _datetime
from time import gmtime as _gmtime
from pytz import UTC as _UTC
from functools import partial as _partial
import os as _os
import shutil as _shutil
from collections import Counter as _Counter
from hashlib import sha256 as _sha256
from hashlib import sha1 as _sha1


###########
# classes #
###########


class FileType(_Enum):
    ''' Enum indicating type of file entry

    Note: only symlinks, regular files and directories are in iOS backup '''

    Symlink = 40960
    RegularFile = 32768
    Directory = 16384


class BackupType(_Enum):
    ''' Enum to indicate the type of backup '''

    IOS5TO9 = 1
    IOS10 = 2


class PearBackError(Exception):
    ''' basic error for this module '''
    pass


class PlistParseError(PearBackError):
    ''' raised when some error occurs while parsing plists '''
    pass


class ExtractError(PearBackError):
    ''' raised when extraction fails for some reason '''
    pass


class MbdbParseError(PearBackError):
    ''' raised when parsing of older Manifest.mbdb fails '''
    pass


# instead of defining full classes, I use namedtuples for simplicity

# a backup object consists of rootdir, connection to Manifest.db (None when
# dealing with backups from devices with iOS9 or below), parsed
# status.plist and manifest.plist and a partial generator function for
# iterating over parsed file-records from Manifest.db
_backup = _nt('iOSbackup', 'backuptype rootdir db status manifest filerecords')


# a simple object for representing a single entry in the Files table
_file_entry = _nt('file_entry', 'fileID domain relativePath uid gid '
                                'mtime ctime btime inode mode filetype '
                                'permissions size protection '
                                'extended_attributes linktarget digest')


# namedtuple for representing the values in the plist in the file field in iOS10
# Manifest.db databases
_plistvals = _nt('plist_values', 'uid gid mtime ctime btime inode mode '
                                 'filetype permissions size protection '
                                 'relpath extended_attributes linktarget '
                                 'digest')


# expected toplevel fields in the file plist in iOS10 Manifest.db databases
_known_plist_keys = set(['$version', '$top', '$objects', '$archiver'])


#######
# API #
#######


def load_backup(filepath):
    ''' load backup from given filepath and return a simple backup object '''

    # find the absolute path of the backup directory
    rootdir = _os.path.abspath(_os.path.expanduser(filepath))

    # determine type of backup
    backuptype = _checkdir(rootdir)

    status = _read_status_plist(_os.path.join(rootdir, 'Status.plist'))
    manifest = _read_manifest_plist(_os.path.join(rootdir, 'Manifest.plist'))

    if backuptype == BackupType.IOS10:
        db = _opendb(_os.path.join(filepath,'Manifest.db'))
        filerecords = _partial(_db_file_records, db)
    elif backuptype == BackupType.IOS5TO9:
        mbdb = _open_mbdb(_os.path.join(filepath,'Manifest.mbdb'))
        filerecords = _partial(_parse_mbdb, mbdb)
        db = None
    else:
        raise PearBackError('unknown backup type')

    return _backup(backuptype, rootdir, db, status, manifest, filerecords)


def print_status(backup, header=True, sep=None):
    ''' prints the contents of Status.plist of the given backup object '''

    if header is True:
        print("Status.plist")
        print("============")
    for field in sorted(backup.status._fields):
        val = getattr(backup.status, field)
        if isinstance(val, _datetime):
            val = val.isoformat()
        if sep is None:
            print("{:25s} {:s}".format(field, str(val)))
        else:
            print("{:s}{:s}{:s}".format(field, sep, str(val)))


def print_manifest(backup, header=True, sep=None):
    ''' prints a summary of Manifest.plist of the given backup object '''

    if header is True:
        print("Manifest.plist")
        print("==============")

    toprint={}
    for field in sorted(backup.manifest._fields):
        val = getattr(backup.manifest, field)
        if field == "Lockdown":
            for subname, subval in val.items():
                if isinstance(subval, dict):
                    # skip the nested dicts
                    continue
                toprint[subname] = subval
            continue
        elif isinstance(val, dict):
            field = "#"+field
            val = len(val)
# .Data is deprecated
        elif isinstance(val, bytes):
           continue
        elif isinstance(val, _datetime):
            val = val.isoformat()
        toprint[field] = val

    for k in sorted(toprint.keys()):
        if sep is None:
            print("{:25s} {:15s}".format(k, str(toprint[k])))
        else:
            print("{:s}{:s}{:s}".format(k, sep, str(toprint[k])))


def print_filerecords(filerecs, sep='\t', headers=True, fields=None):
    ''' prints the given sequence of filerecords

    NOTE: the first argument is a sequence of filerecords, and not the
    entire backup object, so you can limit the type of records to print. For
    example if you only want to print records related to WhatsApp:

    >>> g = backup.filerecords()
    >>> g = filter(lambda r: "WhatsApp" in r.domain, g)
    >>> print_filerecords(g)

    '''

    if fields is not None:
        cols = [f for f in fields if f in _file_entry._fields]
    else:
        cols = [f for f in _file_entry._fields]

    # do not include extended attributes, this can mess with separators and
    # produces a lot of extra data for some files
    cols = [c for c in cols if not c=='extended_attributes']

    if headers is True:
       print(sep.join(cols))

    for f in filerecs:
        vals = [getattr(f, col) for col in cols]
        vals = [val.isoformat() if isinstance(val, _datetime) else val for val in vals]
        vals = [str(val) if isinstance(val, int) else val for val in vals]
        vals = [str(val) if isinstance(val, FileType) else val for val in vals]
        vals = ['' if val is None else val for val in vals]
        # extended attributes are in a dict, convert to string
        # vals = [str(val) if isinstance(val, dict) else val for val in vals]
        print(sep.join(vals))


def extract_files(backuptype, filerecords, rootdir, outdir, hardlink=False):
    ''' extract filerecords to outdir (using hardlinks if hardlink is True) '''

    outdir = _checkout(outdir)

    for f in filerecords:
        if f.filetype == FileType.Symlink:
            # skip symlinks for now, they can also point to absolute paths on
            # original filesystem (i.e. /private/var/mobile/...)
            #_os.symlink(f.linktarget, target)
            continue

        # split the domain into domain, subdomain
        domain = f.domain.split('-', 1)
        if len(domain) == 1:
            target = _os.path.join(outdir, domain[0], f.relativePath)
        else:
            target = _os.path.join(outdir, domain[0], domain[1], f.relativePath)

        if f.filetype == FileType.Directory:
            if _os.path.exists(target):
                if not _os.path.isdir(target):
                    raise ExtractError('target exists but is not a directory: {:s}'.format(target))
            else:
                _os.makedirs(target, mode=0o750)

        elif f.filetype == FileType.RegularFile:
            # the parentdir is not always included in the sequence of filerecords
            parentdir, child = _os.path.split(target)
            if _os.path.exists(parentdir):
                if not _os.path.isdir(parentdir):
                    raise ExtractError('parentdir is not a directory: {:s}'.format(parentdir))
            else:
                _os.makedirs(parentdir, mode=0o750)

            if f.size == 0:
                # create empty file
                _os.mknod(target)
            else:
                if backuptype.value == BackupType.IOS10.value:
                    source = _os.path.join(rootdir, f.fileID[0:2], f.fileID)
                elif backuptype.value == BackupType.IOS5TO9.value:
                    source = _os.path.join(rootdir, f.fileID)
                else:
                    raise ValueError('unknown backuptype in extract function')

                if hardlink is True:
                    _os.link(source, target)
                else:
                    _shutil.copyfile(source, target)


def extract(backup, outdir, hardlink=False, progress=False):
    ''' extract files from given backup to outdir

    if hardlink is True, files will be linked instead of copied '''

    filerecords = backup.filerecords()
    if progress is True:
        if backup.backuptype == BackupType.IOS10:
            total = _db_nr_of_files(backup)
        else:
            filerecords = list(filerecords)
            total = len(filerecords)

        filerecords = _progresswrapper(filerecords, 'extracting', 'files', total)

    extract_files(backup.backuptype, filerecords, backup.rootdir, outdir, hardlink)


def list_all(backup, sep='\t', headers=True):
    ''' list all files in backup '''

    # for API purposes we tolerate a single statement per function
    print_filerecords(backup.filerecords(), sep, headers)


def summarize(backup):
    ''' prints a brief summary on the given backup '''

    print()
    print_manifest(backup)
    print()
    print_status(backup)
    print()
    print("File stats")
    print("==========")
    c = _Counter(r.filetype for r in backup.filerecords())
    for k,v in c.items():
        print("{:25s} {:25s}".format(k, str(v)))


def changed_files(backup1, backup2):
    ''' yield files that are different or only exist in one of the backups.

    Yields file-tuples: (file1, file2)

    If a file exists only in backup1, this will yield (file1, None)
    If a file exists only in backup2, this will yield (None, file2)
    If contents of files differs, both files are yielded: (file1, file2)

    Note that we only compare files with the same domain,relativePath
    properties. Moved or otherwise duplicate files are not considered between
    backups. Also, when the size is different, no actual comparing is done,
    based on the fact that files of different size have different contents by
    definition. '''

    # we are only interested in files
    b1recs = filter(lambda r: r.filetype == FileType.RegularFile, backup1.filerecords())
    b2recs = filter(lambda r: r.filetype == FileType.RegularFile, backup2.filerecords())

    # put filerecords for boths sets in a dictionary by (domain, relativePath)
    b1dict = {(r.domain, r.relativePath):r for r in b1recs}
    b2dict = {(r.domain, r.relativePath):r for r in b2recs}

    b1keys = set(b1dict.keys())
    b2keys = set(b2dict.keys())

    # files that only exist in b1
    for k in b1keys-b2keys:
        yield(b1dict[k], None)

    # files that only exist in b2
    for k in b2keys-b1keys:
        yield(None, b2dict[k])

    # files that exist in both sets
    for k in b1keys.intersection(b2keys):
        f1 = b1dict[k]
        f2 = b2dict[k]
        if f1.size != f2.size:
            # if size differs, so does contents
            yield(f1, f2)
        elif f1.size == 0:
            # both are empty, equal!
            pass
        else:
            # compare by hash
            if backup1.backuptype == BackupType.IOS10:
                d1 = _os.path.join(backup1.rootdir, f1.fileID[0:2], f1.fileID)
            elif backup1.backuptype == BackupType.IOS5TO9:
                d1 = _os.path.join(backup1.rootdir, f1.fileID)
            else:
                raise ValueError('unexpected backuptype')

            s1 = _sha256()
            with open(d1, 'rb') as f:
                s1.update(f.read())
            if backup2.backuptype == BackupType.IOS10:
                d2 = _os.path.join(backup2.rootdir, f2.fileID[0:2], f2.fileID)
            elif backup2.backuptype == BackupType.IOS5TO9:
                d2 = _os.path.join(backup2.rootdir, f2.fileID)
            else:
                raise ValueError('unexpected backuptype')

            s2 = _sha256()
            with open(d2, 'rb') as f:
                s2.update(f.read())
            if s1.digest() != s2.digest():
                yield(f1, f2)


def extract_changed_and_removed_files(backup1, backup2, outdir, hardlink=False):
    ''' extract files from backup1 that are removed or changed in backup 2

    Note that this might not do what you expect. It extract files from
    *backup1* that are no longer present in *backup2* or for which the contents
    have changed in *backup2*. No files from *backup2* will be extracted.

    I use this to extract all files from a previous backup that are no longer
    present with the same contents in the new backup:

    >>> extract_changed_and_removed_files(old_backup, new_backup, outdir, True)

    If you want this the other way around (i.e. extract all files from the
    newer backup that where not yet in the previous backup or have been changed
    since), you can flip the backup1 and backup2 arguments:

    >>> extract_changed_and_removed_files(new_backup, old_backup, outdir, True)
    '''

    diffs = changed_files(backup1, backup2)
    backup1_recs = (f1 for f1,f2 in diffs if f1 is not None)
    extract_files(backup1.backuptype, backup1_recs, backup1.rootdir, outdir, hardlink)


######################
# 'hidden' functions #
######################


def _checkdir(indir):
    ''' check if input dir is an iOS backup directory and returns version. '''

    expected_10plus = ['Info.plist', 'Status.plist', 'Manifest.plist', 'Manifest.db']
    expected_5to9 = ['Info.plist', 'Status.plist', 'Manifest.plist', 'Manifest.mbdb']

    indir = _os.path.expanduser(indir)

    if not _os.path.isdir(indir):
        raise FileNotFoundError('backup directory does not exist!')
    if len(_os.listdir(indir)) == 0:
        raise FileExistsError('backup directory is empty!')

    # first check if this is a backup of a device with iOS10 or above
    missing = set(expected_10plus) - set(_os.listdir(indir))
    if missing == set():
        return BackupType.IOS10

    # then check if this is a backup of a device with iOS5 through 9
    missing = set(expected_5to9) - set(_os.listdir(indir))
    if missing == set():
        return BackupType.IOS5TO9

    raise PearBackError('could not determine backup type')


def _opendb(filepath):
    ''' open file as sqlite3 database, returning db connection object '''
    filepath = _os.path.expanduser(filepath)
    db = sqlite3.connect(filepath)
    return db


def _read_status_plist(statusfile):
    ''' read Status.plist into a simple object.

    Here, the toplevel fields of the plist are converted into namedtuple
    fields. Subfields are left as dictionaries. '''

# deprecated
#    s = _plistlib.readPlist(statusfile)
    with open(statusfile, 'rb') as f:
        s = _plistlib.load(f)

    # only convert toplevel fields into namedtuple fields, since we have
    # encountered names that are not proper Python identifiers in some of the
    # subfields (i.e. start with number or underscore) and I do not want to
    # mangle those names.
    keys = sorted(s.keys())
    vals = [s[k] for k in keys]
    status = _nt('status', ' '.join(keys))(*vals)
    return status


def _read_manifest_plist(manifestplist):
    ''' read Manifest.plist into a simple object.

    Here, the toplevel fields of the plist are converted into namedtuple
    fields. Subfields are left as dictionaries. '''

# deprecated
#    m = _plistlib.readPlist(manifestplist)
    with open(manifestplist, 'rb') as f:
        m = _plistlib.load(f)

    # here too, only convert toplevel fields into namedtuple fields
    keys = sorted(m.keys())
    vals = [m[k] for k in keys]
    manifest = _nt('manifest', ' '.join(keys))(*vals)
    return manifest


def _db_file_records(db):
    ''' yield all records from the Files table as namedtuples '''

    # perform the query
    q = '''SELECT * FROM Files'''
    c = db.cursor().execute(q)

    # check if columns match what we expect
    colnames = list(zip(*c.description))[0]
    # we expect the following columns in the Files table
    _expected_filerec = ('fileID', 'domain', 'relativePath', 'flags', 'file')
    if colnames != _expected_filerec:
        raise ValueError('Unexpected table layout for Files table')

    # create a namedtuple for the unprocessed file records for convenience
    record = _nt('file', ' '.join(colnames))

    for r in c:
        r = record(*r)
        # the file column contains a plist that needs additional parsing
        p = _db_parse_file_column(r.file)
        # relativePath should match
        if p.relpath != r.relativePath:
            raise ValueError('relativePath mismatch!')

        # the value in the flags field always seems to correspond to the
        # filetype when derived from the mode field (1 = RegularFile,
        # 2=Directory, 3=Symlink). Test this here and abort if this assumption
        # is broken.
        if (r.flags == 1 and p.filetype != FileType.RegularFile):
            raise ValueError('assumption broken on flags field')
        elif (r.flags == 2 and p.filetype != FileType.Directory):
            raise ValueError('assumption broken on flags field')
        elif (r.flags == 4 and p.filetype != FileType.Symlink):
            raise ValueError('assumption broken on flags field')

        yield _file_entry(r.fileID, r.domain, r.relativePath,
                          p.uid, p.gid, p.mtime, p.ctime, p.btime, p.inode,
                          p.mode, p.filetype, p.permissions, p.size,
                          p.protection, p.extended_attributes, p.linktarget,
                          p.digest)


def _db_parse_file_column(bytes_):
    ''' parse the plist in the file column of the Files table of iOS10+ backups '''

    # NOTE: using biplist is not needed anymore, substituted by plistlib
    p = _plistlib.loads(bytes_)

    # check if we have the same fields as in our reference sample
    if set(p.keys()) != _known_plist_keys:
        raise PlistParseError('someting in file column of Files table in Manifest.db changed')

    # we have only seen backups where $version, $archiver and $top have fixed
    # values, so raise exception when we hit some other value
    version = p.get('$version')
    if version != 100000:
        raise PlistParseError('$version != 100000')
    archiver = p.get('$archiver')
    if archiver != 'NSKeyedArchiver':
        raise PlistParseError('$archiver != NSKeyedArchiver')
    root_uid = p.get('$top').get('root')
    if root_uid.data != 1:
        raise PlistParseError("$top['root'] != Uid(1)")

    # the interesting data is in the $objects field
    objects = p.get('$objects')
    # first field is expected to be $null
    if objects[0] != '$null':
        raise PlistParseError("$objects[0] != $null")

    # check if we have any new types of of fields
    #if len(set(objects[1].keys()) - _known_object_keys) != 0:
    #    raise PlistParseError("$objects[1] fields do not match known fields: {:s}".format(str(objects[1].keys())))

    uid = objects[1].get('UserID')
    # contents modification time
    mtime = _datetime(*list(_gmtime(objects[1].get('LastModified'))[0:7])+[_UTC])
    inode = objects[1].get('InodeNumber')
    mode = objects[1].get('Mode')
    # determine filetype and permissions based on mode
    filetype = FileType(mode & 0xE000)
    permissions = oct(mode & 0x1FFF)
    # metadata-change time
    ctime = _datetime(*list(_gmtime(objects[1].get('LastStatusChange'))[0:7])+[_UTC])
    gid = objects[1].get('GroupID')
    # birth-time (aka creation time)
    btime = _datetime(*list(_gmtime(objects[1].get('Birth'))[0:7])+[_UTC])
    size = objects[1].get('Size')
    # not sure what this is
    protection = objects[1].get('ProtectionClass')

    # apparently since iOS11 the plist includes a field 'Flags' in the plist
    # field as well, but I've only seen value 0 in my backups
    if objects[1].get('Flags', 0) != 0:
#        raise PearBackError('assumption on plist flags field broken')
        print("skipping non-zero plist flags field")

    # the Uid stored in 'RelativePath' seems to point to index in 'objects'
    # where the actual value is stored. The Uid.data property gives the
    # integer value
    relpath = objects[objects[1].get('RelativePath').data]

    # something similar for the '$class', which seems to be 'MBFile' always
    class_= objects[objects[1].get('$class').data].get('$classname')
    if class_ != 'MBFile':
        raise PlistParseError('assumption broken: $class is not always MBFile')

    # extended attributes are not always present, but if they are, they seem to
    # be pointed to by the UID value in the 'ExtendedAttributes' fields. The
    # target item then contains a bplist with key-value pairs under the key
    # 'NS.data'
    if 'ExtendedAttributes' in objects[1]:
        ea_idx = objects[1]['ExtendedAttributes'].data
        if isinstance(objects[ea_idx], bytes):
            # load dict from binary plist
            extended_attributes = _plistlib.loads(objects[ea_idx], fmt=_plistlib.FMT_BINARY, dict_type=dict)
        else:
            # normal dict after NS.data
            extended_attributes = _plistlib.loads(objects[ea_idx].get('NS.data'))
    else:
        extended_attributes = None

    # target is only available when type is a symlink and its value indicates
    # the index of the property in the $objects field
    if filetype == FileType.Symlink:
        if 'Target' not in objects[1]:
            raise PlistParseError('Assumption broken on symlinks')
        tgt_idx = objects[1]['Target'].data
        linktarget = objects[tgt_idx]
    else:
        linktarget = None

    # digest is also not always present, it works similar as above two fields,
    # let's store hex string instead of bytes
    if 'Digest' in objects[1]:
        d_idx = objects[1]['Digest'].data
        digest = objects[d_idx]
        if type(digest) == dict:
            digest = digest['NS.data']
            digest = _hexlify(digest).decode()
        else:
            digest = _hexlify(digest).decode()
    else:
        digest = None

    # convert to our named tuple and return object
    return _plistvals(uid, gid, mtime, ctime, btime, inode, mode,
                      filetype, permissions, size, protection, relpath,
                      extended_attributes, linktarget, digest)


def _checkout(outdir):
    ''' check if output directory exists and is empty '''

    outdir = _os.path.expanduser(outdir)

    if not _os.path.isdir(outdir):
        raise FileNotFoundError('output directory does not exist!')
    if len(_os.listdir(outdir)) != 0:
        raise FileExistsError('output directory is not empty!')

    return outdir


def _progresswrapper(sequence, desc=None, unit='files', total=None):
    ''' a simple wrapper that prints a progressbar on iteration (using tqdm)

    You need the tqdm module in order to make this work. If you don't have it
    the situation will be handled gracefully.
    '''

    try:
        from tqdm import tqdm as _tqdm
    except:
        return sequence

    # if we have a generator, convert to list to know number of iterations
    if total is None:
        sequence = list(sequence)

    sequence = _tqdm(sequence, desc=desc, unit=' {:s}'.format(unit),
                     leave=True, ncols=80, total=total)
    return sequence


def _db_nr_of_files(backup):
    ''' return total number of Files in Manifest.db '''

    c = backup.db.cursor().execute('SELECT count(*) FROM Files')
    return c.fetchall()[0][0]


def _open_mbdb(filepath):
    ''' opens Manifest.mbdb file '''

    filepath = _os.path.expanduser(filepath)
    # just read entire file into bytes object
    with open(filepath, 'rb') as f:
        mbdb = f.read()

    if mbdb[0:4].decode('utf8') != 'mbdb':
        raise MbdbParseError('{:s} is not a mbdb file'.format(filepath))
    if int.from_bytes(mbdb[4:6], 'big') != 0x500:
        raise MbdbParseError('unexpected value encountered in Manifest.mbdb')

    return mbdb


def _parse_mbdb(mbdb):
    ''' yields file_entry objects from given mbdn array '''
    size = len(mbdb)
    pos = 6
    while pos < size:
        entry, newpos = _parse_mbdb_entry(mbdb, pos)
        pos = newpos
        yield entry


def _parse_mbdb_entry(mbdb, pos):
    ''' parse a single entry in the mbdb file '''

    offset = pos
    domain, pos = _mbdb_string(mbdb, pos)
    filename, pos = _mbdb_string(mbdb, pos)
    linktarget, pos = _mbdb_string(mbdb, pos)
    # a simple test (N=1, scientific is it not?) shows that what is commonly
    # called 'datahash' in the scripts I used as basis for this, is stored in a
    # value that is called 'digest' in the newer (iOS10+) backups. So, we call
    # this 'digest' here as well.
    digest, pos = _mbdb_string(mbdb, pos)
    # this is commonly called enckey in the scripts that I used as source, but
    # in my backups it is consistently an empty string. So assume that it is,
    # break if it isn't.
    unknown, pos = _mbdb_string(mbdb, pos)
    if unknown != '':
        raise MbdbParseError('assumption broken on empty string in unknown field')

    mode = int.from_bytes(mbdb[pos:pos+2], 'big')
    pos+=2
    inode = int.from_bytes(mbdb[pos:pos+8], 'big')
    pos+=8
    uid = int.from_bytes(mbdb[pos:pos+4], 'big')
    pos+=4
    gid = int.from_bytes(mbdb[pos:pos+4], 'big')
    pos+=4
    # some sources that I based this function on had a different
    # order for these timestamps and in addition instead of a
    # btime assumed an atime, which I think is incorrect based on some simple
    # experiments (comparing timestamps on a rooted phone with backup
    # timestamps).
    mtime = _datetime(*list(_gmtime(int.from_bytes(mbdb[pos:pos+4], 'big'))[0:7])+[_UTC])
    pos+=4
    ctime = _datetime(*list(_gmtime(int.from_bytes(mbdb[pos:pos+4], 'big'))[0:7])+[_UTC])
    pos+=4
    btime = _datetime(*list(_gmtime(int.from_bytes(mbdb[pos:pos+4], 'big'))[0:7])+[_UTC])
    pos+=4
    size = int.from_bytes(mbdb[pos:pos+8], 'big')
    pos+=8
    # Based on the different values I've encountered in the field that is
    # commonly called 'flags' in the scripts that I've used as source it would
    # seem that this is what is called 'protection' in the newer backups.
    # Perhaps these values represent some enum value of the protection level.
    # So, I've called this field 'protection' in contrast to the other scripts
    # out there.
    protection = int.from_bytes(mbdb[pos:pos+1], 'big')
    pos+=1
    numprops = int.from_bytes(mbdb[pos:pos+1], 'big')
    pos+=1

    # determine filetype and permissions based on mode
    filetype = FileType(mode & 0xE000)
    permissions = oct(mode & 0x1FFF)

    extended_attributes = _OD()
    for ii in range(numprops):
        pname, pos = _mbdb_string(mbdb, pos)
        pval, pos = _mbdb_string(mbdb, pos)
        extended_attributes[pname] = pval

    # the fileID was originally stored in a separate mbdx file, but we can also
    # determine this by combining the domain and filepath and calculating sha1
    # hash over it
    fileID = _sha1('{:s}-{:s}'.format(domain, filename).encode('utf8')).hexdigest()

    return _file_entry(fileID, domain, filename,
                       uid, gid, mtime, ctime, btime, inode,
                       mode, filetype, permissions, size,
                       protection, extended_attributes, linktarget,
                       digest), pos


def _mbdb_string(mbdb, pos):
    ''' parse a string from the mbdb file.

    The string length is encoded in 2 bytes prior to the string. If the length
    is 0xffff, this indicates an empty string. The string is decoded as uft 8
    and if that fails, the bytes are returned as hexstring. '''

    size = int.from_bytes(mbdb[pos:pos+2],'big')
    if size == 65535:
        return '', pos+2
    else:
        val = mbdb[pos+2:pos+2+size]
        try:
            val = val.decode('utf8')
        except:
            val = _hexlify(val).decode('utf8')
        return val, pos+2+size



