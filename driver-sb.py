#!/usr/bin/python
# -*- coding:utf-8 -*-

import json
import os
import signal
import sys
import time
import urllib2
import glob

from websocket_server import WebsocketServer

if sys.version[0] == '2':
    reload(sys)
#pylint: disable-msg=E1101
    sys.setdefaultencoding("utf-8")

def file_get_contents(filename, use_include_path = 0, context = None, offset = -1, maxlen = -1):
    if (filename.find('://') > 0):
        ret = urllib2.urlopen(filename).read()
        if (offset > 0):
            ret = ret[offset:]
        if (maxlen > 0):
            ret = ret[:maxlen]
        return ret
    else:
        try:
            fp = open(filename, 'rb')
            try:
                if (offset > 0):
                    fp.seek(offset)
                ret = fp.read(maxlen)
                return ret
            finally:
                fp.close()
        except:
            pass

def processMessage(client, server, message):
    try:
        data = json.loads(message)

        if (data['method'] == 'exec'):
            os.system("cd /tmp/sb_pilot && rm -f *.rep e p && ./sb_pilot " + data['data'] + " 1>/dev/null 2>/dev/null")

            rep = glob.glob("/tmp/sb_pilot/*.rep")
            if len(rep):
                ser = rep[0].split('.')[0].split('/')
                ser = ser[len(ser) - 1]
            else:
                ser = False
            if ser:
                r = file_get_contents(rep[0]).decode('koi8-r').split('\n')
            else:
                r = ''

            e = file_get_contents('/tmp/sb_pilot/e')

            if not e:
                e = ''
            else:
                e = str(e).decode('koi8-r').split('\n')

            p = file_get_contents('/tmp/sb_pilot/p')
            if not p:
                p = ''
            else:
                p = str(p).decode('koi8-r').split('\n')

            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': { 'e': e, 'p': p, 's': ser, 'r': r } }))
            os.system("rm -f /tmp/sb_pilot/*.rep /tmp/sb_pilot/e /tmp/sb_pilot/p 1>/dev/null 2>/dev/null")
            return
            
        server.send_message(client, json.dumps({ 'result': 'ERR', 'method': data['method'], 'type': 'invalid', 'value': 'Unknown method' }))

    except Exception as e:
        server.send_message(client, json.dumps({ 'result': 'ERR', 'type': type(e).__name__, 'value': e.args[0] }))
    
def serviceShutdown(signum, frame):
    global exit

    exit = True
    sys.exit()

try:
    signal.signal(signal.SIGTERM, serviceShutdown)
    signal.signal(signal.SIGINT, serviceShutdown)    

    server = WebsocketServer(9113, '0.0.0.0')
    server.set_fn_message_received(processMessage)

    server.run_forever()

except Exception as e:
    print(str(e))
    exit = True
    sys.exit()
