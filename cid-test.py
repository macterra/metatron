
from cid import make_cid
import binascii

scheme = binascii.hexlify(str.encode("CID1")).decode()

test = "QmeuJTFYWaLv3CMQv3m6FaWDrEQ6HwJZjE3YYrkAGZZGcs"
cid = make_cid(test)

cid0 = cid.multihash.hex()
cid1 = binascii.hexlify(cid.to_v1().buffer).decode()

print(cid0, len(cid0))
print(cid1, len(cid1))

hexdata = scheme + cid1

print('cid', cid, hexdata, len(hexdata))

data = bytes.fromhex(hexdata)
print(data)

print('verify prefix', data[0:4] == b'CID1')

x1 = make_cid(data[4:])
print("CID1>>", x1)
x0 = x1.to_v0()
print("CID0>>", x0)

print('verify decode', x0 == cid)
