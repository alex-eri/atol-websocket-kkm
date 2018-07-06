#!/usr/bin/python
# -*- coding:utf-8 -*-

import json
import os
import signal
import sys
import time

import serial

from websocket_server import WebsocketServer

if sys.version[0] == '2':
    reload(sys)
#pylint: disable-msg=E1101
    sys.setdefaultencoding("utf-8")

exit = False

def display(caption):
    if len(sys.argv) > 1:
        p = serial.Serial('/dev/' + sys.argv[1], 9600)
        try:
            model = 1
            if len(sys.argv) > 2:
                model = int(sys.argv[2])
            if model == 1:
                p.write('\x1B\x3D\x02\x1B\x74\x06\x1B\x52\x00\x0C')
            else:
                p.write('\x1B\x3D\x02\x1B\x74\x07\x1B\x52\x00\x0C')
            p.write(str(caption).encode('cp866'))
            p.flushOutput()
            p.close()
        except:
            pass

def processMessage(client, server, message):
    try:
        data = json.loads(message)

        if (data['method'] == 'display'):
            # Вывести что-то на дисплей покупателя
            display(data['data'])
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
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

    # 2x20 - две строки по 20 символов
    display('****************************************')

    server = WebsocketServer(9112, '0.0.0.0')
    server.set_fn_message_received(processMessage)

    server.run_forever()

except Exception as e:
    print(str(e))
    exit = True
    sys.exit()
