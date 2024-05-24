#!/usr/bin/bash

if [ ! -f "$1" ]; then
  echo "usage: ./tools/integrate-launchpad-translations-export.sh /path/to/launchpad-export.tar.gz"
  exit 1
fi

set -x

EXPORT_TARBALL=$1
TMPWD=/tmp/ubuntu-pro-client-dev/launchpad-export/

rm -rf $TMPWD
mkdir -p $TMPWD
tar -xvf $EXPORT_TARBALL -C $TMPWD

cd $TMPWD/debian/po || exit
for pofile in *.po; do
  mv $pofile ${pofile#ubuntu-pro-}
done

cd - || exit
cp $TMPWD/debian/po/* ./debian/po/
