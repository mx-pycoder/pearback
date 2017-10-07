# pearback

Pearback is a python module to work with iOS backups. Backups from devices
running iOS 5 through 11 are supported. Pearback can be used as a library in
other projects, or as a command-line tool for interacting with backups.

Pearback was written for my personal use in order to take the manual labour out
of managaging backups of the couple of iOS devices that we keep around the
house. But I hope it will be useful for you as well!

## warning

This is still experimental. At the time of this writing, I'm testing it on the
various iOS devices I have available. I take no responsibilty if you decide to
use this software and if anything goes wrong (see LICENCE). But if you do
decide to try it and find any problems or issues, it is appreciated if you
report them.

Also note that this has been written and tested on a Linux machine, it may or
may not work on Windows. I did not test this.

## what it does

When used as a module in other projects, pearback provides you with a
consistent interface to the backup, regardless of whether the backup uses a
Manifest.mbdb file (iOS 5 through 9) or a Manifest.db file (iOS 10 and 11)
internally.

As a tool, you can choose between three operating modes: extract, info and
diff. In extract mode, you can extract all files a given backup to an output
directory by either copying or hard-linking to the original backup. In info
mode, you can get some basic information on the backup or you can list all
metadata of all files in the backup. In diff mode, you can compare two backups
and either show, or extract the differences between them.

Pearback comes with a script called backup.sh, which can be used to create
backups from an iOS device in a structured manner (see requirements below).
Each time a new backup is created, it is compared to the previous backup and
all files that have changed or have been removed are preserved in a separate
directory. This gives the user the option to check the preserved file for any
important data that the user want's to keep.

## example usage

Pearback can be used as a python module, or as a standalone tool. Both use
cases are briefly demonstrated here.


### using pearback as a module

Start by opening an iOS backup and printing some details about it. Note that
for privacy reasons I have changed some values in output below.

```
>>> import pearback
>>> b1 = pearback.load_backup('~/ios_backups/new_backup/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/')
>>> pearback.summarize(b1)

Manifest.plist
==============
#Applications             307
BuildVersion              15A421
Date                      2017-05-23T06:58:57.004993
DeviceName                xxxxxxxxxxx
IsEncrypted               False
ProductType               iPhone6,2
ProductVersion            11.0.2
SerialNumber              xxxxxxxxxxxx
SystemDomainsVersion      24.0
UniqueDeviceID            xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Version                   10.0
WasPasscodeSet            True

Status.plist
============
BackupState               new
Date                      2017-10-06T22:36:38.706502
IsFullBackup              False
SnapshotState             finished
UUID                      xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Version                   3.2

File stats
==========
FileType.RegularFile      12293
FileType.Symlink          9
FileType.Directory        6620
```

The backup object is simply a namedtuple with some fields containing the
information stored in the various metadata files associated with an iOS backup.

```
>>> b1._fields
('backuptype', 'rootdir', 'db', 'status', 'manifest', 'filerecords')
>>> b1.backuptype
<BackupType.IOS10: 2>
>>> b1.rootdir
'/home/testuser/ios_backups/new_backup/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
```

Depending on the type of backup the db object is an sqlite3 Connection object
to Manifest.db or None:

```
>>> b1.db
<sqlite3.Connection object at 0x7f22b87cf730>
```

The status field contains values parsed from Status.plist:

```
>>> b1.status.Date
datetime.datetime(2017, 10, 6, 22, 36, 38, 706502)
>>> b1.status.SnapshotState
'finished'
```

The manifest object contains values parsed from Manifest.plist, which includes
information on installed applications (the example uses the pprint module for
printing):

```
>>> b1.manifest.Version
'10.0'
>>> len(b1.manifest.Applications.keys())
307
>>> applist = [name for name in b1.manifest.Applications.keys() if 'whatsapp'
>>> in name]
>>> import pprint
>>> pprint.pprint(applist)
['net.whatsapp.WhatsApp.ShareExtension',
 'net.whatsapp.WhatsApp',
 'net.whatsapp.WhatsApp.Intents',
 'group.net.whatsapp.WhatsApp.shared',
 'net.whatsapp.WhatsApp.IntentsUI',
 'net.whatsapp.WhatsApp.TodayExtension']
>>> pprint.pprint(b1.manifest.Applications['net.whatsapp.WhatsApp'])
{'CFBundleIdentifier': 'net.whatsapp.WhatsApp',
 'CFBundleVersion': '2.17.20.1127',
 'ContainerContentClass': 'Data/Application',
 'Path':
 '/var/containers/Bundle/Application/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/WhatsApp.app'}
```

The filerecords object is a partial generator function that one can call to
iterate over the file records in the Manifest.db or Manifest.mbdb database.
The generator yields file\_entry namedtuples that contain the metadata
associated with each file record:

