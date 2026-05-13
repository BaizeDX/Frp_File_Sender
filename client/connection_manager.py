"""
连接管理器
处理与发送端的连接
"""

import socket
import requests
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger


class ConnectionManager:
    """管理与发送端的连接"""
    
    def __init__(self):
        self.logger = setup_logger('ConnectionManager', 'logs/connection.log')
        self.connected = False
        self.server_url = None
        self.server_info = None
    
    def connect(self, host, port, access_code=None, use_https=False):
        """
        连接到发送端服务器
        
        Args:
            host: 服务器地址（IP或域名）
            port: 端口号
            access_code: 访问码（可选）
            use_https: 是否使用HTTPS
        
        Returns:
            (bool, str) 成功标志和消息
        """
        try:
            # 标准化地址
            if not host.startswith('http'):
                protocol = 'https' if use_https else 'http'
                host = f"{protocol}://{host}"
            
            self.server_url = f"{host}:{port}"
            
            # 测试连接
            self.logger.info(f"正在连接到 {self.server_url}")
            
            response = requests.get(
                f"{self.server_url}/api/stats",
                timeout=10
            )
            
            if response.status_code == 200:
                self.server_info = response.json()
                self.connected = True
                self.logger.info(f"连接成功: {self.server_url}")
                return True, f"已连接到 {self.server_url}"
            else:
                return False, f"服务器返回: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "连接超时，请检查地址和端口是否正确"
        except requests.exceptions.ConnectionError:
            return False, "无法连接，请确认服务器是否在运行"
        except Exception as e:
            self.logger.error(f"连接错误: {e}")
            return False, f"连接失败: {str(e)}"
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
        self.server_url = None
        self.server_info = None
        self.logger.info("已断开连接")
    
    def get_file_list(self, search=None, sort_by='name'):
        """
        获取服务器文件列表
        
        Returns:
            list: 文件信息列表
        """
        if not self.connected:
            return []
        
        try:
            params = {}
            if search:
                params['search'] = search
            if sort_by:
                params['sort'] = sort_by
            
            response = requests.get(
                f"{self.server_url}/api/files",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('files', [])
            else:
                self.logger.error(f"获取文件列表失败: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"获取文件列表错误: {e}")
            return []
    
    def download_file(self, file_url, save_path, progress_callback=None):
        """
        下载文件（使用服务器端相对路径）
        
        Args:
            file_url: 文件下载URL或文件名
            save_path: 保存路径
            progress_callback: 进度回调
        
        Returns:
            (bool, str, str) 成功标志、消息、文件路径
        """
        if not self.connected:
            return False, "未连接", None
        
        try:
            # 如果是文件名，构建完整URL
            if not file_url.startswith('http'):
                file_url = f"{self.server_url}/api/download/{file_url}"
            
            # 使用流式下载
            from client.downloader import StreamDownloader
            downloader = StreamDownloader()
            
            return downloader.download(
                url=file_url,
                save_path=save_path,
                progress_callback=progress_callback
            )
            
        except Exception as e:
            self.logger.error(f"下载错误: {e}")
            return False, f"下载失败: {str(e)}", None
    
    def get_server_stats(self):
        """获取服务器统计信息"""
        if not self.connected:
            return None
        
        try:
            response = requests.get(
                f"{self.server_url}/api/stats",
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            self.logger.error(f"获取统计信息错误: {e}")
            return None
    
    def ping(self):
        """测试连接是否存活"""
        if not self.connected:
            return False
        
        try:
            response = requests.get(
                f"{self.server_url}/api/stats",
                timeout=3
            )
            return response.status_code == 200
        except:
            return False