#!/bin/sh

ARCHIVE_NAME=LED-Matrix_virtuelenv.tar.gz

# go to the parent directory of the virtualenv location
cd "$VIRTUALENV_DIR"
cd ..

# tar the virtualenv directory
tar -zcvf "$OUT_DIR"/$ARCHIVE_NAME $(basename "$VIRTUALENV_DIR")

chown $BUILD_UID:$BUILD_GID "$OUT_DIR"/$ARCHIVE_NAME
