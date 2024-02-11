import frida, sys


def on_message(message, data):
    if message['type'] == 'send':
        print("[*] {0}".format(message['payload']))
    else:
        print(message)

with open('./enumerate.js') as f:
    jscode = f.read()

pid = int(sys.argv[1])
process = frida.get_usb_device().attach(pid)
script = process.create_script(jscode)
script.on('message', on_message)
print('[*] Running')
script.load()
sys.stdin.read()