```
>>> b1.filerecords
functools.partial(<function _db_file_records at 0x7f22b820eae8>, <sqlite3.Connection object at 0x7f22b87cf730>)
>>> g = b1.filerecords()
>>> pprint.pprint(next(g)._asdict())
{'fileID': 'b1529201502c902a0ccbc961de80c6da9b61c67e',
 'domain': 'AppDomainPlugin-com.apple.news.diagnosticextension',
 'relativePath': '',
 'uid': 501,
 'gid': 501,
 'mtime': datetime.datetime(2017, 10, 6, 21, 32, 13, 4, tzinfo=<UTC>),
 'ctime': datetime.datetime(2017, 10, 6, 21, 33, 46, 4, tzinfo=<UTC>),
 'btime': datetime.datetime(2015, 12, 16, 22, 52, 11, 2, tzinfo=<UTC>),
 'inode': 2058125,
 'mode': 16877,
 'filetype': <FileType.Directory: 16384>,
 'permissions': '0o755',
 'size': 0,
 'protection': 0,
 'extended_attributes': None,
 'linktarget': None,
 'digest': None}
>>> pprint.pprint(next(g)._asdict())
{'fileID': '5b54f06a6837c79d9b6ab332d7eb82c71db1e006',
 'domain': 'AppDomainPlugin-com.apple.news.diagnosticextension',
 'relativePath': 'Library',
 'uid': 501,
 'gid': 501,
 'mtime': datetime.datetime(2015, 12, 16, 22, 52, 11, 2, tzinfo=<UTC>),
 'ctime': datetime.datetime(2017, 5, 8, 20, 14, 38, tzinfo=<UTC>),
 'btime': datetime.datetime(2015, 12, 16, 22, 52, 11, 2, tzinfo=<UTC>),
 'inode': 2058127,
 'mode': 16877,
 'filetype': <FileType.Directory: 16384>,
 'permissions': '0o755',
 'size': 0,
 'protection': 0,
 'extended_attributes': None,
 'linktarget': None,
 'digest': None}
```

In the above example, we use the \_asdict() function in order to convert the
namedtuples to dictionaries for printing, but for other purposes you can
simply access the individual fields with dot-notation:

```
>>> g = b1.filerecords()
>>> a = next(g)
>>> a.domain
'AppDomainPlugin-com.apple.news.diagnosticextension'
>>> a.inode
2058125
>>> a.ctime
datetime.datetime(2017, 10, 6, 21, 33, 46, 4, tzinfo=<UTC>)
```

If you are only interested in a subset of the files, this is easily achieved
using filters:

```
>>> g = b1.filerecords()
>>> f = filter(lambda r: 'Camera' in r.domain, g)
>>> f = filter(lambda r: 'jpg' in r.relativePath, f)
>>> a = next(f)
>>> a.relativePath
'Media/PhotoData/Mutations/DCIM/107APPLE/IMG_7552/Adjustments/FullSizeRender.jpg'
>>> a.size
2334762
>>> a.mtime
datetime.datetime(2017, 7, 21, 7, 18, 22, 4, tzinfo=<UTC>)
```

The fileID property of a file\_entry corresonds to the filename by which the
file is stored in the backup directory. For IOS9 backups, each file is stored
in the root of the backup directory, for IOS10 and above, there is an
intermediate structure where the first two characters of the fileID determine
in which subdirectory the file is stored. This allows you to access a file in
the backup as follows:

```
>>> a.fileID
'344caf5e612c4b118a486e292f61cb0036bfb60a'
>>> import os.path
>>> backupfile = os.path.join(b1.rootdir, a.fileID[0:2], a.fileID)
>>> backupfile
'/home/testuser/ios_backups/new_backup/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/34/344caf5e612c4b118a486e292f61cb0036bfb60a'
>>> with open(backupfile, 'rb') as g:
...     g.read(10)
...
...
b'\xff\xd8\xff\xe0\x00\x10JFIF'
```

If you want to export all files in the backup to a directory structure, you can
use the extract function. Depending on your preference you can either copy or
hardlink the files. If you hardlink, the extracted backup will not take much
extra space on disk and extraction will be much faster. I'm not sure if this
also works under Windows though. The function also has a progress option, which
displays a progress bar using the tqdm module:

```
>>> pearback.extract(b1, '~/temp/outdir', hardlink=True, progress=True)
extracting: 100%|███████████████████| 18922/18922 [00:09<00:00, 1942.34 files/s]
```

The export is structured by domain and does not necessarily reflect the exact
filesystem layout that the files have internally on the filesystem of your iOS
device:

