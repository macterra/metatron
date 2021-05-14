import ipfshttpclient
import uuid
import json
import zlib
import time
import os
import cid
import binascii

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
        try:
            meta = json.loads(ipfs.cat(cid + '/meta.json'))
            xid = meta['xid']
        except:
            try:
                # deprecated
                xid = ipfs.cat(cid + '/xid')
                xid = xid.decode().strip()
            except:
                print(f"error: unable to retrieve xid for {cid}")
        
    return verifyXid(xid)

def getCert(cid):
    ipfs = getIpfs()
    return json.loads(ipfs.cat(cid))

def addCert(cert):
    ipfs = getIpfs()
    res = ipfs.add(cert)
    return res['Hash']

def findCid(tx):
    for vout in tx['vout']:
        scriptPubKey = vout['scriptPubKey']
        script_type = scriptPubKey['type']
        if script_type == 'nulldata':
            hexdata = scriptPubKey['hex']
            data = bytes.fromhex(hexdata)
            if data[0] == 0x6a:
                #print("data len", data[1])
                try:
                    if data[1] == 34: # len of CIDv0
                        cid0 = cid.make_cid(0, cid.CIDv0.CODEC, data[2:])
                        return str(cid0)
                    elif data[1] == 36: # len of CIDv1
                        cid1 = cid.make_cid(data[2:])
                        cid0 = cid1.to_v0()
                        return str(cid0)
                except:
                    #print('cid parser fail')
                    pass
    return None

def encodeCid(hash):
    cid1 = cid.make_cid(hash)
    return binascii.hexlify(cid1.to_v1().buffer).decode()
