import ipfshttpclient
import uuid

ipfs = ipfshttpclient.connect()

def getXid(cid):
    xid = None

    try:
        meta = json.loads(ipfs.cat(cid))
        print(meta)        
        xid = meta['xid']
    except:
        xid = ipfs.cat(cid + '/xid').decode().strip()
        
    xid = str(uuid.UUID(xid))        
    print('xid', xid)
    return xid