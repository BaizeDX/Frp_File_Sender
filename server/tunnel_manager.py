"""
frp隧道管理器
"""

import os
import json
import time
import subprocess
import threading
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger


class TunnelManager:
    """管理frp隧道"""
    
    def __init__(self, local_port, config_dir='./config', frp_path='./frpc'):
        self.local_port = local_port
        self.config_dir = config_dir
        self.frp_path = frp_path
        self.logger = setup_logger('TunnelManager', 'logs/tunnel.log')
        
        self.frp_process = None
        self.remote_url = None
        self.tunnel_active = False
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
    
    def start(self, frp_server=None, frp_port=None, token=None, remote_port=None):
        """
        启动frp隧道
        
        Args:
            frp_server: frp服务器地址
            frp_port: frp服务器端口
            token: 认证令牌
            remote_port: 远程端口
        
        Returns:
            bool: 是否成功启动
        """
        try:
            # 加载或创建配置
            config_file = self._prepare_config(frp_server, frp_port, token, remote_port)
            
            if not config_file:
                self.logger.error("无法准备frp配置")
                return False
            
            # 检查frp客户端
            if not os.path.exists(self.frp_path):
                self.logger.error(f"frp客户端不存在: {self.frp_path}")
                return False
            
            # 启动frp进程
            self.logger.info("正在启动frp隧道...")
            
            self.frp_process = subprocess.Popen(
                [self.frp_path, '-c', config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待一小段时间检查是否启动成功
            time.sleep(2)
            
            if self.frp_process.poll() is not None:
                # 进程已退出
                stdout, stderr = self.frp_process.communicate()
                self.logger.error(f"frp启动失败: {stderr}")
                return False
            
            self.tunnel_active = True
            
            # 启动日志监控线程
            monitor_thread = threading.Thread(
                target=self._monitor_process,
                daemon=True
            )
            monitor_thread.start()
            
            # 读取远程地址
            self._extract_remote_url(frp_server, remote_port)
            
            self.logger.info(f"frp隧道启动成功: {self.remote_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动frp隧道错误: {e}")
            return False
    
    def stop(self):
        """停止frp隧道"""
        self.tunnel_active = False
        
        if self.frp_process:
            try:
                self.frp_process.terminate()
                time.sleep(1)
                
                if self.frp_process.poll() is None:
                    self.frp_process.kill()
                
                self.logger.info("frp隧道已停止")
            except Exception as e:
                self.logger.error(f"停止frp隧道错误: {e}")
            
            self.frp_process = None
            self.remote_url = None
    
    def get_remote_url(self):
        """获取远程访问地址"""
        return self.remote_url
    
    def _prepare_config(self, frp_server, frp_port, token, remote_port):
        """
        准备frp配置文件
        
        Returns:
            str: 配置文件路径
        """
        config_file = os.path.join(self.config_dir, 'frpc.ini')
        
        # 如果配置文件已存在，直接使用
        if os.path.exists(config_file):
            self.logger.info(f"使用现有配置: {config_file}")
            
            # 更新端口
            self._update_config_port(config_file)
            return config_file
        
        # 创建新配置
        if not frp_server or not frp_port:
            self.logger.error("缺少frp服务器信息")
            return None
        
        config_content = f"""[common]
server_addr = {frp_server}
server_port = {frp_port}
token = {token or ''}

admin_addr = 127.0.0.1
admin_port = 7400

log_file = ./logs/frpc.log
log_level = info
log_max_days = 3

[file-transfer]
type = tcp
local_ip = 127.0.0.1
local_port = {self.local_port}
remote_port = {remote_port or self.local_port}
use_encryption = true
use_compression = true
"""
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        self.logger.info(f"创建配置: {config_file}")
        return config_file
    
    def _update_config_port(self, config_file):
        """更新配置文件中的本地端口"""
        try:
            with open(config_file, 'r') as f:
                content = f.read()
            
            # 简单替换端口（实际应该用ini解析器）
            import re
            content = re.sub(
                r'local_port = \d+',
                f'local_port = {self.local_port}',
                content
            )
            
            with open(config_file, 'w') as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"更新配置错误: {e}")
    
    def _extract_remote_url(self, frp_server, remote_port):
        """从日志中提取远程地址"""
        # 如果没有提供frp服务器，从配置读取
        if not frp_server:
            config_file = os.path.join(self.config_dir, 'frpc.ini')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    for line in f:
                        if line.startswith('server_addr'):
                            frp_server = line.split('=')[1].strip()
        
        port = remote_port or self.local_port
        self.remote_url = f"http://{frp_server}:{port}"
    
    def _monitor_process(self):
        """监控frp进程"""
        while self.tunnel_active and self.frp_process:
            if self.frp_process.poll() is not None:
                self.logger.warning("frp进程意外退出")
                self.tunnel_active = False
                break
            
            # 读取输出
            try:
                line = self.frp_process.stdout.readline()
                if line:
                    self.logger.debug(f"frp: {line.strip()}")
            except:
                pass
            
            time.sleep(1)