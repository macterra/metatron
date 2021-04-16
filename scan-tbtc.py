
# pip install bitcoinrpc
# pip install py-cid

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from datetime import datetime
from dateutil import tz
from decimal import Decimal
import cid
import json
from xidb import *

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
import credentials
    
connect = credentials.tbtc_connect
chain = 'tBTC'    
magic = '0.00001111'

blockchain = AuthServiceProxy(connect, timeout=120)
ipfs = ipfshttpclient.connect()

with open("db.json", "r") as read_file:
    db = json.load(read_file)

print(db)

def findCid(tx):
    for vout in tx['vout']:
        scriptPubKey = vout['scriptPubKey']
        script_type = scriptPubKey['type']
        if script_type == 'nulldata':
            hexdata = scriptPubKey['hex']
            data = bytes.fromhex(hexdata)
            if data[0] == 0x6a:
                print("data len", data[1])
                try:
                    if data[1] == 34: # len of CIDv0
                        cid0 = cid.make_cid(0, cid.CIDv0.CODEC, data[2:])
                        return str(cid0)
                    elif data[1] == 36: # len of CIDv1?
                        cid1 = cid.make_cid(data[2:])
                        cid0 = cid1.to_v0()
                        return str(cid0)
                except:
                    print('cid parser fail')
    return None

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

def writeCert(tx, cid, xid, version, prevCert):
    block = blockchain.getblock(tx['blockhash'])
    height = block['height']
    
    block_time = block['time']
    utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())

    txid = tx['txid']
    index = block['tx'].index(txid)

    n = -1
    for vout in tx['vout']:
        val = vout['value']
        if val.compare(Decimal(magic)) == 0:
            n = vout['n']
            break

    urn = f"urn:chain:{chain}:{height}:{index}:{n}"

    owner = {
        "id": urn,
        "tx": { "txid": txid, "vout": n },
        "addresses": tx['vout'][n]['scriptPubKey']['addresses']
    }

    cert = {
        "type": "block-cert",
        "xid": xid,
        "cid": cid,
        "version": version,
        "prev": prevCert,
        "chain": chain,
        "time": str(utc),
        "owner": owner,
        "tx": tx
    }

    print('cert', cert)

    certFile = f"block-cert-v{version}.json"
    print('certFile', certFile)

    with open(certFile, "w") as write_file:
        json.dump(cert, write_file, cls = Encoder, indent=4)

    res = ipfs.add(certFile)
    db[xid] = res['Hash']
    
    with open("db.json", "w") as write_file:
        json.dump(db, write_file, cls = Encoder, indent=4)

def addVersion(tx, cid):
    print('addVersion', cid)

    xid = getXid(cid)    
    if xid in db:
        print("error, xid already claimed")
        return

    print("OK to add new block-cert")
    writeCert(tx, cid, xid, 0, "")

def updateVersion(oldTx, oldCid, newTx, newCid):
    print('updateVersion', oldCid, newCid)
    
    oldXid = getXid(oldCid)
    newXid = getXid(newCid)

    if oldXid != newXid:
        print("error, ids do not match", oldXid, newXid)
        return addVersion(newTx, newCid)
    
    if not oldXid in db:
        print("warning, can't find id in db", oldXid)
        return addVersion(newTx, newCid)
    
    certcid = db[oldXid]
    print('certcid', certcid)

    cert = json.loads(ipfs.cat(certcid))
    print('cert', cert)

    if oldXid != cert['xid']:
        print("error, cert does not match xid", newXid)
        return

    if oldCid != cert['cid']:
        print("error, cert does not match meta", oldCid)
        return
        
    print("OK to update block-cert")

    version = cert['version'] + 1
    writeCert(newTx, newCid, newXid, version, certcid)

def isAuthTx(tx, n):
    vout = tx['vout'][n]
    val = vout['value']
    return val.compare(Decimal(magic)) == 0

def verifyTx(newTx, newCid):
    for vin in newTx['vin']:
        txid = vin['txid']
        vout = vin['vout']
        oldTx = blockchain.getrawtransaction(txid, 1)
        if isAuthTx(oldTx, vout):
            oldCid = findCid(oldTx)
            if oldCid:
                return updateVersion(oldTx, oldCid, newTx, newCid)
    return addVersion(newTx, newCid)

def scanBlock(height):
    block_hash = blockchain.getblockhash(height)
    block = blockchain.getblock(block_hash)
    
    block_time = block['time']
    utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())
    timestamp = utc.astimezone(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S')

    print(height, block_hash, block_time, utc, timestamp)

    txns = block['tx']
    for txid in txns:
        #print(txid)
        print('.', end='', flush=True)
        tx = blockchain.getrawtransaction(txid, 1)        
        cid = findCid(tx)
        if cid:
            print(f"found cid {cid}")
            verifyTx(tx, cid)
    print()
    print(f"scanned {len(txns)} transactions")


def updateScan():          
    count = blockchain.getblockcount()
    print(count)

    try:
        last = db['scan'][chain]
    except:
        last = count

    for height in range(last, count+1):
        scanBlock(height)

    db['scan'][chain] = count

    with open("db.json", "w") as write_file:
        json.dump(db, write_file, cls = Encoder, indent=4)
    

scanBlock(1971687)

#updateScan()
