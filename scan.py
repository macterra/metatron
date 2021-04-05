
# pip install bitcoinrpc
# pip install py-cid

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from datetime import datetime
from dateutil import tz
from decimal import Decimal
import cid
import json
import ipfshttpclient

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
from credentials import connect
    
btc_client = AuthServiceProxy(connect, timeout=120)
ipfs_client = ipfshttpclient.connect()

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

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

def writeCert(tx, cid, xid, version, prevCert):
    block = btc_client.getblock(tx['blockhash'])
    height = block['height']
    
    block_time = block['time']
    utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())

    txid = tx['txid']
    index = block['tx'].index(txid)

    n = -1
    for vout in tx['vout']:
        val = vout['value']
        if val.compare(Decimal("0.00001234")) == 0:
            n = vout['n']
            break

    urn = f"urn:chain:tBTC:{height}:{index}:{n}"

    owner = {
        "id": urn,
        "tx": { "txid": txid, "vout": n },
        "addresses": tx['vout'][n]['scriptPubKey']['addresses']
    }

    cert = {
        "type": "block-cert",
        "id": xid,
        "meta": cid,
        "version": version,
        "prev": prevCert,
        "chain": "tBTC",
        "time": str(utc),
        "owner": owner,
        "tx": tx
    }

    print('cert', cert)

    certFile = f"block-cert-v{version}.json"
    print('certFile', certFile)

    with open(certFile, "w") as write_file:
        json.dump(cert, write_file, cls = Encoder, indent=4)

    res = ipfs_client.add(certFile)
    db[xid] = res['Hash']
    
    with open("db.json", "w") as write_file:
        json.dump(db, write_file, cls = Encoder, indent=4)

def addVersion(tx, cid):
    print('addVersion', cid)
    meta = json.loads(ipfs_client.cat(cid))
    print(meta)
    xid = meta['id']

    if xid in db:
        print("error, xid already claimed")
        return

    print("OK to add new block-cert")
    writeCert(tx, cid, xid, 0, "")

def updateVersion(oldTx, oldCid, newTx, newCid):
    print('updateVersion', oldCid, newCid)
    
    meta1 = json.loads(ipfs_client.cat(oldCid))
    meta2 = json.loads(ipfs_client.cat(newCid))

    xid = meta1['id']
    xid2 = meta2['id']

    if xid != xid2:
        print("error, ids do not match", xid, xid2)
        return
    
    if not xid in db:
        print("warning, can't find id in db", xid)
        return addVersion(newTx, newCid)
    
    certcid = db[xid]
    print('certcid', certcid)

    cert = json.loads(ipfs_client.cat(certcid))
    print('cert', cert)

    if xid != cert['id']:
        print("error, cert does not match xid", xid)
        return

    if oldCid != cert['meta']:
        print("error, cert does not match meta", oldCid)
        return
        
    print("OK to update block-cert")

    version = cert['version'] + 1
    writeCert(newTx, newCid, xid, version, certcid)

def isAuthTx(tx, n):
    vout = tx['vout'][n]
    val = vout['value']
    return val.compare(Decimal("0.00001234")) == 0

def verifyTx(newTx, newCid):
    for vin in newTx['vin']:
        txid = vin['txid']
        vout = vin['vout']
        oldTx = btc_client.getrawtransaction(txid, 1)
        if isAuthTx(oldTx, vout):
            oldCid = findCid(oldTx)
            if oldCid:
                return updateVersion(oldTx, oldCid, newTx, newCid)
    return addVersion(newTx, newCid)

def scanBlock(height):
    block_hash = btc_client.getblockhash(height)
    block = btc_client.getblock(block_hash)
    
    block_time = block['time']
    utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())
    timestamp = utc.astimezone(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S')

    print(height, block_hash, block_time, utc, timestamp)

    txns = block['tx']
    for txid in txns:
        tx = btc_client.getrawtransaction(txid, 1)        
        cid = findCid(tx)
        if cid:
            verifyTx(tx, cid)

          
count = btc_client.getblockcount()
print(count)

for height in range(count-9, count+1):
    scanBlock(height)

# scanBlock(1969830)
# scanBlock(1969831)
# scanBlock(1969832)
# scanBlock(1969833)
# scanBlock(1969843)