#!/usr/bin/env bash

CURRENT_DIR=$PWD
OUTFILE="$PWD/lambda.zip"
SITE_PACKAGES="$VIRTUAL_ENV/lib/python2.7/site-packages"
SITE_PACKAGES_64="$VIRTUAL_ENV/lib64/python2.7/site-packages"

[ -f "$OUTFILE" ] && rm $OUTFILE

zip -9 $OUTFILE config.json

[ -d "$SITE_PACKAGES" ] && cd $SITE_PACKAGES && zip -r9 $OUTFILE *
[ -d "$SITE_PACKAGES_64" ] && cd $SITE_PACKAGES_64 && zip -r9 $OUTFILE *

cd $CURRENT_DIR && zip -9 $OUTFILE *.py
