import sys
import binascii
import json
import uuid
import ipfshttpclient
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from cid import make_cid

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
import credentials

magic = '0.00001111'
wallet = 'btc-wallet.json'    
btc_client = AuthServiceProxy(credentials.btc_connect, timeout=120)
ipfs_client = ipfshttpclient.connect()

try:
    with open(wallet, "r") as read_file:
        db = json.load(read_file)
except:
    db = {}

#print(db)

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

def writeWallet(idx, cid, tx):

    n = -1
    for vout in tx['vout']:
        val = vout['value']
        if val.compare(Decimal(magic)) == 0:
            n = vout['n']
            break

    if n < 0:
        print("error, can't find auth txn")
        return

    db[idx] = {
        "meta": cid,
        "auth": { "txid": tx['txid'], "vout": n },
        "tx": tx
    }
    
    with open(wallet, "w") as write_file:
        json.dump(db, write_file, cls = Encoder, indent=4)


def authorize(filename):
    if filename[:2] == "Qm":
        hashcid = filename
    else:
        res = ipfs_client.add(filename)
        print('res', res)
        hashcid = res['Hash']

    try:
        meta = json.loads(ipfs_client.cat(hashcid))
        print(meta)
        idx = meta['idx']
    except:
        idx = ipfs_client.cat(hashcid + '/idx').decode().strip()
        idx = str(uuid.UUID(idx))
        print('idx', idx)

    if idx in db:
        print('found idx', idx)

        last = db[idx]
        print('last', last)

        if hashcid == last['meta']:
            print("error, already submitted")
            return

        ownertx = last['auth']
        print('ownertx', ownertx)

        prev = [ ownertx ]
    else:
        print('first version of', idx)
        prev = []

    scheme = binascii.hexlify(str.encode("CID1")).decode()
    
    cid = make_cid(hashcid)
    cid1 = binascii.hexlify(cid.to_v1().buffer).decode()
    hexdata = scheme + cid1

    print('cid', cid, hexdata)
    nulldata = { "data": hexdata }

    addr = btc_client.getnewaddress("auth", "bech32")
    print('addr', addr)
    authtxn = { addr: magic }

    rawtxn = btc_client.createrawtransaction(prev, [authtxn, nulldata])
    print('raw', rawtxn)

    funtxn = btc_client.fundrawtransaction(rawtxn)
    print('fun', funtxn)

    sigtxn = btc_client.signrawtransactionwithwallet(funtxn['hex'])
    print('sig', sigtxn)

    dectxn = btc_client.decoderawtransaction(sigtxn['hex'])
    print('dec', dectxn)

    acctxn = btc_client.testmempoolaccept([sigtxn['hex']])
    print('acc', acctxn)

    if acctxn[0]['allowed']:
        txid = btc_client.sendrawtransaction(sigtxn['hex'])
        print('txid', txid)
        writeWallet(idx, hashcid, dectxn)

def main():
    for arg in sys.argv[1:]:
        authorize(arg)

if __name__ == "__main__":
    # execute only if run as a script
    main()