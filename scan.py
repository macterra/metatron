
# pip install bitcoinrpc
# pip install py-cid

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from datetime import datetime
from dateutil import tz
import cid
import json
import ipfshttpclient

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
from credentials import connect
    
rpc_connection = AuthServiceProxy(connect, timeout=120)
block_count = rpc_connection.getblockcount()

rpc_connection = AuthServiceProxy(connect, timeout=120)
client = ipfshttpclient.connect()

#print(client.id())

with open("db.json", "r") as read_file:
    db = json.load(read_file)

print(db)

def findCid(tx):
    #print('findCid', tx) 
    for vout in tx['vout']:
        scriptPubKey = vout['scriptPubKey']
        script_type = scriptPubKey['type']
        if script_type == 'nulldata':
            hexdata = scriptPubKey['hex']
            data = bytes.fromhex(hexdata)
            if data[0] == 0x6a and data[1] == 40:
                if data[2:6] == b'CID1':
                    cid1 = cid.make_cid(data[6:])
                    cid0 = str(cid1.to_v0())
                    return cid0
    return None

def addVersion(tx, cid):
    print('addVersion', cid)
    meta = json.loads(client.cat(cid))
    print(meta)
    xid = meta['id']
    if xid in db:
        print("error, xid already claimed")
        return
    else:
        print("OK to add new block-cert")

def updateVersion(tx, oldCid, newCid):
    print('updateVersion', oldCid, newCid)
    
    meta1 = json.loads(client.cat(oldCid))
    meta2 = json.loads(client.cat(newCid))

    xid1 = meta1['id']
    xid2 = meta2['id']

    if xid1 != xid2:
        print("error, ids do not match", xid1, xid2)
        return
    
    if not xid1 in db:
        print("error, can't find id in db", xid1)
        return
    
    certcid = db[xid1]
    print('certcid', certcid)

    cert = json.loads(client.cat(certcid))
    print('cert', cert)
    print('verify xid', xid1 == cert['id'])
    print('verify meta', oldCid == cert['meta'])

    print("OK to update block-cert")

def verifyTx(tx, newCid):
    for vin in tx['vin']:
        txid = vin['txid']
        tx = rpc_connection.getrawtransaction(txid, 1)
        cid = findCid(tx)
        if cid:
            return updateVersion(tx, cid, newCid)
    return addVersion(tx, newCid)

def scanBlock(height):
    block_hash = rpc_connection.getblockhash(height)
    block = rpc_connection.getblock(block_hash)
    
    block_time = block['time']
    utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())
    timestamp = utc.astimezone(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S')

    print(height, block_hash, block_time, utc, timestamp)

    txns = block['tx']
    for txid in txns:
        tx = rpc_connection.getrawtransaction(txid, 1)        
        cid = findCid(tx)

        if cid:
            verifyTx(tx, cid)

#scanBlock(1940280)                    
scanBlock(1969654)
scanBlock(1969665)