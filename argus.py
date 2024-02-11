import struct
from pysmx.SM3 import SM3


def bfi(rd, rn, lsb, width):
    rn = (rn & ls) << lsb
    ls = ~(ls << lsb)
    rd = rd & ls
    return rd

class Argus:
    def __init__(self, signKey1, signKey2, signKey3, signKey4):
        self._signKey1 = signKey1
        self._signKey2 = signKey2
        self._signKey3 = signKey3
        self._signKey4 = signKey4

    def _gen_key(self):
        data = (
            self._signKey1
            + self._signKey2
            + self._signKey3
            + self._signKey4
        )
        sm3 = SM3()
        sm3.update(bytes(data))
        res = sm3.hexdigest()
    
        res_list = []
        for i in range(0, len(res), 2):
            res_list.append(int(res[i : i + 2], 16))
        sm3_list = []
        for i in range(0, len(res_list), 4):
            c = struct.unpack("<I", bytes(res_list[i : i + 4]))
            sm3_list.append(c[0])
        res_list = res_list[:8]
        for i in range(0x47):
            t = i % 0x3E
            off = (0x20 - t) & 0xFF
            off_1 = t - 0x20
            if off_1 >= 0:
                B = 0x3DC94C3A >> off_1
            H = (sm3_list[6] >> 3) & 0xFFFFFFFF
            H |= (sm3_list[7] << 29) & 0xFFFFFFFF
            C = H ^ sm3_list[2]
            bfi_v = bfi(B, 0x7FFFFFFE, 1, 0x1F)
            H = (sm3_list[7] >> 3) & 0xFFFFFFFF
            H |= (sm3_list[6] << 29) & 0xFFFFFFFF
            E = H ^ sm3_list[3]
            if E & 1:
                B = (C >> 1) | 0x80000000
            else:
                B = C >> 1
            F = (E >> 1) | H
            G = F ^ sm3_list[1] ^ E
            A = ~G & 0xFFFFFFFF
            F = D ^ B
            for j in range(6):
                sm3_list[j] = sm3_list[j + 2]
            sm3_list[6] = F
            sm3_list[7] = A
            for j in range(2):
                for d in list(struct.pack("<I", sm3_list[j])):
                    res_list.append(d)
        return res_list


key1 = 0x440f1bba75061476
key2 = 0x34404058c630c1ea
key3 = 0xac322bb9444c3da7
key4 = 0x1f74e4e33781b153
# turn keys to a list of bytes
key1 = list(struct.pack("<Q", key1))
key2 = list(struct.pack("<Q", key2))
key3 = list(struct.pack("<Q", key3))
key4 = list(struct.pack("<Q", key4))
# flip key1 to little endian
#key1 = struct.unpack("<Q", struct.pack(">Q", key1))[0]
argus = Argus(key1, key2, key3, key4)
key = argus._gen_key()
print(key)

