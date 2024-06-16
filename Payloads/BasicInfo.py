import platform
import os
import socket
from pathlib import Path
import ctypes
import json


def get_system_info():
    system_info = {}
    system_info['os'] = platform.system()
    system_info['os_info'] = platform.platform()
    system_info['os_version'] = platform.version()
    system_info['hostname'] = socket.gethostname()
    if system_info['os'] == 'Windows':
        disk_info = []
        drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{d}:").exists()]
        for drive in drives:
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            used_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(drive), None, ctypes.pointer(total_bytes),
                                                       ctypes.pointer(free_bytes))
            used_bytes.value = total_bytes.value - free_bytes.value
            percent = (used_bytes.value / total_bytes.value) * 100
            disk_info.append({
                'device': drive,
                'total': total_bytes.value,
                'used': used_bytes.value,
                'free': free_bytes.value,
                'percent': percent
            })
        system_info['disk_info'] = disk_info
        import win32api
        import win32security
        import ntsecuritycon
        user = win32api.GetUserName()
        sid = win32security.LookupAccountName(None, user)[0]
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), ntsecuritycon.TOKEN_READ)
        groups = win32security.GetTokenInformation(token, win32security.TokenGroups)
        group_name = win32security.LookupAccountSid(None, sid)[0]
        system_info['current_user'] = {
            'user': user,
            'group': group_name,
            'permissions': 'None'
        }
    else:
        import pwd
        import grp
        system_info['disk_info'] = ['/']
        current_user = pwd.getpwuid(os.getuid())
        current_group = grp.getgrgid(os.getgid())
        system_info['current_user'] = {
            'user': current_user.pw_name,
            'group': current_group.gr_name,
            'permissions': oct(os.stat(os.getcwd()).st_mode)[-3:]
        }
    system_info['current_path'] = os.getcwd()
    net_info = []
    hostname = socket.gethostname()
    addresses = socket.getaddrinfo(hostname, None)
    for addr in addresses:
        if addr[0] == socket.AF_INET:
            net_info.append({
                'interface': addr[4][0],
                'ip_address': addr[4][0]
            })
    system_info['net_info'] = net_info
    system_info['env_vars'] = dict(os.environ)
    system_info['success'] = True
    return system_info


try:
    resp = json.dumps(get_system_info())
except Exception as e:
    resp = str({'error': str(e)})
# ra = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'

print(resp)
