import ipfshttpclient

client = ipfshttpclient.connect()

res = client.add('test.py')
cid = res['Hash']
print(cid)
print(client.cat(cid))
