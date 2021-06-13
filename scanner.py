
# pip install bitcoinrpc
# pip install py-cid
# pip install redis

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from datetime import datetime
from dateutil import tz
from decimal import Decimal

import os
import time
import json
import traceback
import redis

from xidb import *

magic = '0.00001111'

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

class Scanner:
    def __init__(self):
        
        if not checkIpfs():
            print("can't connect to IPFS")
            return

        self.chain = os.environ.get('SCANNER_CHAIN')

        if not self.chain:
            print("missing SCANNER_CHAIN")
            return

        self.keyfirst = f"scanner/{self.chain}/first"
        self.keylast = f"scanner/{self.chain}/last"
        self.keyheight = f"scanner/{self.chain}/height"
        self.keytime = f"scanner/{self.chain}/time"

        connect = os.environ.get('SCANNER_CONNECT')

        if not connect:
            print("missing SCANNER_CONNECT")
            return

        dbhost = os.environ.get('SCANNER_DBHOST')

        if not dbhost:
            dbhost = 'localhost'
      
        self.blockchain = AuthServiceProxy(connect, timeout=30)
        self.height = self.blockchain.getblockcount()

        self.db = redis.Redis(host=dbhost, port=6379, db=0)  
        self.db.set(self.keyheight, self.height)
        self.first = self.db.get(self.keyfirst)
        self.last = self.db.get(self.keylast)

        if self.first:
            self.first = int(self.first)

        if self.last:
            self.last = int(self.last)

        start = os.environ.get('SCANNER_START')

        if start:
            start = int(start)
        else:
            start = self.first or self.height

        # check for change in start
        if not self.last or not self.last or self.last < start or start < self.first:
            self.first = start
            self.last = start-1 
            self.db.set(self.keyfirst, self.first)
            self.db.set(self.keylast, self.last)


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

        auth = {
            "chain": self.chain,
            "time": str(utc),
            "id": f"urn:chain:{self.chain}:{height}:{index}:{n}",
            "tx": { "txid": txid, "vout": n },
            "addresses": tx['vout'][n]['scriptPubKey']['addresses'],
            "blockhash": tx['blockhash']
        }

        cert = {
            "type": "QmeKMenbWpW4YWV8Gi41kdsohjYaHvagXTem4zVcN23Q7t/block-certification",
            "xid": xid,
            "cid": cid,
            "version": version,
            "prev": prevCert,
            "auth": auth
        }

        print('cert', cert)
        certFile = f"block-cert-v{version}.json"
        print('certFile', certFile)

        with open(certFile, "w") as write_file:
            json.dump(cert, write_file, cls = Encoder, indent=4)

        self.db.set(f"xid/{xid}", addCert(certFile))

    def addVersion(self, tx, cid):
        print('addVersion', cid)

        xid = getXid(cid)

        if not xid:
            return

        if xid in self.db:
            print("error, xid already claimed")
            return

        print("OK to add new block-cert")
        self.writeCert(tx, cid, xid, 0, "")
        return cid

    # don't need oldTx?
    def updateVersion(self, oldTx, oldCid, newTx, newCid):
        print('updateVersion', oldCid, newCid)
        
        oldXid = getXid(oldCid)

        if not oldXid:
            print(f"error, no xid in {oldCid}")
            return

        newXid = getXid(newCid)

        if not newXid:
            print(f"error, no xid in {newCid}")
            return

        if oldXid != newXid:
            print("error, ids do not match", oldXid, newXid)
            return

        xid = newXid
        
        # !!! what is the logic here?
        certCid = self.db.get(f"xid/{xid}")
        if not certCid:
            self.verifyTx(oldTx, oldCid)
            certCid = self.db.get(f"xid/{xid}")
            if not certCid:
                print("warning, can't find cert cid in db", xid)
                return

        certCid = certCid.decode()
        print('certCid', certCid)
        
        cert = getCert(certCid)
        print('cert', cert)
        
        if cert['cid'] == newCid:
            print(f"error, certCid {certCid} already assigned to xid {xid}")
            return

        if oldXid != cert['xid']:
            print("error, cert does not match xid", xid)
            return

        if oldCid != cert['cid']:
            print("error, cert does not match meta", oldCid)
            return
        
        print("OK to update block-cert")

        version = cert['version'] + 1
        self.writeCert(newTx, newCid, newXid, version, certCid)
        return newCid

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
                oldCid = findCid(oldTx)
                if oldCid:
                    return self.updateVersion(oldTx, oldCid, newTx, newCid)
        return self.addVersion(newTx, newCid)

    def scanBlock(self, height):
        block_hash = self.blockchain.getblockhash(height)
        block = self.blockchain.getblock(block_hash)
        
        block_time = block['time']
        utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())
        timestamp = utc.astimezone(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S')

        print(f"{height}", block_hash, block_time, utc, timestamp)

        txns = block['tx']
        for txid in txns:
            #print(txid)
            print('.', end='', flush=True)
            tx = self.blockchain.getrawtransaction(txid, 1)        
            cid = findCid(tx)
            if cid:
                print(f"found cid {cid}")
                self.verifyTx(tx, cid)
        print()
        print(f"scanned {len(txns)} transactions", flush=True)
        
        self.db.set(self.keylast, height)
        self.db.set(self.keytime, f"{utc}")

    def updateScan(self):
        print(f"{datetime.now()} scanning {self.chain} height={self.height}", flush=True) 

        for block in range(self.last+1, self.height+1):
            self.scanBlock(block)

def scanAll():
    while True:
        try:
            scanner = Scanner()
            scanner.updateScan()
        except Exception as e:
            print("error", e)
            print(traceback.format_exc())
        time.sleep(10)

if __name__ == "__main__":
    scanAll()
            
    #scanner = Scanner()
    #scanner.scanBlock(99316)
