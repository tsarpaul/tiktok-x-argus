def eor(val):
    string = []
    key=[0xa5, 0x10, 0x71, 0xc7, 0x50, 0x90]
    for i in range(len(val)):
        j = i & 7
        v = val[j] ^ key[j]
        if v != 0: string.append(chr(v))
        else: print('x00')
    return "".join(string)

# mov w8, 0x72c4
# mov w9, 0x71
val = [0xc4, 0x72, 0x71]
eor(val)
