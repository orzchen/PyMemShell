# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-13 16:08
@Auth ： No2Cat
@File ：CommonUtils.py
@IDE ：PyCharm
@DESC：
"""
from .PayloadEncrypt import PayloadEncrypt
from .RandXor import RandXor
from .logs import MyLogger
import requests
import base64
import json
import time
import random
import string



proxies = {
    'http': 'http://127.0.0.1:6666'
}

def Logger():
    # 全局时间戳
    global_time_stamp = time.strftime("%Y%m%d", time.localtime()) # %Y%m%d%H%M%S
    # 指定日志文件的目录
    log_directory = 'logs/'
    # 指定日志文件的路径
    log_file_name = '{0}.log'.format(global_time_stamp)
    logger = MyLogger(log_directory, log_file_name).logger
    return logger
logger = Logger()

def generate_random_string(min_length, max_length):
    length = random.randint(min_length, max_length)
    letters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(letters) for _ in range(length))
    return random_string

def get_random_user_agent():
    browsers = [
        'Chrome',
        'Firefox',
        'Safari',
        'Edge'
    ]
    chrome_versions = ['91.0.4472', '90.0.4430', '89.0.4389']
    firefox_versions = ['89.0', '88.0', '87.0']
    safari_versions = ['14.0', '13.1', '13.0']
    edge_versions = ['91.0.864', '90.0.818', '89.0.774']

    operating_systems = [
        'Windows NT 10.0; Win64; x64',
        'Macintosh; Intel Mac OS X 10_15_7',
        'X11; Linux x86_64',
        'iPhone; CPU iPhone OS 14_6 like Mac OS X'
    ]

    browser = random.choice(browsers)
    if browser == 'Chrome':
        version = random.choice(chrome_versions)
    elif browser == 'Firefox':
        version = random.choice(firefox_versions)
    elif browser == 'Safari':
        version = random.choice(safari_versions)
    elif browser == 'Edge':
        version = random.choice(edge_versions)

    operating_system = random.choice(operating_systems)

    user_agent = f"Mozilla/5.0 ({operating_system}) AppleWebKit/537.36 (KHTML, like Gecko) {browser}/{version} Safari/537.36"
    return user_agent

def get_random_accept():
    accept_types = ['text/html', 'application/xhtml+xml', 'application/xml;q=0.9', 'image/webp', '*/*;q=0.8']
    return ', '.join(random.choices(accept_types, k=random.randint(1, len(accept_types))))

def get_random_headers():
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': get_random_accept(),
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    return headers


def basic_info(payload, url, password):
    m = random.randint(0, len(payload))
    s = generate_random_string(10, 100)
    try:
        p_enc = PayloadEncrypt(payload, password, m, s)
        resp = requests.post(url=url, data=p_enc, headers=get_random_headers(),proxies=proxies, verify=False)
        # if resp.status_code == 200:
        rx = RandXor(password)
        resp = rx.decrypt(resp.text)
        resp = base64.b64decode(resp).decode('utf-8')
        json_resp = json.loads(resp)
        return json_resp
    except Exception as e:
        logger.warning('[basic_info] Exception: {0}'.format(e))
        return None


