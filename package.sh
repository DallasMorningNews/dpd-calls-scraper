#!/usr/bin/env bash

CURRENT_DIR=$PWD
OUTFILE="$PWD/lambda.zip"
SITE_PACKAGES="$VIRTUAL_ENV/lib/python2.7/site-packages"
SITE_PACKAGES_64="$VIRTUAL_ENV/lib64/python2.7/site-packages"
PSYCOPG2_DIR="$PWD/lambda-psycopg2/"

[ -f "$OUTFILE" ] && rm $OUTFILE

zip -9 $OUTFILE config.json

[ -d "$SITE_PACKAGES" ] && cd $SITE_PACKAGES && zip -r9 $OUTFILE *
[ -d "$SITE_PACKAGES_64" ] && cd $SITE_PACKAGES_64 && zip -r9 $OUTFILE *

if [ ! -d "$PSYCOPG2_DIR" ]; then
  mkdir -p $PSYCOPG2_DIR
  curl -L https://github.com/jkehler/awslambda-psycopg2/archive/master.zip -o $PSYCOPG2_DIR/master.zip
  unzip $PSYCOPG2_DIR/master.zip -d $PSYCOPG2_DIR/
fi

cd $PSYCOPG2_DIR/awslambda-psycopg2/ && zip -r9 $OUTFILE psycopg2

cd $CURRENT_DIR && zip -9 $OUTFILE *.py
