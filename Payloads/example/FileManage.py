# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-15 23:02
@Auth ： No2Cat
@File ：FileManage.py
@IDE ：PyCharm
@DESC：
"""
from pathlib import Path
import os, stat, shutil, json, platform, uuid, base64
from datetime import datetime

file_block_content = dict()


def X_getDisk():
    import ctypes
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
    return disk_info


def get_permission_info(mode):
    is_readable = bool(mode & stat.S_IRUSR)
    is_writable = bool(mode & stat.S_IWUSR)
    is_executable = bool(mode & stat.S_IXUSR)
    return {
        'readable': is_readable,
        'writable': is_writable,
        'executable': is_executable
    }


def get_directory_details(directory_path):
    try:
        # 获取目录中的所有文件和子目录
        items = os.listdir(directory_path)

        # 存储目录详情的列表
        details = []

        for item in items:
            item_path = os.path.join(directory_path, item)
            # 获取文件/目录的元数据
            item_info = os.stat(item_path)

            # 获取详细信息
            item_details = {
                'name': item,
                'path': item_path,
                'size': item_info.st_size,  # 文件大小，单位为字节
                'created': datetime.fromtimestamp(item_info.st_ctime).strftime('%Y/%m/%d %H:%M:%S'),  # 创建时间
                'modified': datetime.fromtimestamp(item_info.st_mtime).strftime('%Y/%m/%d %H:%M:%S'),  # 修改时间
                'is_directory': os.path.isdir(item_path),  # 是否是目录
                'permissions': get_permission_info(item_info.st_mode)  # 权限信息
            }
            details.append(item_details)
        return details
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def make_directory(directory_path):
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            return True
        except Exception as e:
            return str(e)


def create_file(file_path, mode):
    result = dict()
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    if os.path.exists(file_path):
        result['status'] = 'error'
        result['msg'] = 'File already exists'
    else:
        with open(file_path, mode) as file:
            pass
        result['status'] = 'success'
        result['msg'] = str(file_path)
    return result


def delete_path(path):
    result = dict()
    if os.path.exists(path):
        if os.path.isfile(path):
            os.remove(path)
            result['status'] = 'success'
            result['msg'] = 'File deleted'
        elif os.path.isdir(path):
            shutil.rmtree(path)
            result['status'] = 'success'
            result['msg'] = 'Directory deleted'
    else:
        result['status'] = 'error'
        result['msg'] = 'File does not'
    return result


def upload_file(file_path, mode, content, file_id):
    result = dict()
    result['file_id'] = file_id
    # 判断文件路径
    try:
        cf = create_file(file_path, mode)
        with open(file_path, mode) as file:
            file.write(content)
            result['status'] = 'success'
            result['msg'] = 'ok'
    except Exception as e:
        result['status'] = 'error'
        result['msg'] = str(e)
    return result


def read_file_as_binary(file_path):
    try:
        with open(file_path, 'rb') as file:
            binary_data = file.read()
        return binary_data
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
    except IOError:
        print(f"An error occurred while reading the file {file_path}.")


def split_and_encode_binary_data(binary_data, chunk_size=2 * 1024 * 1024):
    # 分割并编码二进制数据
    encoded_data_dict = {}
    total_size = len(binary_data)
    num_chunks = (total_size + chunk_size - 1) // chunk_size  # 计算分块数
    for i in range(num_chunks):
        chunk = binary_data[i * chunk_size: (i + 1) * chunk_size]
        encoded_chunk = base64.b64encode(chunk).decode('utf-8')
        encoded_data_dict[f'chunk_{i + 1}'] = encoded_chunk
    return encoded_data_dict


def download_file(file_path, file_id):
    result = dict()
    chunk_size = 2 * 1024 * 1024
    # chunk_size = 1024
    result['file_id'] = file_id
    try:
        file_size = os.path.getsize(file_path)
        if 'start_byte' not in file_block_content[file_id]:
            file_block_content[file_id] = {'start_byte': 0 , 'end_byte': chunk_size + 1, 'file_size': file_size, 'now_size': 0}
        start_byte = file_block_content[file_id]['start_byte']
        if start_byte < file_size:
            result['status'] = 'continue'
        else:
            result['status'] = 'success'
        with open(file_path, 'rb') as f:
            f.seek(start_byte)
            chunk = f.read(chunk_size)
            file_block_content[file_id]['start_byte'] += chunk_size
            file_block_content[file_id]['now_size'] += chunk_size
            encoded_chunk = base64.b64encode(chunk).decode()
        result['msg'] = encoded_chunk
    except FileNotFoundError as e:
        result['status'] = 'error'
        result['msg'] = str(e)
    return result


def X_file_manage_main(type='', path='', mode='w', file_id='', content=''):
    result = dict()
    if type == 'dir':
        details = get_directory_details(path)
        result['status'] = 'success'
        result['msg'] = details
    elif type == 'mkdir':
        result['msg'] = make_directory(path)
        if result['msg'] is True:
            result['status'] = 'success'
        else:
            result['status'] = 'error'
    elif type == 'touch':
        result = create_file(path, mode)
    elif type == 'del':
        result = delete_path(path)
    elif type == 'upload':
        content = base64.b64decode(content)
        if file_id == '':
            file_id = str(uuid.uuid4())
            file_block_content[file_id] = {'path': path, 'mode': mode}
        result = upload_file(path, mode, content, file_id)
    elif type == 'download':
        if file_id == '':
            file_id = str(uuid.uuid4())
            file_block_content[file_id] = {'path': path}
        result = download_file(path, file_id)

    return json.dumps(result)


# 目录遍历
node_path = "C:\\\\"
json_data = X_file_manage_main(type='dir', path=node_path)
print(json.loads(json_data))

# 分块下载示例用法
# file_path = "G:\WinPlayerN5-1214\Win网络播放器N5-1214.exe"
# file_id = ''
# flag = True
# all_chunks = []
# while flag:
#     result = X_file_manage_main(type='download', path=file_path, file_id=file_id)
#     result = json.loads(result)
#     print(result['msg'])
#     if result['status'] == 'continue':
#         file_id = result['file_id']
#         all_chunks.append(result['msg'])
#     elif result['status'] == 'success':
#         flag = False
#         print('完成')
# l_all = 0
# for chunk in all_chunks:
#     chunk = base64.b64decode(chunk)
#     l_all += len(chunk)
#     with open('C:\\text.exe', 'ab+') as f:
#         f.write(chunk)
# print(os.path.getsize(file_path))
# print(l_all)
# ======================================================
file_path = "G:\自动走砍,自动躲避技能原理揭秘.mp4"
binary_data = read_file_as_binary(file_path)

if binary_data:
    encoded_data_dict = split_and_encode_binary_data(binary_data)
    for key, value in encoded_data_dict.items():
        print(f"{key}: {len(value)} characters: ")

    file_path_2 = 'C:\\appverifUI.mp4'
    for value in encoded_data_dict.values():
        # content = base64.b64decode(value)
        X_file_manage_main(type='upload', path=file_path_2, mode='ab+', content=value)

# 上传示例用法
# contents = [b'12312312', b'123123123', b'546456456']
# file_id = ''
# for content in contents:
#     content = base64.encodebytes(content)
#     result = X_file_manage_main(type='upload', path='C:\\upload.txt', mode='ab', content=content, file_id=file_id)
#     if 'file_id' in json.loads(result):
#         file_id = json.loads(result)['file_id']
#     print(result)

# if platform.system().lower() == 'windows':
#     disk_info = X_getDisk()
# else:
#     disk_info = [{'device': '/'}]
#
# for disk in disk_info:
#     print('磁盘', disk['device'])
#     directory_info = get_directory_details(disk['device'])
#     for directory in directory_info:
#         # print(f'{directory['name']} {directory['size']} {directory['created'].strftime('%Y/%m/%d %H:%M:%S')}')
#         # print(directory['name'], directory['size'], directory['created'].strftime('%Y/%m/%d %H:%M:%S'))
#         print(directory)

# get_directory_details('C:\\')
# print(get_directory_details('C:\\'))
