import sys
import os
import binascii
import json

from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from cid import make_cid
from xidb import *

magic = Decimal('0.00001111')
txfee = Decimal('0.00002222')
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

    def findCid(self, tx):
        for vout in tx['vout']:
            scriptPubKey = vout['scriptPubKey']
            script_type = scriptPubKey['type']
            if script_type == 'nulldata':
                hexdata = scriptPubKey['hex']
                data = bytes.fromhex(hexdata)
                if data[0] == 0x6a:
                    #print("data len", data[1])
                    try:
                        if data[1] == 34: # len of CIDv0
                            cid0 = make_cid(0, cid.CIDv0.CODEC, data[2:])
                            return str(cid0)
                        elif data[1] == 36: # len of CIDv1
                            cid1 = make_cid(data[2:])
                            cid0 = cid1.to_v0()
                            return str(cid0)
                    except:
                        #print('cid parser fail')
                        pass
        return None

    def updateWallet(self):
        unspent = self.blockchain.listunspent()
        print(unspent)
        auths = []
        funds = []
        for tx in unspent:
            if tx['amount'] == magic:
                auths.append(tx)
            else:
                funds.append(tx)

        xids = {}
        for tx in auths:
            print(f"{tx['txid']} {tx['amount']}")
            txin = self.blockchain.getrawtransaction(tx['txid'], 1)
            cid = self.findCid(txin)
            xid = getXid(cid)
            #print(json.dumps(txin, indent=2, cls=Encoder), cid)
            print(cid, xid)
            xids[xid] = tx

        print(xids)

        for tx in funds:
            print(f"{tx['txid']} {tx['amount']}")

        self.funds = funds
        self.xids = xids

    def authorize(self, cid):
        print(f"authorizing {cid}")
        
        xid = getXid(cid)

        if not xid:
            print(f"{cid} includes no valid xid")
            return

        print(f"found xid {xid}")

        self.updateWallet()

        inputs = []

        if xid in self.xids:  
            print(f"found xid {xid} in wallet")
            input = {
                "txid": self.xids[xid]['txid'],
                "vout": self.xids[xid]['vout']
            }
            inputs.append(input)
        else:
            print(f"claiming xid {xid}")


        funtxn = self.funds[0]
        funinp = {
            "txid": funtxn['txid'],
            "vout": funtxn['vout']
        }
        inputs.append(funtxn)

        # CIDv1
        realcid = make_cid(cid)
        hexdata = binascii.hexlify(realcid.to_v1().buffer).decode()

        print('cid', hexdata)
        nulldata = { "data": hexdata }

        authAddr = blockchain.getnewaddress("auth", "bech32")
        changeAddr = blockchain.getnewaddress("auth", "bech32")
        change = funtxn['amount'] - magic - txfee

        outputs = { authAddr: str(magic), "data": hexdata, changeAddr: change }

        print('inputs', inputs)
        print('outputs', outputs)

        rawtxn = blockchain.createrawtransaction(inputs, outputs)
        print('raw', rawtxn)

        sigtxn = blockchain.signrawtransaction(rawtxn)
        print('sig', sigtxn)
        
        dectxn = blockchain.decoderawtransaction(sigtxn['hex'])
        print('dec', json.dumps(dectxn, indent=2, cls=Encoder))
        
        txid = blockchain.sendrawtransaction(sigtxn['hex'])
        print('txid', txid)

def main():
    connect = os.environ.get('SCANNER_CONNECT')
    blockchain = AuthServiceProxy(connect, timeout=120)

    authorizer = Authorizer(blockchain)

    for arg in sys.argv[1:]:
        authorizer.authorize(arg)

if __name__ == "__main__":
    main()
