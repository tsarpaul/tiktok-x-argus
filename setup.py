import lldb
import subprocess
import os
import struct
from time import sleep

def pack_reg(exe_ctx, f, reg):
    reg = exe_ctx.frame.FindRegister(reg).value
    reg = int(reg, 16)
    b = struct.pack('<Q', reg)
    f.write(b)

def dumpit(debugger, command, exe_ctx, result, internal_dict):
    # dump every stack/heap region, libmetasec.so and registers
    regs = [
        'x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7',
        'x8', 'x9', 'x10', 'x11', 'x12', 'x13', 'x14', 'x15',
        'x16', 'x17', 'x18', 'x19', 'x20', 'x21', 'x22', 'x23',
        'x24', 'x25', 'x26', 'x27', 'x28', 'x29', 'x30', 'sp', 'pc'
    ]
    with open('dumpit/emulator.bin', 'wb') as f:
        for reg in regs:
            pack_reg(exe_ctx, f, reg)

    with open('dumpit/code.bin', 'wb') as f:
        # dump every stack/heap region
        # write addr, size then dump memory into file
        modules = exe_ctx.target.modules
        for module in modules:
            name = module.file.basename
            if name.startswith("libmetasec_ov.so"):
                addr = hex(int(module.ResolveFileAddress(0).GetLoadAddress(exe_ctx.target)))
                size = sum([section.size for section in module.section_iter()])
                print(f'{name}: {addr} {hex(size)}')

                # write addr and size
                addr = int(addr, 16)
                f.write(struct.pack('<Q', addr))
                f.write(struct.pack('<Q', size))

                # dump memory
                addr = lldb.SBAddress(addr, exe_ctx.target)
                memory = exe_ctx.target.ReadMemory(addr, size, lldb.SBError())
                f.write(memory)

        # dump heap
    with open('dumpit/maps.bin', 'wb') as f:
        # get process id from lldb
        pid = exe_ctx.process.id
        print(f"PID: {pid}")
        # get heap address from /proc/pid/maps
        pipe = subprocess.Popen("adb shell su -c 'cat /proc/" + str(pid) + "/maps | grep 'rw-p''", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        regions = pipe.stdout.read().strip()
        regions = regions.decode('utf-8')
        regions = regions.split('\n')
        for region in regions:
            if '(deleted)' in region: continue
            region = region.split(' ')
            source = region[-1]
            if source.startswith('/'): continue

            addr = int(region[0].split('-')[0], 16)
            size = int(region[0].split('-')[1], 16) - addr
            print(f'region: {hex(addr)} {hex(size)}')
            f.write(struct.pack('<Q', addr))
            f.write(struct.pack('<Q', size))
            addr = lldb.SBAddress(addr, exe_ctx.target)
            memory = exe_ctx.target.ReadMemory(addr, size, lldb.SBError())
            f.write(memory)

def get_pid():
    # redirect stdout to devnull
    #pid=$(adb shell ps -A | grep musically | awk -F ' ' '{print $2}' | head -n 1)
    pipe = subprocess.Popen("adb shell ps -A | grep -E 'musically$' | awk -F ' ' '{print $2}' | head -n 1", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pid = pipe.stdout.read().strip()
    pid = pid.decode('utf-8')
    return pid

def sigstuff(debugger, command, result, internal_dict):
    debugger.HandleCommand('proc hand -p true -s false -n false SIGSEGV SIGCHLD')
    debugger.HandleCommand('proc hand -p false -s false -n true SIGSTOP SIGQUIT SIGABRT')

def appup(debugger, command, result, internal_dict):
    pipe = subprocess.Popen("adb shell monkey -p com.zhiliaoapp.musically 1", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sleep(1)
    tiktok_connect(debugger, command, result, internal_dict)

def tiktok_connect(debugger, command, result, internal_dict):
    pid = get_pid()
    debugger.HandleCommand('platform select remote-android')
    debugger.HandleCommand('platform connect connect://7088b1b5:10000')
    debugger.HandleCommand('process attach -c --pid ' + pid)
    debugger.HandleCommand('proc hand -p true -s false -n false SIGSEGV SIGCHLD')
    debugger.HandleCommand('proc hand -p false -s false -n true SIGSTOP SIGQUIT')

def get_addr(modname, exe_ctx):
    modules = exe_ctx.target.modules
    for module in modules:
        name = module.file.basename
        if name == modname:
            return int(module.ResolveFileAddress(0).GetLoadAddress(exe_ctx.target))
    return 0

def addrs(debugger, command, exe_ctx, result, internal_dict):
    # find address of libsscronet.so and libmetasec_ov.so
    modules = exe_ctx.target.modules
    for module in modules:
        name = module.file.basename
        if name in ["libsscronet.so", "libmetasec_ov.so"]:
            # print base address
            addr = hex(int(module.ResolveFileAddress(0).GetLoadAddress(exe_ctx.target)))
            print(f'{name}: {addr}')

def get_module(debugger, exe_ctx, address):
    # address is in-process address, we want to find relative address
    modules = exe_ctx.target.modules
    for module in modules:
        start_addr = module.ResolveFileAddress(0).GetLoadAddress(exe_ctx.target)
        size = sum([section.size for section in module.section_iter()])
        end_addr = start_addr + size
        if start_addr <= address <= end_addr:
            return module.file.basename
    return None

def calc_addr(lib, addr, exe_ctx):
    baseaddr = get_addr(lib, exe_ctx)
    return hex(addr - baseaddr)

def vm(debugger, command, exe_ctx, result, internal_dict):
    addr_str = command.split(' ')[0]
    if not addr_str: return
    if addr_str.endswith(','): addr_str = addr_str[:-1]
    if addr_str.startswith('$'):
        # get register value
        reg = addr_str[1:]
        addr_str = exe_ctx.frame.FindRegister(reg).value
    addr = int(addr_str, 16)
    print(calc_addr("libmetasec_ov.so", addr, exe_ctx))

def vc(debugger, command, exe_ctx, result, internal_dict):
    addr_str = command.split(' ')[0]
    if not addr_str: return
    if addr_str.endswith(','): addr_str = addr_str[:-1]
    addr = int(addr_str, 16)
    print(calc_addr("libsscronet.so", addr, exe_ctx))

def new_bp(debugger, command, exe_ctx, result, internal_dict):
    # continue until execution reaches new breakpoint
    last_addr = exe_ctx.frame.pc
    while True:
        debugger.HandleCommand('c')
        addr = exe_ctx.frame.pc
        if not addr == last_addr: break
        last_addr = addr

def jmp_c(debugger, command, exe_ctx, result, internal_dict):
    # step until execution leaves branch
    debugger.SetAsync(False)
    last_addr = exe_ctx.frame.pc
    while True:
        debugger.HandleCommand('s')
        addr = exe_ctx.frame.pc
        if not addr-4 == last_addr: break
        last_addr = addr
        
def jmp_str(debugger, command, exe_ctx, result, internal_dict):
    # step until 'str' instruction
    debugger.SetAsync(False)

    # check if we are stopped
    if not exe_ctx.process.is_stopped:
        print('Error: process is not stopped')
        return

    while True:
        exe_ctx.thread.StepInto()

        addr = lldb.SBAddress(exe_ctx.frame.pc, exe_ctx.target)
        inst = exe_ctx.target.ReadInstructions(addr, 1)[0]
        op = inst.GetMnemonic(exe_ctx.target)

        #if op == 'str': 
        if op:
            function = exe_ctx.frame.GetFunction()
            function_start_addr = function.GetStartAddress().GetLoadAddress(exe_ctx.target)
            rel_addr = exe_ctx.frame.pc - function_start_addr
            print(f'+{rel_addr}: {inst}')
            break

def log_jmp_tbl(debugger, command, exe_ctx, result, internal_dict):
    with open('log2.txt', 'w') as f:
        while True:
            debugger.HandleCommand('c')
            addr = exe_ctx.frame.pc
            addr_rel = calc_addr("libmetasec_ov.so", addr, exe_ctx)

            if not addr_rel == "0xa01a0": break
            x0 = exe_ctx.frame.FindRegister('x0').value
            x0 = int(x0, 16)
            x0_rel = calc_addr("libmetasec_ov.so", x0, exe_ctx)
            f.write(f'{x0_rel}\n')

def new_bp_log(debugger, command, exe_ctx, result, internal_dict):
    debugger.SetAsync(False)
    log_file = open('log.txt', 'w')
    while True:
        debugger.HandleCommand('s')

        # log current instruction to file
        addr = exe_ctx.frame.pc
        # if current addr is a breakpoint, break
        if exe_ctx.target.FindBreakpointByID(exe_ctx.thread.GetStopReasonDataAtIndex(0)).IsValid(): break

        # read $pc register
        ip = exe_ctx.GetTarget().ResolveLoadAddress(addr)
        inst = exe_ctx.target.ReadInstructions(ip, 1)[0]

        # get current library
        lib = get_module(debugger, exe_ctx, addr)
        want_lib = "libmetasec_ov.so"
        if want_lib != lib:
            # NOTE: This can miss some instructions if a BR (not BL) is called to a different library 
            debugger.HandleCommand('fin')
            continue
        addr_fixed = calc_addr(lib, addr, exe_ctx)
        addr_fixed = addr_fixed[2:]
        addr_fixed = addr_fixed.zfill(6)

        log_file.write(f'{inst}\n')
        log_file.flush()

def str_c(debugger, command, exe_ctx, result, internal_dict):
    pass

def dump(debugger, command, exe_ctx, result, internal_dict):
    # 1st arg = start address, 2nd arg = size, 3rd arg optional = output file
    args = command.split(' ')
    if len(args) < 2: 
        print('Usage: dump <start_addr> <size> [outfile]')
        return
    start_addr = int(args[0], 16)
    size = int(args[1], 16)
    outfile = 'dump.bin'
    if len(args) == 3: outfile = args[2]

    addr = lldb.SBAddress(start_addr, exe_ctx.target)
    memory = exe_ctx.target.ReadMemory(addr, size, lldb.SBError())
    with open(outfile, 'wb') as f: f.write(memory)

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -o -f setup.tiktok_connect tiktok_connect')
    debugger.HandleCommand('command script add -o -f setup.addrs addrs')
    debugger.HandleCommand('command script add -o -f setup.vm vm')
    debugger.HandleCommand('command script add -o -f setup.vc vc')
    debugger.HandleCommand('command script add -o -f setup.jmp_c jmp_c')
    debugger.HandleCommand('command script add -o -f setup.jmp_str jmp_str')
    debugger.HandleCommand('command script add -o -f setup.new_bp new_bp')
    debugger.HandleCommand('command script add -o -f setup.new_bp_log new_bp_log')
    debugger.HandleCommand('command script add -o -f setup.sigstuff sigstuff')
    debugger.HandleCommand('command script add -o -f setup.appup appup')
    debugger.HandleCommand('command script add -o -f setup.dump dump')
    debugger.HandleCommand('command script add -o -f setup.dumpit dumpit')
    debugger.HandleCommand('command script add -o -f setup.log_jmp_tbl log_jmp_tbl')
    print('Commands installed: tiktok_connect, addrs, vm, vc, jmp_c, jmp_str, new_bp, new_bp_log, sigstuff, appup, dump, dumpit, log_jmp_tbl')

    debugger.HandleCommand('command alias bm b -s libmetasec_ov.so -a')
    debugger.HandleCommand('command alias vma vm $pc')
    print('Aliases added: bm, vma')

    debugger.HandleCommand("command regex ref 's/(.+)/memory read --gdb-format 4gx *(long*)(%1)/'")
    print('Macros added: ref')


