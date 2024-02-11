def bfi(int2, int1, skip, width):
    bins1 = bin(int1)[2:].zfill(32)
    bins1 = list(bins1)[::-1]
    bins2 = bin(int2)[2:].zfill(32)
    bins2 = list(bins2)[::-1]
    bins2[skip:skip+width] = bins1[:width]
    bins2 = ''.join(bins2[::-1])
    final = int(bins2, 2)
    return final

def tohex(i:str):
    # format int to %2x
    num = ord(i)
    return hex(num)[2:].zfill(2)

gorgon_out = [0x17, 0x50]
x21 = 0x14
x8 = 0
w20 = 0xffffffeb
x9 = 0x13
w26 = 0x33
w28 = 1
w12 = 0x23
w13 = 0x1bd
w14 = 7
w15 = 0xFFFFFFAA
w16 = 0x55
gorgon_raw_var = x9
while x8 < x21:
    w11 = gorgon_out[x8]
    w25 = x8 + 1
    i = x8
    w8 = x8
    w9 = w11 >> 4
    w9 = bfi(w9, w11, 4, 8)
    gorgon_out[i] = w9 & 0xff
    import pdb; pdb.set_trace()
    if x21 <= w25:
        if w8 == 0: pass
        else:
            w10 = gorgon_raw_var
            if w10 != w8: pass
            else:
                w10 = gorgon_out[0]
                w9 ^= w10
                gorgon_out[i] = w9 & 0xff
    else:
        w9 = gorgon_out[i+1]
        w10 = gorgon_out[i]
        w9 ^= w10
        gorgon_out[i] = w9 & 0xff
    
    w8 = gorgon_out[i]
    w9 = w15 & (w8 << 1)
    w8 = w16 & (w8 >> 1)
    w8 |= w9
    w9 = w8 << 2
    w9 &= 0xFFFFFFCF
    w8 = w26 & (w8 >> 2)
    w8 |= w9
    # UBFX            W9, W8, #4, #4
    w9 = (w8 >> 4) & 0xf
    w9 = bfi(w9, w8, 4, 0x1c)
    w8 = w9 ^ w20 
    gorgon_out[i] = w8 & 0xff
    x8 = w25

final = "".join([hex(i)[2:] for i in gorgon_out])

