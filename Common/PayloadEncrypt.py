# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-13 15:49
@Auth ： No2Cat
@File ：PayloadEncrypt.py
@IDE ：PyCharm
@DESC：
"""
from .RandXor import RandXor
import base64

def PayloadEncrypt(payload, password, m, s):
    rx = RandXor(password)
    payload = payload.replace('xxxxxxxxxxxxxxxxxxxxxxxxxxxx', s)
    PayloadB64 = base64.b64encode(payload.encode('utf-8'))
    p_enc = rx.encrypt(PayloadB64)
    pm_enc = p_enc[0:m] + rx.magic_str + p_enc[m:]
    return pm_enc

# if __name__ == '__main__':
#     PayloadEncrypt(SSp, 'pass', 12)