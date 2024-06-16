# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-13 22:53
@Auth ： No2Cat
@File ：CMD.py
@IDE ：PyCharm
@DESC：
"""
CMD = {
'os.popen': """
import os
import json
import locale
def execCommand(command):
    try:
        cmd_ref = os.popen(command).read()
        current_path = cmd_ref.splitlines()[-1]
    except Exception as e:
        cmd_ref = str(e)
        current_path = ''
    ec_info = {'success': True, 'cmd': cmd_ref, 'current_path': current_path, 'default_encoding': locale.getpreferredencoding()}
    return json.dumps(ec_info)
resp = execCommand('{0}'.format(str("%command%")))
""",

'subprocess.popen': """
import subprocess
import json
import locale
def execCommand(command):
    try:
        cmd_ref = subprocess.Popen(command,shell=True,stdout=-1,cwd=str("%current_path%")).communicate()[0].strip().decode(locale.getpreferredencoding(), errors='replace')
        current_path = cmd_ref.splitlines()[-1]
    except Exception as e:
        cmd_ref = str(e)
        current_path = ''
    ec_info = {'success': True, 'cmd': cmd_ref, 'current_path': current_path, 'default_encoding': locale.getpreferredencoding()}
    return json.dumps(ec_info)
resp = execCommand('{0}'.format(str("%command%")))
""",

'subprocess.run': """
import subprocess
import json
import locale
def execCommand(command):
    try:
        cmd_ref = subprocess.run(command, capture_output=True, shell=True, text=True).stdout
        current_path = cmd_ref.splitlines()[-1]
    except Exception as e:
        cmd_ref = str(e)
        current_path = ''
    ec_info = {'success': True, 'cmd': cmd_ref, 'current_path': current_path, 'default_encoding': locale.getpreferredencoding()}
    return json.dumps(ec_info)
resp = execCommand('{0}'.format(str("%command%")))
""",

'asyncio.exec': """
import asyncio
import json
import platform
import locale
class CommandRunner:
    def __init__(self):
        self.stdout = None
        self.stderr = None
        self.ec_info = None
    async def run_command(self, command):
        try:
            if platform.system().lower() == 'windows':
                process = await asyncio.create_subprocess_exec(
                    'cmd', '/C', command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    # 'bash', '-c', command,
                    'sh', '-c', command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            stdout, stderr = await process.communicate()
            self.stdout = stdout.decode(locale.getpreferredencoding(), errors='replace')
            cmd_ref = self.stdout
            current_path = cmd_ref.splitlines()[-1]
        except Exception as e:
            cmd_ref = str(e)
            current_path = ''       
        ec_info = {'success': True, 'cmd': cmd_ref, 'current_path': current_path, 'default_encoding': locale.getpreferredencoding()}
        self.ec_info = json.dumps(ec_info)
# 创建 CommandRunner 实例
runner = CommandRunner()
# 运行事件循环
asyncio.run(runner.run_command('{0}'.format(str("%command%"))))
resp = runner.ec_info
"""


}