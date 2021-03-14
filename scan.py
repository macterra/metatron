
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

# credentials should export a connect string like "http://user:password@server:port"
from credentials import connect
    
# rpc_user and rpc_password are set in the bitcoin.conf file
rpc_connection = AuthServiceProxy(connect, timeout=120)
best_block_hash = rpc_connection.getbestblockhash()
tip = rpc_connection.getblock(best_block_hash)
print(tip)
