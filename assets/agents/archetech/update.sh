cd archetech
docker run --rm -v $PWD:/app/io macterra/metatron-agent
cd ..
docker run --rm -v $PWD:/app/io macterra/metatron-asset 
ipfs add -r .

