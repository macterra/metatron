from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

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

inputs = [ 
    { 
        "txid": "f749e7bbf77f20d2aa2a4cdf63870b9e34400f0a8d39f7590fcf1ddef440a132", 
        "vout": 1 
    } 
]

outputs = [ 
    { 
        "data": "010203040506" 
    }
]

rawtxn = rpc_connection.createrawtransaction([], outputs)
print('raw', rawtxn)

funtxn = rpc_connection.fundrawtransaction(rawtxn)
print('fun', funtxn)

sigtxn = rpc_connection.signrawtransactionwithwallet(funtxn['hex'])
print('sig', sigtxn)

dectxn = rpc_connection.decoderawtransaction(sigtxn['hex'])
print('dec', dectxn)

txid = rpc_connection.sendrawtransaction(sigtxn['hex'])
print('txid', txid)
