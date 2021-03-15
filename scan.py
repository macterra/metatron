
# pip install bitcoinrpc
# pip install py-cid

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from datetime import datetime
from dateutil import tz
import cid

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
from credentials import connect
    
rpc_connection = AuthServiceProxy(connect, timeout=120)
block_count = rpc_connection.getblockcount()

def scanBlock(height):
    block_hash = rpc_connection.getblockhash(height)
    block = rpc_connection.getblock(block_hash)
    
    block_time = block['time']
    utc = datetime.utcfromtimestamp(block_time).replace(tzinfo=tz.tzutc())
    timestamp = utc.astimezone(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S')

    #print(block)
    print(height, block_hash, block_time, utc, timestamp)

    txns = block['tx']
    for txid in txns:
        #print(txid)
        tx = rpc_connection.getrawtransaction(txid, 1)
        #print(tx)
        for vout in tx['vout']:
            #print(vout)
            scriptPubKey = vout['scriptPubKey']
            script_type = scriptPubKey['type']
            if script_type == 'nulldata':
                hexdata = scriptPubKey['hex']
                print("hex>>", hexdata)
                data = bytes.fromhex(hexdata)
                if data[0] == 0x6a and data[1] == 40:
                    if data[2:6] == b'CID1':
                        x = cid.make_cid(data[6:])
                        print("CID1>>", x.encode())
                        print("CID0>>", x.to_v0().encode())

scanBlock(1940280)                    
