# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-13 10:13
@Auth ： No2Cat
@File ：BasicInfo.py
@IDE ：PyCharm
@DESC：
"""
import platform
import os
import socket
from pathlib import Path
import ctypes

def get_system_info():
    system_info = {}

    # 获取操作系统及版本
    system_info['os'] = platform.system()
    system_info['os_info'] = platform.platform()
    system_info['os_version'] = platform.version()

    # 获取硬盘信息（仅 Windows）
    if system_info['os'] == 'Windows':
        disk_info = []
        drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{d}:").exists()]
        for drive in drives:
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            used_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(drive), None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes))
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
    else:
        system_info['disk_info'] = ['/']
    # 获取当前路径
    system_info['current_path'] = os.getcwd()

    # 获取网卡信息
    net_info = []
    hostname = socket.gethostname()
    addresses = socket.getaddrinfo(hostname, None)
    for addr in addresses:
        if addr[0] == socket.AF_INET:  # 仅获取 IPv4 地址
            net_info.append({
                'interface': addr[4][0],
                'ip_address': addr[4][0]
            })
    system_info['net_info'] = net_info

    # 获取环境变量
    system_info['env_vars'] = dict(os.environ)

    return system_info

# 运行并打印结果
if __name__ == "__main__":
    info = get_system_info()
    for key, value in info.items():
        print(f"{key}: {value}")