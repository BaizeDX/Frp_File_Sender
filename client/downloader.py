"""
流式下载器
支持大文件分块下载、断点续传、进度显示
"""

import os
import time
import hashlib
import requests
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger
from shared.security import sanitize_filename


class StreamDownloader:
    """流式下载器"""
    
    def __init__(self, chunk_size=65536):
        self.chunk_size = chunk_size  # 64KB
        self.logger = setup_logger('Downloader', 'logs/downloader.log')
    
    def download(self, url, save_path, filename=None, progress_callback=None, 
                 resume=True, verify_ssl=False):
        """
        下载文件
        
        Args:
            url: 下载URL
            save_path: 保存目录
            filename: 文件名（可选，从URL或响应头获取）
            progress_callback: 进度回调 callback(downloaded, total, speed)
            resume: 是否启用断点续传
            verify_ssl: 是否验证SSL证书
        
        Returns:
            (success, message, file_path)
        """
        # 准备保存路径
        if filename:
            filename = sanitize_filename(filename)
        else:
            filename = self._get_filename_from_url(url)
        
        os.makedirs(save_path, exist_ok=True)
        file_path = os.path.join(save_path, filename)
        temp_path = file_path + '.part'
        
        # 检查断点续传
        resume_pos = 0
        if resume and os.path.exists(temp_path):
            resume_pos = os.path.getsize(temp_path)
            self.logger.info(f"断点续传: 从 {resume_pos} 字节继续")
        
        # 准备请求头
        headers = {}
        if resume_pos > 0:
            headers['Range'] = f'bytes={resume_pos}-'
        
        # 发送请求
        try:
            response = requests.get(
                url,
                headers=headers,
                stream=True,
                verify=verify_ssl,
                timeout=(10, 300)  # (连接超时, 读取超时)
            )
            
            # 检查响应状态
            if response.status_code not in (200, 206):
                return False, f"服务器返回错误: {response.status_code}", None
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            if response.status_code == 206:
                total_size += resume_pos
            
            # 开始下载
            mode = 'ab' if resume_pos > 0 else 'wb'
            downloaded = resume_pos
            start_time = time.time()
            last_update = time.time()
            last_downloaded = downloaded
            
            with open(temp_path, mode) as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 进度回调
                        if progress_callback:
                            current_time = time.time()
                            if current_time - last_update > 0.1:  # 最多10次/秒
                                elapsed = current_time - start_time
                                speed = (downloaded - resume_pos) / elapsed if elapsed > 0 else 0
                                
                                if total_size > 0:
                                    percent = (downloaded / total_size) * 100
                                else:
                                    percent = 0
                                
                                progress_callback(downloaded, total_size, speed)
                                last_update = current_time
            
            # 下载完成，重命名文件
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(temp_path, file_path)
            
            # 验证大小
            if total_size > 0 and downloaded != total_size:
                return False, f"文件大小不匹配: 期望{total_size}, 实际{downloaded}", None
            
            elapsed = time.time() - start_time
            avg_speed = downloaded / elapsed if elapsed > 0 else 0
            self.logger.info(
                f"下载完成: {filename} "
                f"({downloaded} bytes, {avg_speed/1024/1024:.1f} MB/s)"
            )
            
            return True, "下载完成", file_path
            
        except requests.exceptions.Timeout:
            return False, "下载超时", None
        except requests.exceptions.ConnectionError:
            return False, "网络连接错误", None
        except Exception as e:
            self.logger.error(f"下载错误: {e}")
            return False, f"下载失败: {str(e)}", None
    
    def _get_filename_from_url(self, url):
        """从URL提取文件名"""
        from urllib.parse import urlparse, unquote
        
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = os.path.basename(path)
        
        if not filename:
            filename = 'downloaded_file'
        
        return sanitize_filename(filename)
    
    def verify_file(self, file_path, expected_hash=None, expected_size=None, algorithm='sha256'):
        """
        验证文件完整性
        
        Args:
            file_path: 文件路径
            expected_hash: 期望的哈希值
            expected_size: 期望的文件大小
            algorithm: 哈希算法
        
        Returns:
            (bool, str) 验证结果和消息
        """
        if not os.path.exists(file_path):
            return False, "文件不存在"
        
        # 验证大小
        if expected_size is not None:
            actual_size = os.path.getsize(file_path)
            if actual_size != expected_size:
                return False, f"大小不匹配: 期望{expected_size}, 实际{actual_size}"
        
        # 验证哈希
        if expected_hash is not None:
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    hash_obj.update(chunk)
            
            actual_hash = hash_obj.hexdigest()
            if actual_hash.lower() != expected_hash.lower():
                return False, f"哈希不匹配:\n期望: {expected_hash}\n实际: {actual_hash}"
        
        return True, "验证通过"