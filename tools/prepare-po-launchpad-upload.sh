#!/usr/bin/bash
tar -czvf debian/po/launchpad_upload.tar.gz debian/po/ubuntu-pro.pot debian/po/*.po
echo "Now upload debian/po/launchpad_upload.tar.gz at https://translations.launchpad.net/ubuntu-advantage/trunk/+translations-upload"
