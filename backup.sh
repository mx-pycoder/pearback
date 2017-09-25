#!/bin/bash

# Copyright (c) 2017 Marnix Kaart
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# comment these next two lines when you have modified CRUFT
echo "[!] make sure to modify CRUFT variable to your needs before first run!"
exit

# stuff that may be removed from backups
CRUFT=("AppDomain/nl.omroep.radio4"
	   "AppDomain/nl.omroep.uitzendinggemist"
	   "CameraRollDomain/Media/PhotoData/Thumbnails"
	   "AppDomain/com.apple.calculator"
	   "AppDomain/nl.sanomadigital.nuhd"
	   "AppDomain/nl.tmobile.mytmobile"
	   "AppDomain/com.surfcheck.hetweer"
	   "AppDomain/nl.rtl.buienradar"
	   "AppDomain/nl.anwb.iphone.onderweg"
	   "HomeDomain/Library/SpringBoard"
	   "HomeDomain/Library/Cookies"
	   )

# the backup directory
BACKUPDIR=$1

if [ ! -e "$BACKUPDIR" ]; then
	echo "[!] $BACKUPDIR does not exist, abort!"
	exit
fi

# operate from the backupdir
pushd "$BACKUPDIR" >/dev/null 2>&1

if [ -e previous_backup ]; then
	echo "[!] previous backup still exists, abort!"
	exit
fi

if [ -e previous.deviceinfo ]; then
	echo "[!] previous deviceinfo still exists, abort!"
	exit
fi

echo "[x] idevicepair pair"
idevicepair pair

err=$?

if [ ! $err -eq 0 ]; then
	echo "[!] error pairing to device, abort!"
	exit
fi

if [ -e current.deviceinfo ]; then
	echo "[x] mv current.deviceinfo previous.deviceinfo"
	mv current.deviceinfo previous.deviceinfo
fi

echo "[x] ideviceinfo > current.deviceinfo"
ideviceinfo > current.deviceinfo

err=$?

if [ ! $err -eq 0 ]; then
	echo "[!] error connecting to device, abort!"
	exit
fi

uniqueid=`grep UniqueDeviceID current.deviceinfo | awk '{print $2}'`

if [ -e current_backup ]; then
	echo "[x] previous backup exists"
	if [ ! -e current_backup/$uniqueid ]; then
		echo "[!] previous backup is probably not from current device, abort!"
		echo "    [x] mv current.deviceinfo failed.deviceinfo"
		mv current.deviceinfo failed.deviceinfo
		echo "    [x] mv previous.deviceinfo current.deviceinfo"
		mv previous.deviceinfo current.deviceinfo
		echo "    [!] you may remove or keep failed.deviceinfo"
		exit
	fi
	echo "[x] cp -al current_backup previous_backup"
	cp -al current_backup previous_backup
fi

if [ ! -e current_backup ]; then
	echo "[x] mkdir current_backup"
	mkdir current_backup
fi

echo "[x] idevicebackup2 backup --full current_backup"
idevicebackup2 backup --full current_backup
# sometimes first attempt does not finish succesfully
echo "[x] idevicebackup2 backup --full current_backup (2nd)"
idevicebackup2 backup --full current_backup

err=$?

if [ ! $err -eq 0 ]; then
	echo "[!] error making backup"
	exit
fi

if [ ! -e previous_backup ]; then
	echo "[x] no previous backup found, we are done!"
	echo "    [!] latest backup is in $BACKUPDIR/current_backup"
	exit
fi

# determine date of previous backup to use in name of preserved files
DATE=`pearback info -D previous_backup/*`

if [ ! -e preserved ]; then
	echo "[x] mkdir preserved"
	mkdir preserved
fi

if [ -e preserved/$DATE ]; then
	echo "[!] directory preserved/$DATE already exists, abort!"
	exit
fi

echo "[x] mkdir preserved/$DATE"
mkdir preserved/$DATE

echo "[x] mv previous.deviceinfo preserved/$DATE.deviceinfo"
mv previous.deviceinfo preserved/$DATE.deviceinfo

echo "[x] extracting changed or removed files into preserved/$DATE"
pearback diff -e preserved/$DATE -l previous_backup/* current_backup/*

# remove previous backup
echo "[x] rm -rf previous_backup"
rm -rf previous_backup

echo "[!] latest backup is in $BACKUPDIR/current_backup"
echo "[!] files that where removed between $DATE and today are in $BACKUPDIR/preserved/$DATE"

# make sure user is aware that some stuff will be removed
while true; do
	read -p "[>] remove cruft from $BACKUPDIR/preserved/$DATE? (y/n/?) " yn
	case $yn in
		[Yy]* ) break;;
		[Nn]* ) exit;;
		[?]* ) echo "    [!] following paths are on cruftlist:";
			   for c in "${CRUFT[@]}"; do echo "        $c" ; done;;
		* ) echo "Please answer y or n.";
	esac
done

for c in "${CRUFT[@]}"; do
	echo "    [x] rm -rf preserved/$DATE/$c"
	rm -rf "preserved/$DATE/$c"
done

echo "[!] done"

popd > /dev/null 2>&2
