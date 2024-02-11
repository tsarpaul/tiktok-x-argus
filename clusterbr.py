for i in range(0, 0xffa00, 0x500):
    lldb.debugger.HandleCommand(f'b -s libmetasec_ov.so -a {hex(i)} -C "bt" --one-shot 1 --auto-continue 1 -N libmetacluster')
