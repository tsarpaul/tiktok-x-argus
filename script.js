var mod = Process.getModuleByName("libmetasec_ov.so");
var baseAddr = mod.base;
var sz = mod.size;
console.log(baseAddr);
console.log(sz);

// for every 100 bytes, try place a breakpoint
for (var i = 0; i < sz; i += 1000) {
    var addr = baseAddr.add(i);
    try{
    Interceptor.attach(addr, {
        onEnter: function(args) {
            console.log("Hit: " + addr);
            var offset = addr - baseAddr;
            if(offset == 1511000){
                // dump the memory at the address
                console.log(hexdump(addr.sub(24), {
                    offset: 0,
                    length: 64,
                    header: true,
                    ansi: true
                }));
            }
        }
    });
    console.log("Attached: " + addr);
    } catch(err){}
}

