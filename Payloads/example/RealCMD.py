

from flask import Flask, request, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

import threading, queue, subprocess, locale, time
default_coding = locale.getdefaultlocale()
session_dict = dict()
def read_output(terminal, outq):
    while session_dict.get('run'):
        try:
            line = terminal.stdout.readline()
            if line:
                outq.put(line.decode(locale.getpreferredencoding(), errors='replace'))
        except:
            pass

def read_error(terminal, outq):
    while session_dict.get('run'):
        try:
            errput = terminal.stderr.readline()
            if errput:
                outq.put(errput.decode(locale.getpreferredencoding(), errors='replace'))
        except:
            pass

def output_reader(terminal, outq):
    idle = 0
    while session_dict.get('run') and idle < 100000:
        write = session_dict.get('writeBuffer') if 'writeBuffer' in session_dict else ''
        # if 'writeBuffer' in session:
        #     print('session', session)
        if len(write) > 0:
            print('命令输入', write)
            terminal.stdin.write(write.encode(default_coding[-1]))
            terminal.stdin.flush()
            session_dict['writeBuffer'] = ''
            idle = 0
        else:
            idle += 1

        try:
            while not outq.empty():
                session_dict['readBuffer'] += outq.get(block=False)
        except queue.Empty:
            pass
        # print(idle)
        time.sleep(0.8)
    terminal.terminate()
    print('stop')

