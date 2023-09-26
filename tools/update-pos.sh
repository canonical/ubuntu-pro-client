#!/usr/bin/bash
set -x
cd debian/po || exit 1
intltool-update --pot -g ubuntu-pro --verbose
for pofile in *.po
do
    locale="${pofile%.po}"
    intltool-update -d $locale -g ubuntu-pro --verbose
done
