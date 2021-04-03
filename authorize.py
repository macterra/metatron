from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from cid import make_cid
import binascii
import json
import ipfshttpclient

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
from credentials import connect
    
rpc_connection = AuthServiceProxy(connect, timeout=120)
client = ipfshttpclient.connect()

print(client.id())

with open("db.json", "r") as read_file:
    db = json.load(read_file)

print(db)

def authorize(filename):
    res = client.add(filename)
    print('res', res)
    hashcid = res['Hash']
    meta = json.loads(client.cat(hashcid))
    print(meta)

    xid = meta['id']
    print('xid', xid)

    if xid in db:
        print('found xid', xid)

        certcid = db[xid]
        print('certcid', certcid)

        cert = json.loads(client.cat(certcid))
        print('cert', cert)
        print('verify xid', xid == cert['id'])

        txid = cert['tx']['txid']
        print('txid', txid)

        prev = [{ "txid": txid, "vout": 0 }]
    else:
        print('first version of', xid)
        prev = []

    scheme = binascii.hexlify(str.encode("CID1")).decode()
    
    cid = make_cid(hashcid)
    cid1 = binascii.hexlify(cid.to_v1().buffer).decode()
    hexdata = scheme + cid1

    print('cid', cid, hexdata)
    output = { "data": hexdata }

    rawtxn = rpc_connection.createrawtransaction(prev, [output])
    print('raw', rawtxn)

    funtxn = rpc_connection.fundrawtransaction(rawtxn)
    print('fun', funtxn)

    sigtxn = rpc_connection.signrawtransactionwithwallet(funtxn['hex'])
    print('sig', sigtxn)

    dectxn = rpc_connection.decoderawtransaction(sigtxn['hex'])
    print('dec', dectxn)

    txid = rpc_connection.sendrawtransaction(sigtxn['hex'])
    print('txid', txid)

authorize('meta-v1.json')