import ipfshttpclient
import uuid
import json
import zlib

def getIpfs():
    return ipfshttpclient.connect('/dns/ipfs/tcp/5001/http')

def verifyXid(xid):
    try:
        u = uuid.UUID(xid)    
        z = zlib.compress(u.bytes)
        if len(z) > len(u.bytes):
            return str(u)
        else:
            print(f"invalid {xid} compresses to {len(z)}")
            return None
    except:
        return None

def getXid(cid):
    xid = None
    ipfs = getIpfs()

    try:
        meta = json.loads(ipfs.cat(cid))
        xid = meta['xid']
    except:
        xid = ipfs.cat(cid + '/xid').decode().strip()
        
    return verifyXid(xid)

def getCert(cid):
    ipfs = getIpfs()
    return json.loads(ipfs.cat(cid))

def addCert(certfile):
    ipfs = getIpfs()
    res = ipfs.add(certFile)
    return res['Hash']
