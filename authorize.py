import sys
import os
import json

from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from xidb import *

magic = Decimal('0.00001111')
txfee = Decimal('0.00002222')

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

class Authorizer:
    def __init__(self, blockchain):
        self.blockchain = blockchain

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
            txin = self.blockchain.getrawtransaction(tx['txid'], 1)
            print(f"got {tx['txid']} {tx['amount']}")
            #print(json.dumps(txin, indent=2, cls=Encoder), cid)
            cid = findCid(txin)
            print(f"> found {cid}")
            xid = getXid(cid)
            print(f">> found {xid}")
            xids[xid] = {
                "utxo": tx,
                "cid": cid
            }

        #print(xids)

        self.balance = 0
        for tx in funds:
            print(f"{tx['txid']} {tx['amount']}")
            self.balance += tx['amount']

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
            print(f"found xid {xid} in vault")
            if cid == self.xids[xid]['cid']:
                print(f"xid is already up to date with {cid}")
                return                
            utxo = self.xids[xid]['utxo']
            print(utxo)
            input = {
                "txid": utxo['txid'],
                "vout": utxo['vout']
            }
            inputs.append(input)
        else:
            print(f"claiming xid {xid}")

        amount = Decimal('0')
        for funtxn in self.funds:
            funinp = {
                "txid": funtxn['txid'],
                "vout": funtxn['vout']
            }
            inputs.append(funtxn)
            amount += funtxn['amount']
            if amount > (magic + txfee):
                break

        if amount < (magic + txfee):
            print('not enough funds in account', amount)
            return

        hexdata = encodeCid(cid)        
        #print('cid', hexdata)
        nulldata = { "data": hexdata }

        authAddr = self.blockchain.getnewaddress("auth", "bech32")
        changeAddr = self.blockchain.getnewaddress("auth", "bech32")
        change = funtxn['amount'] - magic - txfee

        outputs = { authAddr: str(magic), "data": hexdata, changeAddr: change }

        #print('inputs', inputs)
        #print('outputs', outputs)

        rawtxn = self.blockchain.createrawtransaction(inputs, outputs)
        #print('raw', rawtxn)

        sigtxn = self.blockchain.signrawtransaction(rawtxn)
        #print('sig', sigtxn)
        
        dectxn = self.blockchain.decoderawtransaction(sigtxn['hex'])
        print('dec', json.dumps(dectxn, indent=2, cls=Encoder))
        
        txid = self.blockchain.sendrawtransaction(sigtxn['hex'])
        print('txid', txid)

        return txid

def main():
    connect = os.environ.get('SCANNER_CONNECT')
    blockchain = AuthServiceProxy(connect, timeout=120)

    authorizer = Authorizer(blockchain)

    for arg in sys.argv[1:]:
        authorizer.authorize(arg)

if __name__ == "__main__":
    main()
