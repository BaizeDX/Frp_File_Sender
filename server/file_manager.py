"""
文件管理器
处理文件的索引、搜索、排序
"""

import os
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger
from shared.security import validate_file_path


class FileManager:
    """管理共享目录中的文件"""
    
    def __init__(self, share_dir):
        self.share_dir = os.path.abspath(share_dir)
        self.logger = setup_logger('FileManager', 'logs/file_manager.log')
        os.makedirs(self.share_dir, exist_ok=True)
    
    def get_file_list(self, search=None, sort_by='name', reverse=False):
        """获取文件列表，支持搜索和排序"""
        files = []
        
        try:
            for filename in os.listdir(self.share_dir):
                filepath = os.path.join(self.share_dir, filename)
                
                if not os.path.isfile(filepath):
                    continue
                
                # 搜索过滤
                if search and search.lower() not in filename.lower():
                    continue
                
                stat = os.stat(filepath)
                file_info = {
                    'name': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'extension': os.path.splitext(filename)[1].lower(),
                }
                files.append(file_info)
            
            # 排序
            if sort_by == 'name':
                files.sort(key=lambda x: x['name'].lower(), reverse=reverse)
            elif sort_by == 'size':
                files.sort(key=lambda x: x['size'], reverse=reverse)
            elif sort_by == 'modified':
                files.sort(key=lambda x: x['modified'], reverse=reverse)
            
            return files
            
        except Exception as e:
            self.logger.error(f"获取文件列表失败: {e}")
            return []
    
    def get_file_info(self, filename):
        """获取单个文件信息"""
        is_safe, filepath = validate_file_path(self.share_dir, filename)
        if not is_safe:
            return None
        
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            return None
        
        stat = os.stat(filepath)
        return {
            'name': filename,
            'path': filepath,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'extension': os.path.splitext(filename)[1].lower(),
        }
    
    def delete_file(self, filename):
        """删除文件"""
        is_safe, filepath = validate_file_path(self.share_dir, filename)
        if not is_safe:
            return False, "Access denied"
        
        if not os.path.exists(filepath):
            return False, "File not found"
        
        try:
            os.remove(filepath)
            self.logger.info(f"删除文件: {filename}")
            return True, "File deleted"
        except Exception as e:
            self.logger.error(f"删除文件失败: {e}")
            return False, str(e)
    
    def get_statistics(self):
        """获取共享目录统计信息"""
        total_files = 0
        total_size = 0
        file_types = {}
        
        try:
            for filename in os.listdir(self.share_dir):
                filepath = os.path.join(self.share_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    total_files += 1
                    total_size += stat.st_size
                    
                    ext = os.path.splitext(filename)[1].lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'file_types': file_types,
                'directory': self.share_dir
            }
            
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return None