#!/bin/bash

DATE=`date +%y.%m.%d`
VERSION="v$DATE"

sh updateVersion.sh

sh buildVault.sh
docker tag macterra/metatron-vault macterra/metatron-vault:$VERSION
docker push macterra/metatron-vault
docker push macterra/metatron-vault:$VERSION

sh buildScanner.sh
docker tag macterra/metatron-scanner macterra/metatron-scanner:$VERSION
docker push macterra/metatron-scanner
docker push macterra/metatron-scanner:$VERSION

