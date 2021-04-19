mv credentials.py ..
git clean -f -d -x
ipfs add -r . > index
mv ../credentials.py .
