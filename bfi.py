w9 = 0x0000000f
w8 = 0x000007f4

# BFI             W9, W8, #4, #0x1C
def bfi(int2, int1, skip, width):
    bins1 = bin(int1)[2:].zfill(32)
    bins1 = list(bins1)[::-1]
    bins2 = bin(int2)[2:].zfill(32)
    bins2 = list(bins2)[::-1]
    bins2[skip:skip+width] = bins1[:width]
    bins2 = ''.join(bins2[::-1])
    final = int(bins2, 2)
    return final

final1 = bfi(w9, w8, 4, 0x1c)
final2 = bfi(0xe, 0xee, 4, 8)
print(hex(final1))
print(hex(final2))
