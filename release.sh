echo $1

sh buildVault.sh
docker tag macterra/metatron-vault macterra/metatron-vault:$1
docker push macterra/metatron-vault
docker push macterra/metatron-vault:$1

sh buildScanner.sh
docker tag macterra/metatron-scanner macterra/metatron-scanner:$1
docker push macterra/metatron-scanner
docker push macterra/metatron-scanner:$1

