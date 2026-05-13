"""
流式服务器测试
"""

import os
import sys
import time
import threading
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.stream_server import StreamServer


class TestStreamServer(unittest.TestCase):
    """流式服务器测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        # 创建临时目录
        cls.temp_dir = tempfile.mkdtemp(prefix='filep2p_test_')
        
        # 创建测试文件
        cls.test_files = {}
        
        # 小文件 (1KB)
        small_file = os.path.join(cls.temp_dir, 'small.txt')
        with open(small_file, 'w') as f:
            f.write('Hello, World!' * 100)
        cls.test_files['small.txt'] = small_file
        
        # 中等文件 (1MB)
        medium_file = os.path.join(cls.temp_dir, 'medium.bin')
        with open(medium_file, 'wb') as f:
            f.write(b'\x00' * 1024 * 1024)
        cls.test_files['medium.bin'] = medium_file
        
        # 启动服务器
        cls.server = StreamServer(
            host='127.0.0.1',
            port=18848,
            share_dir=cls.temp_dir
        )
        
        cls.server_thread = threading.Thread(
            target=cls.server.start,
            daemon=True
        )
        cls.server_thread.start()
        time.sleep(1)  # 等待服务器启动
    
    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        cls.server.stop()
        
        # 清理临时文件
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def test_server_running(self):
        """测试服务器是否在运行"""
        self.assertTrue(self.server.running)
    
    def test_file_list_api(self):
        """测试文件列表API"""
        import requests
        
        response = requests.get('http://127.0.0.1:18848/api/files')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('files', data)
        self.assertTrue(len(data['files']) >= 2)
    
    def test_download_small_file(self):
        """测试下载小文件"""
        import requests
        
        response = requests.get(
            'http://127.0.0.1:18848/api/download/small.txt'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Hello, World!', response.text)
    
    def test_download_medium_file(self):
        """测试下载中等文件"""
        import requests
        
        response = requests.get(
            'http://127.0.0.1:18848/api/download/medium.bin',
            stream=True
        )
        self.assertEqual(response.status_code, 200)
        
        # 验证大小
        content = b''
        for chunk in response.iter_content(8192):
            content += chunk
        
        self.assertEqual(len(content), 1024 * 1024)
    
    def test_range_request(self):
        """测试Range请求（断点续传基础）"""
        import requests
        
        headers = {'Range': 'bytes=0-99'}
        response = requests.get(
            'http://127.0.0.1:18848/api/download/medium.bin',
            headers=headers
        )
        
        self.assertEqual(response.status_code, 206)
        self.assertEqual(len(response.content), 100)
    
    def test_file_not_found(self):
        """测试404错误"""
        import requests
        
        response = requests.get(
            'http://127.0.0.1:18848/api/download/nonexistent.txt'
        )
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()