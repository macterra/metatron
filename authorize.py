from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from cid import make_cid
import binascii

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
from credentials import connect
    
rpc_connection = AuthServiceProxy(connect, timeout=120)
block_count = rpc_connection.getblockcount()

print(block_count)

info = rpc_connection.getwalletinfo()
print(info)

newaddr = rpc_connection.getnewaddress('bech32')
print(newaddr)

prev = { "txid": "78e189eff6ce7b6437d207ff5c5727126a61b3d7d573ef61c450c54302d90bb0", "vout": 0 } 

cid = make_cid("QmUZc1UF25Q5R6nu2W83Yi6RNREXjxD43T1xzSw9rxLrEp")
scheme = binascii.hexlify(str.encode("CID1")).decode()
print('cid', cid, scheme, cid.multihash.hex())
output = { "data": scheme + cid.multihash.hex() }

rawtxn = rpc_connection.createrawtransaction([prev], [output])
print('raw', rawtxn)

funtxn = rpc_connection.fundrawtransaction(rawtxn)
print('fun', funtxn)

sigtxn = rpc_connection.signrawtransactionwithwallet(funtxn['hex'])
print('sig', sigtxn)

dectxn = rpc_connection.decoderawtransaction(sigtxn['hex'])
print('dec', dectxn)

txid = rpc_connection.sendrawtransaction(sigtxn['hex'])
print('txid', txid)
