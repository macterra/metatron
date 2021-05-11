import sys
import os
import binascii
import json

from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from cid import make_cid
from xidb import *

magic = '0.00001111'
connect = os.environ.get('SCANNER_CONNECT')
wallet = 'tsr-wallet.json'    
blockchain = AuthServiceProxy(connect, timeout=120)

try:
    with open(wallet, "r") as read_file:
        db = json.load(read_file)
except:
    db = {}

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

def writeWallet(xid, cid, tx):

    n = -1
    for vout in tx['vout']:
        val = vout['value']
        if val.compare(Decimal(magic)) == 0:
            n = vout['n']
            break

    if n < 0:
        print("error, can't find auth txn")
        return

    db[xid] = {
        "cid": cid,
        "auth": { "txid": tx['txid'], "vout": n },
        "tx": tx
    }
    
    with open(wallet, "w") as write_file:
        json.dump(db, write_file, cls = Encoder, indent=4)


def authorize(filename):
    if filename[:2] == "Qm":
        cidhash = filename
    else:
        res = ipfs.add(filename)
        cidhash = res['Hash']

    xid = getXid(cidhash)

    if not xid:
        print(f"{cidhash} includes no valid xid")
        return

    if xid in db:
        print('found xid', xid)

        last = db[xid]
        print('last', last)

        if cidhash == last['cid']:
            print("error, already submitted")
            return

        ownertx = last['auth']
        print('ownertx', ownertx)

        prev = [ ownertx ]
    else:
        print('first version of', xid)
        prev = []
    
    cid = make_cid(cidhash)

    # CIDv0
    #hexdata = cid.multihash.hex()

    # CIDv1
    hexdata = binascii.hexlify(cid.to_v1().buffer).decode()

    print('cid', hexdata)
    nulldata = { "data": hexdata }

    addr = blockchain.getnewaddress("auth", "bech32")
    print('addr', addr)
    authtxn = { addr: magic }

    #rawtxn = blockchain.createrawtransaction(prev, [authtxn, nulldata])
    rawtxn = blockchain.createrawtransaction(prev, { addr: magic, "data": hexdata })
    print('raw', rawtxn)

    funtxn = blockchain.fundrawtransaction(rawtxn)
    print('fun', funtxn)

    #sigtxn = blockchain.signrawtransactionwithwallet(funtxn['hex'])
    sigtxn = blockchain.signrawtransaction(funtxn['hex'])
    print('sig', sigtxn)

    dectxn = blockchain.decoderawtransaction(sigtxn['hex'])
    print('dec', dectxn)

    vin = dectxn['vin'][1]
    print('vin', vin)

    txin = blockchain.getrawtransaction(vin['txid'], 1)
    print('txin', txin)

    # acctxn = blockchain.testmempoolaccept([sigtxn['hex']])[0]
    # print('acc', acctxn)

    #if acctxn['allowed']:
    # txid = blockchain.sendrawtransaction(sigtxn['hex'])
    # print('txid', txid)
    # writeWallet(xid, cidhash, dectxn)

class Authorizer:
    def __init__(self, blockchain):
        self.blockchain = blockchain

    def updateWallet(self):
        unspent = self.blockchain.listunspent()
        print(unspent)
        for tx in unspent:
            print(f"{tx['txid']} {tx['amount']}")

    def authorize(self, cid):
        print(f"authorizing {cid}")
        
        xid = getXid(cid)

        if not xid:
            print(f"{cid} includes no valid xid")
            return

        print(f"found xid {xid}")

        self.updateWallet()    

def main():
    connect = os.environ.get('SCANNER_CONNECT')
    blockchain = AuthServiceProxy(connect, timeout=120)

    authorizer = Authorizer(blockchain)

    for arg in sys.argv[1:]:
        authorizer.authorize(arg)

if __name__ == "__main__":
    main()
