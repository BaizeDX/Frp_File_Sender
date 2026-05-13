"""
HTTP工具函数
从原项目提取并增强
"""

import time
from email.utils import formatdate, parsedate_to_datetime
from datetime import datetime


def get_http_date(timestamp=None):
    """将时间戳转换为RFC 1123 HTTP日期格式"""
    if timestamp is None:
        timestamp = time.time()
    return formatdate(timestamp, usegmt=True)


def parse_if_modified_since(value):
    """解析If-Modified-Since头"""
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        return dt.timestamp()
    except Exception:
        return None


def parse_range_header(value, file_size):
    """
    解析Range请求头
    返回: (start, end) 或 None
    
    示例:
        "bytes=0-1023" -> (0, 1023)
        "bytes=1024-" -> (1024, file_size-1)
        "bytes=-2048" -> (file_size-2048, file_size-1)
    """
    if not value or not value.startswith('bytes='):
        return None
    
    try:
        range_str = value[6:]  # 去掉 "bytes="
        if '-' not in range_str:
            return None
        
        start_str, end_str = range_str.split('-', 1)
        
        if start_str == '':  # bytes=-2048
            suffix = int(end_str)
            if suffix > file_size:
                suffix = file_size
            return (file_size - suffix, file_size - 1)
        
        start = int(start_str)
        if start >= file_size:
            return None
        
        if end_str == '':  # bytes=1024-
            return (start, file_size - 1)
        
        end = int(end_str)
        if end >= file_size:
            end = file_size - 1
        
        if start > end:
            return None
        
        return (start, end)
        
    except (ValueError, IndexError):
        return None


def generate_boundary():
    """生成multipart边界字符串"""
    import uuid
    return f"----FileP2PBoundary{uuid.uuid4().hex}"


def format_content_disposition(filename, disposition='attachment'):
    """生成Content-Disposition头"""
    from urllib.parse import quote
    encoded_filename = quote(filename, safe='')
    return f'{disposition}; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}'