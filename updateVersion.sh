#!/bin/bash

DATE=`date +%y.%m.%d`
HASH=`git rev-parse --short HEAD`
echo version="'v$DATE ($HASH)'" > version.py
