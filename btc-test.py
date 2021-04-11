lear
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from cid import make_cid

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
import credentials
    
def getwalletinfo(chain, client):
    print(chain)
    print('height', client.getblockcount())
    print(client.getwalletinfo())
    print()


tsr_client = AuthServiceProxy(credentials.tsr_connect, timeout=120)
getwalletinfo('tesseract', tsr_client)

tbtc_client = AuthServiceProxy(credentials.tbtc_connect, timeout=120)
getwalletinfo('bitcoin-test', tbtc_client)

btc_client = AuthServiceProxy(credentials.btc_connect, timeout=120)
getwalletinfo('bitcoin-main', btc_client)
