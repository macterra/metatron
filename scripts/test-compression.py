import uuid
import zlib
import brotli
import binascii


def test(u):
    comp = brotli.Compressor()
    z = zlib.compress(u.bytes)
    comp.process(u.bytes)
    out = comp.flush()
    blen = len(out)
    zlen = len(z) 
    print(u, len(u.bytes), blen, zlen, binascii.hexlify(z).decode())
    return zlen
    
def test2(i, u):
    z = zlib.compress(u.bytes)
    zlen = len(z) 
    print(i, u, len(u.bytes), zlen, binascii.hexlify(z).decode())
    return zlen

def test3(i, u):
    z = zlib.compress(u.bytes)
    zlen = len(z) 
    if zlen < 24:
        print(i, u, len(u.bytes), zlen, binascii.hexlify(z).decode())
    return zlen

def testRandom():
    for _ in range(100):
        test(uuid.uuid4())

def testSynthetic():
    test(uuid.UUID('00000000-0000-0000-0000-000000000000'))
    test(uuid.UUID('11111111-1111-1111-1111-111111111111'))
    test(uuid.UUID('00000000-0000-0000-1111-111111111111'))
    test(uuid.UUID('00000000-1111-2222-3333-444444444444'))
    test(uuid.UUID('00001111-2222-3333-4444-555566667777'))
    test(uuid.UUID('00000000-dead-beef-0000-000000000000'))
    test(uuid.UUID('12345678-90ab-cdef-fedc-ba0987654321'))
    test(uuid.UUID('deaddead-dead-dead-dead-deaddeaddead'))
    test(uuid.UUID('00000000000000000000000000000001'))

def testSequential():
    i = 1
    res = 0
    while True:
        res = test2(i, uuid.UUID("{0:0>32x}".format(i-1)))
        i += 1
        if res > 16:
            break

def testRandomness():
    i = 1
    hist = {}
    low = []
    high = []
    while True:
        idx = uuid.uuid4()
        res = test3(i, idx)
        try:
            hist[res] += 1
        except:
            hist[res] = 1
        i += 1
        if res < 24:
            print(hist)
        if res < 23:
            low.append(idx)
            print(low)
        # if res > 26:
        #     high.append(idx)
        #     for h in high:
        #         print(h)

#testSynthetic()
testRandomness()
