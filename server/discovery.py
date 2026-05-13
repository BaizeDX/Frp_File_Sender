"""
UDP局域网发现服务
"""

import socket
import json
import threading
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger


class DiscoveryService:
    """局域网自动发现服务"""
    
    BROADCAST_PORT = 8849
    BROADCAST_INTERVAL = 5  # 秒
    
    def __init__(self, server_port, share_dir, device_name=None):
        self.server_port = server_port
        self.share_dir = share_dir
        self.device_name = device_name or socket.gethostname()
        self.running = False
        self.logger = setup_logger('Discovery', 'logs/discovery.log')
        
        # 广播socket
        self.broadcast_socket = None
        # 监听socket
        self.listen_socket = None
        
        self.broadcast_thread = None
        self.listen_thread = None
    
    def start(self):
        """启动发现服务"""
        self.running = True
        
        # 启动广播线程
        self.broadcast_thread = threading.Thread(
            target=self._broadcast_loop,
            daemon=True
        )
        self.broadcast_thread.start()
        
        # 启动监听线程
        self.listen_thread = threading.Thread(
            target=self._listen_loop,
            daemon=True
        )
        self.listen_thread.start()
        
        self.logger.info(f"发现服务启动: {self.device_name}")
    
    def stop(self):
        """停止发现服务"""
        self.running = False
        
        if self.broadcast_socket:
            self.broadcast_socket.close()
        if self.listen_socket:
            self.listen_socket.close()
        
        self.logger.info("发现服务停止")
    
    def _broadcast_loop(self):
        """广播循环"""
        try:
            self.broadcast_socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM
            )
            self.broadcast_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_BROADCAST, 1
            )
            self.broadcast_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )
            
            while self.running:
                try:
                    # 准备广播消息
                    message = {
                        'type': 'filep2p_discovery',
                        'device': self.device_name,
                        'port': self.server_port,
                        'share_dir': self.share_dir,
                        'version': '0.1.0'
                    }
                    
                    # 广播
                    data = json.dumps(message).encode('utf-8')
                    self.broadcast_socket.sendto(
                        data, 
                        ('255.255.255.255', self.BROADCAST_PORT)
                    )
                    
                    time.sleep(self.BROADCAST_INTERVAL)
                    
                except Exception as e:
                    self.logger.error(f"广播错误: {e}")
                    time.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"广播socket创建失败: {e}")
    
    def _listen_loop(self):
        """监听循环 - 接收其他设备的广播"""
        try:
            self.listen_socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM
            )
            self.listen_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )
            self.listen_socket.bind(('0.0.0.0', self.BROADCAST_PORT))
            self.listen_socket.settimeout(1.0)
            
            while self.running:
                try:
                    data, addr = self.listen_socket.recvfrom(1024)
                    message = json.loads(data.decode('utf-8'))
                    
                    if message.get('type') == 'filep2p_discovery':
                        # 发现其他设备
                        device_ip = addr[0]
                        
                        # 忽略自己的广播
                        if self._is_own_ip(device_ip):
                            continue
                        
                        self.logger.info(
                            f"发现设备: {message.get('device')} "
                            f"at {device_ip}:{message.get('port')}"
                        )
                        
                        # 这里可以触发回调或存储发现的设备
                        self._on_device_discovered(message, device_ip)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"监听错误: {e}")
                        
        except Exception as e:
            self.logger.error(f"监听socket创建失败: {e}")
    
    def _is_own_ip(self, ip):
        """检查是否是自己的IP"""
        try:
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            return ip in local_ips or ip == '127.0.0.1'
        except:
            return False
    
    def _on_device_discovered(self, device_info, device_ip):
        """设备发现回调（可被子类或外部处理）"""
        # 存储发现的设备
        if not hasattr(self, 'discovered_devices'):
            self.discovered_devices = {}
        
        device_key = f"{device_ip}:{device_info.get('port')}"
        self.discovered_devices[device_key] = {
            **device_info,
            'ip': device_ip,
            'last_seen': time.time()
        }
    
    def get_discovered_devices(self):
        """获取已发现的设备列表"""
        if not hasattr(self, 'discovered_devices'):
            return {}
        
        # 清理超时的设备
        current_time = time.time()
        active_devices = {}
        
        for key, device in self.discovered_devices.items():
            if current_time - device['last_seen'] < self.BROADCAST_INTERVAL * 3:
                active_devices[key] = device
        
        self.discovered_devices = active_devices
        return active_devices