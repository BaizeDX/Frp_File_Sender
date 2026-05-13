"""
日志系统
从原项目提取并增强
"""

import os
import logging
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler


# 全局锁
log_lock = threading.Lock()


def setup_logger(name='FileP2P', log_file='logs/server.log', level=logging.INFO):
    """设置日志系统"""
    # 创建日志目录
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 防止重复添加处理器
    if logger.handlers:
        return logger
    
    # 文件处理器（自动轮转，每个文件最大10MB，保留5个备份）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def write_log(log_file, client_ip, method, path, status_code, file_size=None):
    """
    追加请求日志（线程安全）
    从原项目提取，增加了文件大小字段
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    size_str = f" | {file_size}" if file_size is not None else ""
    log_entry = f"{client_ip} | {timestamp} | {method} {path} | {status_code}{size_str}\n"
    
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    with log_lock:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)