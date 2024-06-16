# -*- coding: utf-8 -*-
"""
@Time ： 2024-06-12 4:18
@Auth ： No2Cat
@File ：logs.py
@IDE ：PyCharm
@DESC：
"""
import logging
import os

def get_logger(log_path, log_name) -> logging.Logger:
    # 指定日志文件的目录
    log_directory = log_path
    # 如果目录不存在，创建目录
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # 指定日志文件的路径
    log_file_path = os.path.join(log_directory, log_name)

    # 创建日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # 设置日志级别

    # 创建文件处理器，用于写入日志文件
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # 创建控制台处理器，用于输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建格式化器，并将其添加到处理器
    formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    # formatter = logging.Formatter('[%(asctime)s] - %(levelname)-8s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 将处理器添加到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class MyLogger:
    def __init__(self, log_file_path, log_file_name):
        self.logger = get_logger(log_file_path, log_file_name)

# 写入不同级别的日志信息
# logger.debug('这是一个调试信息')
# logger.info('这是一个信息')
# logger.warning('这是一个警告')
# logger.error('这是一个错误')
# logger.critical('这是一个严重错误')
