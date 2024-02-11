import idc 
import idaapi
import ida_bytes
import ida_auto

start = 0x1cc80
end = 0xff9fc

def get_mnem(addr): return idc.GetDisasm(addr).split(' ')[0]
def get_last_op(addr): return idc.GetDisasm(addr).split(' ')[-1]
def get_imm(addr): return idc.GetDisasm(addr).split('#')[-1].split(' ')[0]

for i in range(start, end, 4): 
    # addr1 -> BL within 0x40
    # addr2 -> MOV reg1, X0
    # addr3 -> ADD reg2, reg1, #num
    # addr4 -> BR/B reg2
    # OR:
    # addr2 -> ADD reg1, X0, #num
    # addr3 -> BR/B reg1
    addr = i 
    inst1 = idc.GetDisasm(addr)
    mnem = inst1.split(' ')[0]
    dest = inst1.split(' ')[-1]
    try: dest = int(dest.split('sub_')[-1], 16)
    except: continue
    if mnem == 'BL' and dest-addr < 0x40:
        mnem2 = get_mnem(addr+4)
        reg2 = get_last_op(addr+4)
        end_bad_addr = 0

        # option 1
        if mnem2 == 'MOV' and reg2 == 'X0':
            mnem3 = get_mnem(addr+8)
            if mnem3 == 'ADD':
                offset = get_imm(addr+8)
                try: offset = int(offset, 16)
                except: continue
                end_bad_addr = addr + offset
        
        # option 2
        if mnem2 == 'ADD' and idc.print_operand(addr+4, 1) == 'X0':
            dest = idc.print_operand(addr+4, 0)
            offset = get_imm(addr+4)
            try: offset = int(offset, 16) 
            except: continue

            cmd3 = get_mnem(addr+8)
            if cmd3 in ['BR', 'B'] and idc.print_operand(addr+8, 0) == dest:
                end_bad_addr = addr + offset

        # if found
        if end_bad_addr != 0:
             delta = end_bad_addr - i 
             if delta > 0x40: continue
             print(f'{hex(i)} - {hex(end_bad_addr)}')
             div = int((end_bad_addr-addr)/4)
             div = f'{div:02x}'
             patch_data = bytes.fromhex(div) + b'\x00\x00\x14'
             #patch_data = b'\xe0\x03\x00\xaa'
             #for j in range(i, end_bad_addr, 4): 
             #    ida_bytes.patch_bytes(j, patch_data)
             ida_bytes.patch_bytes(addr+4, patch_data)
             idc.auto_mark_range(i, end_bad_addr, ida_auto.AU_CODE)
             idc.plan_and_wait(i, end_bad_addr)