```
$ ls ~/temp/outdir
AppDomain         HealthDomain    KeychainDomain            SysContainerDomain
AppDomainGroup    HomeDomain      ManagedPreferencesDomain  SysSharedContainerDomain
AppDomainPlugin   HomeKitDomain   MediaDomain               SystemPreferencesDomain
CameraRollDomain  InstallDomain   MobileDeviceDomain        WirelessDomain
DatabaseDomain    KeyboardDomain  RootDomain

$ ls ~/temp/outdir/CameraRollDomain/Media/DCIM
100APPLE  101APPLE  102APPLE  103APPLE  104APPLE  105APPLE  106APPLE  107APPLE 108APPLE
```

If you want to export only a subset of files, this can be done with the
export\_files function. For example, if we only want to extract all jpg files
in the CameraRollDomain we can do:

```
>>> g = b1.filerecords()
>>> f = filter(lambda r: 'Camera' in r.domain, g)
>>> f = filter(lambda r: r.relativePath.endswith('JPG'), f)
>>> pearback.extract_files(b1.backuptype, f, b1.rootdir, '~/temp/outdir2', hardlink=True)
```

The reason to develop this module was to be able to compare two backups of the
same iOS device for changes in the file contents. This can be done via the
changed\_files function. This function compares two files from different
backups if they have the same (domain, relativePath). The function yields
tuples (file\_entry\_0, file\_entry\_1) for any differences found.

If a (domain, relativePath) combination is not available in one of the backups,
the corresponding value in this tuple is set to None. If the contents of the
file differs between two backups, the file\_entries are both in the result
tuple. If the file contents is equal, no tuple is returned for that (domain,
relativePath) combination. Note that only file contents is compared, metadata
changes are not checked:

```
>>> b0 = pearback.load_backup('~/ios_backups/old_backup/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/')
>>> b1 = pearback.load_backup('~/ios_backups/new_backup/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/')
>>> g = pearback.changed_files(b0, b1)
```

Here we see an example of a file that only exists in the older backup and has
been removed since:

```
>>> d = next(g)
>>> d[0].relativePath
'Media/DCIM/107APPLE/IMG_7793.PNG'
>>> d[1]
```

And a file that only exists in the newer backup:

```
>>> g = pearback.changed_files(b0, b1)
>>> f = filter(lambda r: r[0] is None, g)
>>> d = next(f)
>>> d[0]
>>> d[1].relativePath
'Media/PhotoData/Photos.sqlite-shm'
```

And finally a file for which the contents has changed (or in this case has been
truncated):

```
>>> g = pearback.changed_files(b0, b1)
>>> f = filter(lambda r: r[0] is not None and r[1] is not None, g)
>>> d = next(f)
>>> d[0].relativePath
'Library/CallHistoryTransactions/transaction.log'
>>> d[0].size
1052
>>> d[1].size
0
```

Now, if we want to extract only those files from the previous backup that are
no longer present, or have changed since the previous backup we can use the
following function:

```
>>> pearback.extract_changed_and_removed_files(b0, b1, '~/temp/outdir3', hardlink=True)
```

This gives you a directory with all files that are no longer present in the
current backup. This is used in the backup.sh script to preserve files that
have been removed before removing the previous backup.

### commandline tool

This part of documentation is not yet finished.

### backups.h script

This part of documentation is not yet finished.

## installation

This part of documentation is not yet finished.

## related work

The Manifest.mbdb parser is based on various scripts floating around the
internet. For example:

* https://packetstormsecurity.com/files/127648/iTunes-Manifest.mbdb-Parser.html
* http://stackoverflow.com/questions/3085153/how-to-parse-the-manifest-mbdb-file-in-an-ios-4-0-itunes-backup
* http://www.securitylearn.net/tag/manifest-mbdb-format/

Another scripts can be found in the book "iOS Forensic Investigative Methods"
by Jonathan Zdziarski, which can be downloaded here:
https://www.zdziarski.com/blog/?p=2287.

Some of these scripts seem to have made a mistake with the timestamps as stored
in the Manifest.mbdb file, causing the ctime and mtime to be interchanged.
Also, most scripts mention one of the timestamps as atime, but it seems that
this is actually the creation time (btime). This was verified by making several
backups of a rooted iOS device and comparing actual filesystem timestamps with
timestamps as recorded in the Manifest.mbdb file. Still, these scripts where
very helpful in writing the \_parse\_mbdb\_entry and related functions.

The parser for the newer iOS10 Manifest.db was my own work, but of course there
was some inspiration from above parser scripts.

## requirements

The backup.sh script requires libimobiledevice, which can be installed from
here: https://github.com/libimobiledevice/libimobiledevice.git if it is not in
your distribution's package list.

## licence

MIT License

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
