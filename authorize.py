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
        self.locked = 0
        self.balance = 0

        unspent = self.blockchain.listunspent()
        #print(unspent)
        funds = []
        assets = []

        for tx in unspent:
            if tx['vout'] == 1:
                txin = self.blockchain.getrawtransaction(tx['txid'], 1)
                auth = AuthTx(txin)
                if auth.isValid:
                    auth.utxo = tx
                    assets.append(auth)
                    self.locked += tx['amount']
                else:
                    funds.append(tx)
                    self.balance += tx['amount']
            else:
                funds.append(tx)
                self.balance += tx['amount']

        self.funds = funds
        self.assets = assets

    def authorize(self, cid):
        print(f"authorizing {cid}")
        
        xid = getXid(cid)

        if not xid:
            print(f"{cid} includes no valid xid")
            return

        print(f"found xid {xid}")

        self.updateWallet()

        inputs = []

        for asset in self.assets:
            if asset.meta['xid'] == xid:
                if cid == asset.cid:
                    print(f"xid is already up to date with {cid}")
                    return
                inputs.append(asset.utxo)
                break
            
        if len(inputs) == 0:
            print(f"claiming xid {xid}")

        amount = Decimal('0')
        for funtxn in self.funds:
            inputs.append(funtxn)
            amount += funtxn['amount']
            if amount > (magic + txfee):
                break

        if amount < (magic + txfee):
            print('not enough funds in account', amount)
            return

        hexdata = encodeCid(cid)    
        nulldata = { "data": hexdata }

        authAddr = self.blockchain.getnewaddress("auth", "bech32")
        changeAddr = self.blockchain.getnewaddress("auth", "bech32")
        change = funtxn['amount'] - magic - txfee

        outputs = { "data": hexdata, authAddr: str(magic), changeAddr: change }

        rawtxn = self.blockchain.createrawtransaction(inputs, outputs)
        sigtxn = self.blockchain.signrawtransaction(rawtxn)        
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
