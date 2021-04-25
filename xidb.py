import ipfshttpclient
import uuid
import json
import zlib
import time
import os

def getIpfs():
    connect = os.environ.get('IPFS_CONNECT')

    if connect:
        return ipfshttpclient.connect(connect)
    else:
        return ipfshttpclient.connect()

def checkIpfs():
    for i in range(10):
        try:
            ipfs = getIpfs()
            print(ipfs.id())
            return True
        except:
            print(i, "attempting to connect to IPFS...")
            time.sleep(1)
    return False

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

def addCert(cert):
    ipfs = getIpfs()
    res = ipfs.add(cert)
    return res['Hash']
