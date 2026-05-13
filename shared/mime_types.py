"""
MIME类型映射
从原项目提取，新增了更多文件类型
"""

MIME_TYPES = {
    # 文本
    '.html': 'text/html; charset=utf-8',
    '.htm': 'text/html; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.xml': 'application/xml; charset=utf-8',
    '.csv': 'text/csv; charset=utf-8',
    '.md': 'text/markdown; charset=utf-8',
    
    # 图片
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    
    # 音视频
    '.mp4': 'video/mp4',
    '.avi': 'video/x-msvideo',
    '.mov': 'video/quicktime',
    '.mkv': 'video/x-matroska',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.flac': 'audio/flac',
    '.ogg': 'audio/ogg',
    
    # 文档
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    
    # 压缩文件
    '.zip': 'application/zip',
    '.rar': 'application/x-rar-compressed',
    '.7z': 'application/x-7z-compressed',
    '.tar': 'application/x-tar',
    '.gz': 'application/gzip',
    
    # 可执行文件
    '.exe': 'application/x-msdownload',
    '.msi': 'application/x-msdownload',
    '.apk': 'application/vnd.android.package-archive',
    '.dmg': 'application/x-apple-diskimage',
    
    # 代码
    '.py': 'text/x-python; charset=utf-8',
    '.java': 'text/x-java; charset=utf-8',
    '.cpp': 'text/x-c++src; charset=utf-8',
    '.sh': 'text/x-shellscript; charset=utf-8',
}


def get_mime_type(filepath):
    """根据文件扩展名返回MIME类型"""
    import os
    ext = os.path.splitext(filepath)[1].lower()
    return MIME_TYPES.get(ext, 'application/octet-stream')