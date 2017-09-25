# pearback

Pearback is a python module to work with iOS backups. Backups from devices
running iOS 5 through 10 are supported. Pearback can be used as a library in
other projects, or as a command-line tool for interacting with backups. 

Pearback was written for my personal use in order to take the manual labour out
of managaging backups of the couple of iOS devices that we keep around the
house. But I hope it will be useful for you as well!

## warning

This is still experimental. At the time of this writing, I'm testing it on the
various iOS devices I have available. I take no responsibilty if you decide to
use this software and if anything goes wrong (see LICENCE).

## what it does

When used as a module in other projects, pearback provides you with a
consistent interface to the backup, regardless of whether the backup uses a
Manifest.mbdb file (iOS 5 through 9) or a Manifest.db file (iOS 10) internally.
The backup is represented as a backup-object, which consists of the parsed
Manifest.plist and Status.plist files, as well as an generator function that
you can use to iterate over each file-record in the backup. You have a couple
of functions available to extract files from the backup and print some info on
various aspects of the backup.

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
very helpful in writing the _parse_mbdb_entry and related functions.

The parser for the newer iOS10 Manifest.db was my own work, but of course there
was some inspiration from above parser scripts.

## example usage

TODO

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
