import ipfshttpclient

client = ipfshttpclient.connect()

res = client.add('.', recursive=True, pattern="**")

if isinstance(res, list):
    for resp in res:
        print(resp)
else:
    print(res)

#cid = res['Hash']
#print(cid)
#print(client.cat(cid).decode())