def create_terminal(binPath):
    session_dict['readBuffer'] = ''
    outq = queue.Queue()
    terminal = subprocess.Popen(binPath.split(' '), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    session_dict['run'] = True
    session_dict['taks_id'] = terminal.pid

    # 启动单独的线程来读取 stdout 和 stderr
    threading.Thread(target=read_output, args=(terminal, outq)).start()
    threading.Thread(target=read_error, args=(terminal, outq)).start()
    threading.Thread(target=output_reader, args=(terminal, outq)).start()


@app.route('/main', methods=['POST'])
def main():
    data = request.json
    session_id = request.cookies.get('session_id', str('thisiscookie'))
    type = data.get('type')
    binPath = data.get('binPath', "")
    cmd = data.get('cmd', "")
    result = dict()
    if type == 'create':
        create_terminal(binPath)
        result["status"] = "success"
        result["msg"] = "ok"
        result['taks_id']  = session_dict['taks_id']
    elif type == 'read':
        if 'readBuffer' in session_dict:
            readContent = session_dict.get('readBuffer')
            print(readContent)
            session_dict['readBuffer'] = ''
            result["status"] = "success"
            result["msg"] = readContent
        else:
            result["status"] = "fail"
            result["msg"] = "Virtual Terminal fail to start or timeout"
    elif type == 'write':
        session_dict['writeBuffer'] = cmd + '\n'
        # print('main函数write', session['writeBuffer'])
        # print('main函数write', cmd)
        result["status"] = "success"
        result["msg"] = "ok"
    elif type == 'stop':
        session_dict['run'] = False
        result["status"] = "stopped"
        result["msg"] = "ok"

    # print(result)
    return result

if __name__ == '__main__':
    app.run()

# import os
# import base64
# import json
# import subprocess
# import tempfile
# import time
# from threading import Thread, Lock
# from flask import Flask, request
#
# app = Flask(__name__)
# app.secret_key = 'your_secret_key'
#
# # 全局字典用于存储会话数据
# session_data = {}
# session_lock = Lock()
#
# def encrypt(data):
#     # 替换为你实际的加密逻辑
#     return data
#
# def get_safe_str(data):
#     try:
#         data.encode('gbk')
#         return data
#     except UnicodeEncodeError:
#         return data.encode('utf-8', errors='ignore').decode('utf-8')
#
# def create_process(bash_path, session_id):
#     def read_output(proc, win, output_file, error_file):
#         with session_lock:
#             session_data[session_id] = {
#                 'run': True,
#                 'readBuffer': '',
#                 'writeBuffer': ''
#             }
#
#         if win:
#             reader = open(output_file, "r+")
#             error = open(error_file, "r+")
#         else:
#             reader = proc.stdout
#             error = proc.stderr
#
#         idle = 0
#         while True:
#             with session_lock:
#                 print(idle)
#                 if not session_data[session_id]['run'] or idle >= 1000000:
#                     break
#                 write_buffer = session_data[session_id]['writeBuffer']
#
#             if write_buffer:
#                 try:
#                     proc.stdin.write(write_buffer.encode())
#                     proc.stdin.flush()
#                 except OSError as e:
#                     print(f"写入stdin时发生错误: {e}")
#                     with session_lock:
#                         session_data[session_id]['run'] = False
#                 with session_lock:
#                     session_data[session_id]['writeBuffer'] = ''
#                 idle = 0
#             else:
#                 idle += 1
#
#             output = reader.read(10240)
#             if output:
#                 output = get_safe_str(output)
#                 with session_lock:
#                     session_data[session_id]['readBuffer'] += output
#
#             errput = error.read(10240)
#             if errput:
#                 errput = get_safe_str(errput)
#                 with session_lock:
#                     session_data[session_id]['writeBuffer'] = ''
#                     session_data[session_id]['readBuffer'] += errput
#
#             time.sleep(0.8)
#
#         reader.close()
#         error.close()
#         if win:
#             os.remove(output_file)
#             os.remove(error_file)
#
#     win = os.name == 'nt'
#     if win:
#         output_file = os.path.join(tempfile.gettempdir(), f"{os.getpid()}_output.txt")
#         if not os.path.exists(output_file):
#             file = open(output_file, 'w').close()
#         error_file = os.path.join(tempfile.gettempdir(), f"{os.getpid()}_error.txt")
#         if not os.path.exists(error_file):
#             file = open(error_file, 'w').close()
#         proc = subprocess.Popen(bash_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
#     else:
#         proc = subprocess.Popen(bash_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env={'TERM': 'xterm'})
#
#     # 创建并启动线程
#     reader_thread = Thread(target=read_output, args=(proc, win, output_file, error_file))
#     reader_thread.start()
#
# @app.route('/main', methods=['POST'])
# def main():
#     result = {}
#     data = request.json
#     session_id = request.cookies.get('session_id', str(os.urandom(24).hex()))
#     type = data.get('type')
#     bash_path = data.get('bashPath', "")
#     cmd = data.get('cmd', "")
#     whatever = data.get('whatever', "")
#
#     if type == "create":
#         create_process(bash_path, session_id)
#         result["status"] = "success"
#         result["msg"] = "ok"
#     elif type == "read":
#         with session_lock:
#             if 'readBuffer' in session_data.get(session_id, {}):
#                 read_content = session_data[session_id]['readBuffer']
#                 session_data[session_id]['readBuffer'] = session_data[session_id]['readBuffer'][len(read_content):]
#                 result["status"] = "success"
#                 result["msg"] = read_content
#             else:
#                 result["status"] = "fail"
#                 result["msg"] = "虚拟终端启动失败或超时"
#     elif type == "write":
#         cmd = base64.b64decode(cmd).decode()
#         with session_lock:
#             session_data[session_id]['writeBuffer'] = cmd
#         result["status"] = "success"
#         result["msg"] = "ok"
#     elif type == "stop":
#         with session_lock:
#             session_data[session_id]['run'] = False
#         result["status"] = "success"
#         result["msg"] = "已停止"
#
#     result["status"] = base64.b64encode(result["status"].encode()).decode()
#     result["msg"] = base64.b64encode(result["msg"].encode()).decode()
#     response = app.response_class(
#         response=encrypt(json.dumps(result)),
#         status=200,
#         mimetype='application/json'
#     )
#     response.set_cookie('session_id', session_id)
#     return response
#
# if __name__ == '__main__':
#     app.run()
