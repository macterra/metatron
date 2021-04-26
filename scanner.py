
# pip install bitcoinrpc
# pip install py-cid

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from datetime import datetime
from dateutil import tz
from decimal import Decimal
import os
import time
import cid
import json
import traceback
from xidb import *

magic = '0.00001111'
dbfile = 'data/db.json'

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

class Scanner:
    def __init__(self, chain, connect, first):        
        self.chain = chain
        self.blockchain = AuthServiceProxy(connect, timeout=30)
        self.first = first

        try:
            with open(dbfile, "r") as read_file:
                self.db = json.load(read_file)
        except:
            self.db = {
                "scan": {
                    self.chain: self.first
                }
            }
            self.writeDb()

    def writeDb(self):
        with open(dbfile, "w") as write_file:
            json.dump(self.db, write_file, cls = Encoder, indent=4)

    def findCid(self, tx):
        for vout in tx['vout']:
            scriptPubKey = vout['scriptPubKey']
            script_type = scriptPubKey['type']
            if script_type == 'nulldata':
                hexdata = scriptPubKey['hex']
                data = bytes.fromhex(hexdata)
                if data[0] == 0x6a:
                    # print("data len", data[1])
                    try:
                        if data[1] == 34: # len of CIDv0
                            cid0 = cid.make_cid(0, cid.CIDv0.CODEC, data[2:])
                            return str(cid0)
                        elif data[1] == 36: # len of CIDv1
                            cid1 = cid.make_cid(data[2:])
                            cid0 = cid1.to_v0()
                            return str(cid0)
                    except:
                        # print('cid parser fail')
                        pass
        return None


    def writeCert(self, tx, cid, xid, version, prevCert):
        block = self.blockchain.getblock(tx['blockhash'])
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

        urn = f"urn:chain:{self.chain}:{height}:{index}:{n}"

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
            "chain": self.chain,
            "time": str(utc),
            "owner": owner,
            "tx": tx
        }

        print('cert', cert)

        certFile = f"block-cert-v{version}.json"
        print('certFile', certFile)

        with open(certFile, "w") as write_file:
            json.dump(cert, write_file, cls = Encoder, indent=4)

        self.db[xid] = addCert(certFile)
        self.writeDb()

    def addVersion(self, tx, cid):
        print('addVersion', cid)

        xid = getXid(cid)    
        if xid in self.db:
            print("error, xid already claimed")
            return

        print("OK to add new block-cert")
        self.writeCert(tx, cid, xid, 0, "")

    # don't need oldTx?
    def updateVersion(self, oldTx, oldCid, newTx, newCid):
        print('updateVersion', oldCid, newCid)
        
        oldXid = getXid(oldCid)
        newXid = getXid(newCid)

        if oldXid != newXid:
            print("error, ids do not match", oldXid, newXid)
            return self.addVersion(newTx, newCid)
        
        if not oldXid in self.db:
            print("warning, can't find id in db", oldXid)
            return self.addVersion(newTx, newCid)
        
        certcid = self.db[oldXid]
        print('certcid', certcid)

        cert = getCert(certcid)
        print('cert', cert)

        if oldXid != cert['xid']:
            print("error, cert does not match xid", newXid)
            return

        if oldCid != cert['cid']:
            print("error, cert does not match meta", oldCid)
            return
        
        print("OK to update block-cert")

        version = cert['version'] + 1
        self.writeCert(newTx, newCid, newXid, version, certcid)

    def isAuthTx(self, tx, n):
        vout = tx['vout'][n]
        val = vout['value']
        return val.compare(Decimal(magic)) == 0

    def verifyTx(self, newTx, newCid):
        for vin in newTx['vin']:
            txid = vin['txid']
            vout = vin['vout']
            oldTx = self.blockchain.getrawtransaction(txid, 1)
            if self.isAuthTx(oldTx, vout):
                oldCid = self.findCid(oldTx)
                if oldCid:
                    return self.updateVersion(oldTx, oldCid, newTx, newCid)
        return self.addVersion(newTx, newCid)

    def scanBlock(self, height):
        block_hash = self.blockchain.getblockhash(height)
        block = self.blockchain.getblock(block_hash)
        
        block_time = block['time']
        utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())
        timestamp = utc.astimezone(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S')

        print(height, block_hash, block_time, utc, timestamp)

        txns = block['tx']
        for txid in txns:
            #print(txid)
            print('.', end='', flush=True)
            tx = self.blockchain.getrawtransaction(txid, 1)        
            cid = self.findCid(tx)
            if cid:
                print(f"found cid {cid}")
                self.verifyTx(tx, cid)
        print()
        print(f"scanned {len(txns)} transactions", flush=True)
        
        self.db['scan'][self.chain] = height

        self.writeDb()

    def updateScan(self):         
        count = self.blockchain.getblockcount()
        print(f"{datetime.now()} scanning {self.chain} height={count}", flush=True) 

        try:
            last = self.db['scan'][self.chain]
        except:
            last = self.first-1

        for height in range(last+1, count+1):
            self.scanBlock(height)

def main():
    chain = os.environ.get('SCANNER_CHAIN')
    connect = os.environ.get('SCANNER_CONNECT')
    start = os.environ.get('SCANNER_START')

    if not chain:
        print("missing SCANNER_CHAIN")
        return

    if not connect:
        print("missing SCANNER_CONNECT")
        return

    if not start:
        print("missing SCANNER_START")
        return

    if not checkIpfs():
        print("can't connect to IPFS")
        return

    while True:
        try:
            scanner = Scanner(chain, connect, int(start))
            scanner.updateScan()
        except Exception as e:
            print("error", e)
            print(traceback.format_exc())
        time.sleep(10)

if __name__ == "__main__":
    main()
