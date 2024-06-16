# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-13 13:40
@Auth ： No2Cat
@File ：RandXor.py
@IDE ：PyCharm
@DESC：
"""
import random
import base64
import hashlib

class RandXor(object):
    """ 加解密 """
    def __init__(self, shell_password, salt='mewoshell'):
        self.shell_password = shell_password
        self.salt = salt
        self.key = self.generate_key()
        self.rkey = len(self.shell_password)
        self.magic_str = self.get_magic_str()

    def get_md5(self, data):
        md5 = hashlib.md5()
        md5.update(data.encode('utf-8'))
        return md5.hexdigest()
    def generate_key(self):
        """ 异或key """
        return hashlib.sha256(self.get_md5(self.shell_password)[8:24].encode()).digest()

    def get_magic_str(self):
        return self.get_md5(str(self.shell_password + self.salt))[9:25]
    def encrypt(self, plaintext):
        plaintext = base64.b64decode(plaintext)
        ciphertext = bytearray(len(plaintext))
        random.seed(self.rkey)
        for i in range(len(plaintext)):
            ciphertext[i] = plaintext[i] ^ self.rkey
            ciphertext[i] = ciphertext[i] ^ (random.randint(1, len(plaintext)) & 0xff) ^ self.key[i % len(self.key)]
        ciphertext = base64.b64encode(ciphertext).decode('utf-8')
        return ciphertext

    def decrypt(self, ciphertext):
        ciphertext = base64.b64decode(ciphertext)
        plaintext = bytearray(len(ciphertext))
        random.seed(self.rkey)
        for i in range(len(ciphertext)):
            plaintext[i] = ciphertext[i] ^ (random.randint(1, len(ciphertext)) & 0xff) ^ self.key[i % len(self.key)]
            plaintext[i] = plaintext[i] ^ self.rkey
        plaintext = base64.b64encode(plaintext).decode('utf-8')
        return plaintext

payload = """
import os
resp = os.popen('whoami').read()
"""
if __name__ == '__main__':
    rx = RandXor('pass' , 'mewoshell')
    print('password:', 'pass', rx.get_md5('pass'))

    print('异或key（base64）:', base64.b64encode(rx.key).decode('utf-8'))
    print('随机数种子:', rx.rkey)
    print('magic_str:', rx.magic_str)


    payload = base64.b64encode(payload.encode('utf-8'))
    encrypted = rx.encrypt(payload)

    encrypted = 'oJsz0sm2gCoYCyHtylouU/BWcjQkCX1F6kNYoZjqon84pGquuT3260owCQjeC8iYfVe+uC+QPHkw2QrqzYWR2deJNHyWJZ/8ivpi1sF7/NhLJkfgkDEPcChm7ZpWYdDJmMeZS+xLBAMgDmgr8j9CsPN0F92JZA1OCQB4dLVMfLv6ET8Y6fnbZahadYPZbhqoYwg5CqIlVxgYUFT69u1htxo1BcKUeNWiQBAfDk5peX9JMWlPVDo1VmQiNcAHnA=='
    print('加密结果:', encrypted)


    print('解密结果:', base64.b64decode(rx.decrypt(encrypted)).decode('utf-8'))