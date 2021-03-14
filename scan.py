
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from datetime import datetime
from dateutil import tz

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
from credentials import connect
    
rpc_connection = AuthServiceProxy(connect, timeout=120)
block_count = rpc_connection.getblockcount()

for height in range(block_count, block_count-10, -1):
    block_hash = rpc_connection.getblockhash(height)
    block = rpc_connection.getblock(block_hash)
    
    block_time = block['time']
    utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())
    timestamp = utc.astimezone(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S')

    print(height, block_hash, block_time, utc, timestamp)
    print(block)

    txns = block['tx']
    for txid in txns:
        print(txid)
        raw = rpc_connection.getrawtransaction(txid, 1)
        print(raw)
