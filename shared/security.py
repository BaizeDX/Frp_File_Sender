"""
安全工具
"""

import os
import hashlib
import secrets
import string


def validate_file_path(base_dir, file_path):
    """
    验证文件路径安全性（防路径遍历攻击）
    从原项目提取
    
    返回: (bool, str) 是否安全, 解析后的绝对路径或错误信息
    """
    try:
        # 清理路径
        safe_path = file_path.lstrip('/')
        full_path = os.path.join(base_dir, safe_path)
        
        # 获取真实路径（解析符号链接）
        real_base = os.path.realpath(base_dir)
        real_file = os.path.realpath(full_path)
        
        # 安全检查：确保文件在基础目录内
        if os.path.commonpath([real_base, real_file]) != real_base:
            return False, "Access denied: path traversal detected"
        
        return True, real_file
        
    except Exception as e:
        return False, f"Path validation error: {str(e)}"


def sanitize_filename(filename):
    """
    清理文件名，移除危险字符
    """
    # 移除路径分隔符
    filename = filename.replace('/', '_').replace('\\', '_')
    # 移除空字节
    filename = filename.replace('\x00', '')
    # 限制长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    # 移除前后空格和点
    filename = filename.strip('. ')
    return filename or 'unnamed_file'


def generate_access_code(length=6):
    """
    生成随机访问码（用于保护传输）
    """
    alphabet = string.ascii_uppercase + string.digits
    # 移除容易混淆的字符
    alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def verify_access_code(stored_code, provided_code):
    """
    验证访问码（时间恒定比较，防时序攻击）
    """
    if not stored_code or not provided_code:
        return False
    return secrets.compare_digest(stored_code.upper(), provided_code.upper())


def calculate_file_hash(filepath, algorithm='sha256', chunk_size=8192):
    """
    计算文件哈希（支持大文件）
    """
    hash_obj = hashlib.new(algorithm)
    
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()