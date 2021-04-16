import ipfshttpclient
import uuid
import json
import zlib

ipfs = ipfshttpclient.connect()

def verifyXid(xid):
    try:
        u = uuid.UUID(xid)    
        z = zlib.compress(u.bytes)
        if len(z) > len(u.bytes):
            return str(u)
        else:
            print(f"{xid} compresses to {len(z)}")
    except:
        return None
    return None

def getXid(cid):
    xid = None

    try:
        meta = json.loads(ipfs.cat(cid))
        xid = meta['xid']
    except:
        xid = ipfs.cat(cid + '/xid').decode().strip()
        
    xid = verifyXid(xid)       
    print('xid', xid)
    return xid