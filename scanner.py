
# pip install bitcoinrpc
# pip install py-cid
# pip install redis
# pip install docker

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from datetime import datetime
from dateutil import tz
from decimal import Decimal
from pathlib import Path

import os
import time
import json
import traceback
import redis
import shutil
from jinja2 import Environment, FileSystemLoader

import xidb
from authorize import AuthTx

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

class ScannerDb():
    def __init__(self):
        dbhost = os.environ.get('DB_HOST')

        if not dbhost:
            dbhost = 'localhost'
    
        self.db = redis.Redis(host=dbhost, port=6379, db=0)

    def dump(self):
        keys = self.db.keys("*")
        for key in sorted(keys):
            val = self.db.get(key)
            print(key, val)

    def getStatus(self):
        keys = self.db.keys("scanner/*")

        status = {}

        for key in keys:
            val = self.db.get(key)
            _, chain, prop = key.decode().split('/')
            if not chain in status:
                status[chain] = {}
            status[chain][prop] = val.decode()

        return status

    def getLatestVersion(self, xid):
        latest = self.db.get(f"xid/{xid}")
        
        if latest:
            latest = latest.decode().strip()

        return latest

    def getAssets(self):
        xids = self.db.keys("xid/*")
        assets = []

        for xid in xids:
            cid = self.db.get(xid).decode().strip()
            version = xidb.getMeta(cid)
            if version:
                meta = xidb.getMeta(version['cid'])
                if 'asset' in meta:
                    version['meta'] = meta
                    assets.append(version)
                else:
                    print("deprecated", xid)
                    #db.delete(xid)

        return sorted(assets, key=lambda version: version['meta']['asset'])

    def getAgents(self):
        axids = self.db.keys("agent/*")
        agents = []

        for axid in axids:
            xid = self.db.get(axid)
            cid = self.db.get(xid).decode().strip()
            version = xidb.getMeta(cid)
            if version:
                meta = xidb.getMeta(version['cid'])
                if 'asset' in meta:
                    version['meta'] = meta
                    agents.append(version)
        return agents

    def importAgents(self, authorizer):
        authorizer.updateWallet()
        for asset in authorizer.assets:
            isAgent = asset.meta['type'].find("/agent") > 0
            if isAgent:
                xid = asset.meta['xid']
                name = asset.meta['asset']
                print(xid, name)
                self.db.set(f"agent/{xid}", f"xid/{xid}")

    def flushall(self):
        self.db.flushall()
        
class Scanner:
    def __init__(self):
        self.server = os.environ.get('METATRON_SERVER')

        if not self.server:
            print("missing METATRON_SERVER")
            return
        
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

        connect = os.environ.get(f"{self.chain}_CONNECT")

        if not connect:
            print(f"missing {self.chain}_CONNECT")
            return

        dbhost = os.environ.get('DB_HOST')

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
            "blockheight": height,
            "blockhash": blockhash,
            "chainid": f"urn:chain:{self.chain}:{height}:{index}:{n}",
            "tx": { "txid": txid, "vout": n }
        }

        url = {
            "chain": f"http://{self.server}/chain/{self.chain}",
            "block": f"http://{self.server}/chain/{self.chain}/block/",
            "tx": f"http://{self.server}/chain/{self.chain}/tx/",
            "xid": f"http://{self.server}/versions/xid/"
        }

        cert = {
            "xid": xid,
            "meta": "QmZ3JispqhstvqsHnNSGXRnAhBZbJv7SdtcpVMvDt8gaFx/version",
            "cid": cid,
            "time": str(utc),
            "version": version,
            "prev": prevCert,
            "chain": self.chain,
            "auth": auth,
            "url": url
        }

        print('cert', cert)

        Path(xid).mkdir(parents=True, exist_ok=True)

        certFile = f"{xid}/meta.json"

        with open(certFile, "w") as write_file:
            json.dump(cert, write_file, cls = Encoder, indent=4)

        txFile = f"{xid}/tx.json"        
        with open(txFile, "w") as write_file:
            json.dump(tx.tx, write_file, cls = Encoder, indent=4)

        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template("version.html")
        index = template.render(version=cert)

        with open(f"{xid}/index.html", "w") as fout:
            fout.write(index)

        cert = xidb.addCert(xid)
        self.db.set(f"xid/{xid}", cert)

        print("added version", cert)
        shutil.rmtree(xid)

        return cert

    def addVersion(self, tx):
        #print('addVersion', tx.cid)
        current = self.db.get(f"xid/{tx.xid}")

        if current:
            print("error, xid already claimed")
            return

        #print("OK to add new version")
        return self.writeCert(tx, 1, "")        

    def updateVersion(self, oldTx, newTx):
        # print('updateVersion', oldTx.cid, newTx.cid)
        
        if oldTx.xid != newTx.xid:
            print("error: ids do not match", oldTx.xid, newTx.xid)
            return

        xid = newTx.xid        
        versionCid = self.db.get(f"xid/{xid}")

        if not versionCid:
            versionCid = self.verifyTx(oldTx)
            if not versionCid:
                print("warning, can't find version in db", xid)
                return
        else:
            versionCid = versionCid.decode()
        #print('versionCid', versionCid)
        
        versionMeta = xidb.getMeta(versionCid)
        #print('versionMeta', versionMeta)
        
        if versionMeta['cid'] == newTx.cid:
            print(f"warning: versionCid {versionCid} already assigned to xid {xid}")
            return

        if oldTx.xid != versionMeta['xid']:
            print("error: version does not match xid", xid)
            return

        if oldTx.cid != versionMeta['cid']:
            print("error: version does not match meta", oldTx.cid)
            return
        
        #print("OK to update version")

        version = versionMeta['version'] + 1
        return self.writeCert(newTx, version, versionCid)

    def verifyTx(self, newTx):
        vin = newTx.tx['vin'][0]
        txid = vin['txid']
        vout = vin['vout']
        
        #print(f"verifyTx {txid} {vout}")
        if vout == 1:
            tx = self.blockchain.getrawtransaction(txid, 1)
            oldTx = AuthTx(tx)
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
    #scanner.scanBlock(102888)
