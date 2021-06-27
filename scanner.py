
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

import xidb
from authorize import AuthTx

#magic = '0.00001111'

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

class Scanner:
    def __init__(self):
        
        if not xidb.checkIpfs():
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
        #self.db.flushall()
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


    def writeCert(self, tx, version, prevCert):
        cid = tx.cid
        xid = tx.xid
        blockhash = tx.tx['blockhash']
        txid = tx.tx['txid']

        block = self.blockchain.getblock(blockhash)
        height = block['height']
        
        block_time = block['time']
        utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())

        index = block['tx'].index(txid)
        n = 1

        auth = {
            "chain": self.chain,
            "blockheight": height,
            "blockhash": blockhash,
            "chainid": f"urn:chain:{self.chain}:{height}:{index}:{n}",
            "tx": { "txid": txid, "vout": n }
        }

        cert = {
            "type": "QmNxoYA7yWa2foqNKFMDR1vTvaPi8F7oHq9qiqAb9znHVs/authorization",
            "xid": xid,
            "cid": cid,
            "time": str(utc),
            "version": version,
            "prev": prevCert,
            "auth": auth
        }

        print('cert', cert)
        certFile = f"block-cert-v{version}.json"
        print('certFile', certFile)

        with open(certFile, "w") as write_file:
            json.dump(cert, write_file, cls = Encoder, indent=4)

        cert = xidb.addCert(certFile)
        self.db.set(f"xid/{xid}", cert)
        return cert

    def addVersion(self, tx):
        print('addVersion', tx.cid)

        current = self.db.get(f"xid/{tx.xid}")

        if current:
            print("error, xid already claimed")
            return

        print("OK to add new block-cert")
        return self.writeCert(tx, 0, "")        

    # don't need oldTx?
    def updateVersion(self, oldTx, newTx):
        print('updateVersion', oldTx.cid, newTx.cid)
        
        if oldTx.xid != newTx.xid:
            print("error, ids do not match", oldXid, newXid)
            return

        xid = newTx.xid        
        certCid = self.db.get(f"xid/{xid}")

        if not certCid:
            certCid = self.verifyTx(oldTx)
            if not certCid:
                print("warning, can't find cert cid in db", xid)
                return

        certCid = certCid.decode()
        print('certCid', certCid)
        
        cert = xidb.getCert(certCid)
        print('cert', cert)
        
        if cert['cid'] == newTx.cid:
            print(f"error, certCid {certCid} already assigned to xid {xid}")
            return

        if oldTx.xid != cert['xid']:
            print("error, cert does not match xid", xid)
            return

        if oldTx.cid != cert['cid']:
            print("error, cert does not match meta", oldTx.cid)
            return
        
        print("OK to update block-cert")

        version = cert['version'] + 1
        self.writeCert(newTx, version, certCid)
        return newTx.cid

    def verifyTx(self, newTx):
        vin = newTx.tx['vin'][0]
        txid = vin['txid']
        vout = vin['vout']
        
        print(f"verifyTx {txid} {vout}")

        if vout == 1:
            tx = self.blockchain.getrawtransaction(txid, 1)
            oldTx = xidb.AuthTx(tx)
            if oldTx.isValid:
                return self.updateVersion(oldTx, newTx)

        return self.addVersion(newTx)

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
            newTx = AuthTx(tx)
            if newTx.isValid:
                self.verifyTx(newTx)
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
    #scanner.scanBlock(101091)
