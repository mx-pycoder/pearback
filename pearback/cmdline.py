#!/usr/bin/env python3

''' application.py - commandline interface for pearback

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

# TODO: add exception handling
# TODO: add commandline switches to tweak output when listing diffs

import argparse as _argparse
import os as _os
from . import _pearback


def _parser():
    ''' argument parser '''
    parser = _argparse.ArgumentParser(
        prog='pearback',
        formatter_class = _argparse.RawDescriptionHelpFormatter,
        description = 'pearback - a simple tool to interact with iOS backups',
        epilog = 'Example usage: \n' +\
                 ' pearback extract -l ' +\
                 '~/temp/backup/047595d0fae972fbed0c51b4a41c7a349e0c47b ' +\
                 '~/temp/outdir\n' +\
                 ' pearback info -S ' +\
                 '~/temp/backup/047595d0fae972fbed0c51b4a41c7a349e0c47b\n'
        )

    subparsers = parser.add_subparsers(help='sub-command help')

    # extract mode
    ext = subparsers.add_parser('extract', help='extract backup')

    ext.add_argument('backupdir',
                     metavar='BACKUPDIR',
                     help='directory where iOS backup is stored')

    ext.add_argument('outdir',
                     metavar='OUTDIR',
                     help='directory where files should be extracted to')

    ext.add_argument('-P',
                     action="store_true",
                     help='show progress indicator')

    ext.add_argument('-l',
                     action="store_true",
                     help='use hardlinks instead of copying files')

    # info mode
    lst = subparsers.add_parser('info', help='get info on backup')

    lst.add_argument('backupdir',
                     metavar='BACKUPDIR',
                     help='directory where iOS backup is stored')

    lsttype = lst.add_mutually_exclusive_group(required=True)

    lsttype.add_argument('-L',
                         action="store_true",
                         help='list all files and their metadata')
    lsttype.add_argument('-S',
                         action="store_true",
                         help='print summary of backup')
    lsttype.add_argument('-D',
                         action="store_true",
                         help='print backup date')

    lst.add_argument('--sep',
                     metavar='separator',
                     help='separator to use when listing files (default: \\t)',
                     default='\t')

    lst.add_argument('--no-header',
                     action="store_true",
                     help='suppress header when listing files')

    # diff mode
    dif = subparsers.add_parser('diff', help='list or extract diffs between two backups')

    dif.add_argument('backup1', metavar='BACKUP1',
                      help='directory of first backup')

    dif.add_argument('backup2', metavar='BACKUP2',
                      help='directory of second backup')

    dif.add_argument('-e',
                     metavar='OUTDIR',
                     help='extract files from backup1 to OUTDIR if they are ' +\
                          'not present in backup2 or if they are different in ' +\
                          'backup2')

    dif.add_argument('-l',
                      action="store_true",
                      help='use hardlinks instead of copying files (requires -e)')

    return parser


def main():
    ''' entry point '''

    parser = _parser()
    args = parser.parse_args()

    # diff mode
    if hasattr(args, 'backup1'):

        backup1 = getattr(args, 'backup1')
        backup2 = getattr(args, 'backup2')
        b1 = _pearback.load_backup(backup1)
        b2 = _pearback.load_backup(backup2)

        # extract diff
        if hasattr(args, 'e'):
            outdir = getattr(args, 'e')
            hardlink = False
            if getattr(args, 'l') is True:
                hardlink = True
            _pearback.extract_changed_and_removed_files(b1, b2, outdir, hardlink)
            exit()

        # list diff
        else:
            diff = _pearback.changed_files(b1, b2)
            for (f1, f2) in diff:
                if f1 is not None:
                    f1 = _os.path.join(f1.domain, f1.relativePath)
                else:
                    f1 = ''
                if f2 is not None:
                    f2 = _os.path.join(f2.domain, f2.relativePath)
                else:
                    f2 = ''
                print("{:s}\t{:s}".format(f1, f2))
            exit()

        parser.print_help()

    # info or extract mode
    if not hasattr(args, 'backupdir'):
        parser.print_help()
        exit()

    # load the backup
    backup = _pearback.load_backup(getattr(args, 'backupdir'))

    # in info mode, we have either S, L or D
    if getattr(args, 'S', False) is True:
        # summarize backup
        _pearback.summarize(backup)
        exit()

    elif getattr(args, 'L', False) is True:
        # list files
        sep = getattr(args, 'sep')
        header = True
        if getattr(args, 'no_header') is True:
            header=False
        _pearback.list_all(backup, sep, header)
        exit()

    elif getattr(args, 'D', False) is True:
        date = backup.status.Date.isoformat()
        date = date.split('.')[0].replace('-','').replace(':','')
        print(date)
        exit()

    # if we get here, this is extract mode
    elif hasattr(args, 'outdir'):
        outdir = getattr(args, 'outdir')
        hardlink = False
        progress = False
        if getattr(args, 'l') is True:
            hardlink = True
        if getattr(args, 'P') is True:
            progress = True
        _pearback.extract(backup, outdir, hardlink, progress)
        exit()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()


