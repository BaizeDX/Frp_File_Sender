"""
网络工具函数 - 纯Python实现（无需编译依赖）
用于检测网络拓扑、子网判断、网关检测
"""

import socket
import struct
import subprocess
import platform
import ipaddress
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger


class NetworkDetector:
    """网络拓扑检测器（纯Python实现）"""
    
    def __init__(self):
        self.logger = setup_logger('NetworkDetector', 'logs/network.log')
        self._cached_local_info = None
    
    def get_local_network_info(self):
        """
        获取本机网络信息
        
        Returns:
            dict: 网络信息
        """
        if self._cached_local_info:
            return self._cached_local_info
        
        info = {
            'hostname': socket.gethostname(),
            'interfaces': [],
            'default_gateway': None,
            'public_ip': None,
            'dns_servers': [],
        }
        
        try:
            # 获取所有IP地址
            hostname = socket.gethostname()
            all_ips = socket.gethostbyname_ex(hostname)[2]
            
            # 获取默认网关
            gateway = self._get_default_gateway()
            info['default_gateway'] = gateway
            
            # 为每个IP创建接口信息
            for ip in all_ips:
                if ip != '127.0.0.1':
                    interface_info = {
                        'name': self._get_interface_name(ip),
                        'ip': ip,
                        'netmask': self._get_netmask(ip),
                        'network': None,
                        'mac': None,
                        'is_wireless': self._is_wireless_interface(ip),
                    }
                    
                    # 计算网络地址
                    if interface_info['netmask']:
                        interface_info['network'] = self._calculate_network(
                            ip,
                            interface_info['netmask']
                        )
                    
                    info['interfaces'].append(interface_info)
            
            # 获取DNS服务器
            info['dns_servers'] = self._get_dns_servers()
            
        except Exception as e:
            self.logger.error(f"获取网络信息失败: {e}")
        
        self._cached_local_info = info
        return info
    
    def get_primary_ip(self):
        """获取主IP地址"""
        try:
            # 创建一个UDP socket来获取默认路由的IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.1)
            
            # 不需要实际连接，只是获取路由
            try:
                sock.connect(('8.8.8.8', 80))
                ip = sock.getsockname()[0]
                sock.close()
                return ip
            except:
                sock.close()
        except:
            pass
        
        # 备用方法：获取第一个非回环IP
        try:
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
            for ip in ips:
                if ip != '127.0.0.1':
                    return ip
        except:
            pass
        
        return '127.0.0.1'
    
    def get_all_local_ips(self):
        """获取所有本地IP"""
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname_ex(hostname)[2]
        except:
            return ['127.0.0.1']
    
    def is_same_subnet(self, target_ip, local_ip=None):
        """
        判断目标IP是否在同一子网
        
        Args:
            target_ip: 目标IP地址
            local_ip: 本地IP（可选，自动检测）
        
        Returns:
            (bool, str): 是否同一子网, 详细信息
        """
        try:
            target = ipaddress.IPv4Address(target_ip)
            
            if not target.is_private:
                return False, "目标IP为公网地址，需要内网穿透"
            
            if local_ip:
                local = ipaddress.IPv4Address(local_ip)
            else:
                local = ipaddress.IPv4Address(self.get_primary_ip())
            
            # 获取本机所有接口信息
            info = self.get_local_network_info()
            
            for interface in info['interfaces']:
                if interface['network']:
                    try:
                        network = ipaddress.IPv4Network(
                            interface['network'],
                            strict=False
                        )
                        
                        if target in network and local in network:
                            return True, f"同一子网: {interface['network']}"
                    except Exception:
                        pass
            
            # 更宽松的判断：检查是否在同一/24子网
            local_network = ipaddress.IPv4Network(
                f"{local}/24",
                strict=False
            )
            if target in local_network:
                return True, "同一/24子网"
            
            return False, "不同子网"
            
        except Exception as e:
            self.logger.error(f"子网判断错误: {e}")
            return False, f"无法判断: {str(e)}"
    
    def has_same_gateway(self, target_ip):
        """
        判断是否共享同一网关
        
        Returns:
            (bool, str)
        """
        try:
            # 检查是否在线
            if not self._is_host_reachable(target_ip):
                return False, "目标不可达"
            
            local_gateway = self._get_default_gateway()
            if not local_gateway:
                return False, "无法获取本地网关"
            
            is_same, msg = self.is_same_subnet(target_ip)
            
            if is_same:
                return True, f"同一子网，共享网关 {local_gateway}"
            else:
                return False, f"不同网关 (本地: {local_gateway})"
                
        except Exception as e:
            self.logger.error(f"网关检测错误: {e}")
            return False, str(e)
    
    def get_recommend_transfer_mode(self, target_ip):
        """
        智能推荐传输模式
        
        Returns:
            dict: {
                'mode': 'direct' | 'tunnel',
                'reason': str,
                'estimated_speed': str,
                'recommendation': str,
                'connection_url': str,
            }
        """
        # 检查是否为私有IP
        try:
            target = ipaddress.IPv4Address(target_ip)
            is_private = target.is_private
        except:
            is_private = False
        
        if not is_private:
            return {
                'mode': 'tunnel',
                'reason': '目标为公网地址',
                'estimated_speed': '1-10 MB/s (取决于frp服务器)',
                'recommendation': '🔵 需要使用frp远程访问',
                'connection_url': '通过frp服务器获取',
            }
        
        # 检查是否同一子网
        same_subnet, subnet_msg = self.is_same_subnet(target_ip)
        reachable = self._is_host_reachable(target_ip)
        
        if same_subnet:
            return {
                'mode': 'direct',
                'reason': subnet_msg,
                'estimated_speed': '100-1000 MB/s (局域网)',
                'recommendation': '✅ 推荐直连传输，速度最快',
                'connection_url': f'http://{self.get_primary_ip()}:8848',
            }
        elif reachable:
            return {
                'mode': 'direct',
                'reason': '目标可达但不同子网',
                'estimated_speed': '10-100 MB/s',
                'recommendation': '⚠️ 可尝试直连，但速度可能较慢',
                'connection_url': f'http://{self.get_primary_ip()}:8848',
            }
        else:
            return {
                'mode': 'tunnel',
                'reason': '目标不可达，需要内网穿透',
                'estimated_speed': '1-10 MB/s (取决于frp服务器)',
                'recommendation': '🔵 需要使用frp远程访问',
                'connection_url': '通过frp服务器获取',
            }
    
    def scan_lan_devices(self, port=8848, timeout=1):
        """
        扫描局域网内运行FileP2P的设备
        
        Returns:
            list: 发现的设备列表
        """
        devices = []
        info = self.get_local_network_info()
        
        # 获取所有本机IP
        local_ips = self.get_all_local_ips()
        
        for interface in info['interfaces']:
            if interface['network']:
                try:
                    network = ipaddress.IPv4Network(
                        interface['network'],
                        strict=False
                    )
                    
                    print(f"扫描网络: {interface['network']}")
                    
                    # 限制扫描范围
                    if network.num_addresses > 256:
                        # 只扫描/24子网
                        network = ipaddress.IPv4Network(
                            f"{interface['ip']}/24",
                            strict=False
                        )
                    
                    # 扫描子网内的IP
                    scanned = 0
                    for ip in network.hosts():
                        ip_str = str(ip)
                        
                        # 跳过自己
                        if ip_str in local_ips:
                            continue
                        
                        # 测试端口
                        if self._is_port_open(ip_str, port, timeout):
                            try:
                                import requests
                                response = requests.get(
                                    f'http://{ip_str}:{port}/api/stats',
                                    timeout=2
                                )
                                if response.status_code == 200:
                                    devices.append({
                                        'ip': ip_str,
                                        'info': response.json(),
                                    })
                                    print(f"  发现设备: {ip_str}")
                            except:
                                pass
                        
                        scanned += 1
                        if scanned % 50 == 0:
                            print(f"  已扫描: {scanned}")
                                
                except Exception as e:
                    self.logger.debug(f"扫描网络错误: {e}")
        
        return devices
    
    # ==================== 私有方法 ====================
    
    def _calculate_network(self, ip, netmask):
        """计算网络地址"""
        try:
            if not ip or not netmask:
                return None
            
            ip_int = struct.unpack('!I', socket.inet_aton(ip))[0]
            mask_int = struct.unpack('!I', socket.inet_aton(netmask))[0]
            network_int = ip_int & mask_int
            
            network_ip = socket.inet_ntoa(struct.pack('!I', network_int))
            cidr = bin(mask_int).count('1')
            
            return f"{network_ip}/{cidr}"
        except:
            return None
    
    def _get_default_gateway(self):
        """获取默认网关（纯Python + subprocess）"""
        system = platform.system()
        
        try:
            if system == 'Windows':
                return self._get_gateway_windows()
            elif system == 'Darwin':  # macOS
                return self._get_gateway_mac()
            else:  # Linux
                return self._get_gateway_linux()
        except Exception as e:
            self.logger.debug(f"获取网关失败: {e}")
            return None
    
    def _get_gateway_windows(self):
        """Windows获取默认网关"""
        try:
            # 方法1: 使用 route print
            output = subprocess.check_output(
                'route print 0.0.0.0',
                shell=True,
                text=True,
                encoding='gbk',
                errors='ignore'
            )
            
            # 解析输出
            lines = output.split('\n')
            for line in lines:
                if '0.0.0.0' in line and '0.0.0.0' not in line[line.index('0.0.0.0')+7:]:
                    # 提取IP
                    parts = line.strip().split()
                    for part in parts:
                        if self._is_valid_ip(part) and part != '0.0.0.0':
                            return part
            
            # 方法2: 使用 ipconfig
            output = subprocess.check_output(
                'ipconfig',
                shell=True,
                text=True,
                encoding='gbk',
                errors='ignore'
            )
            
            # 查找默认网关
            for line in output.split('\n'):
                if '默认网关' in line or 'Default Gateway' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        ip = parts[-1].strip()
                        if self._is_valid_ip(ip) and ip != '0.0.0.0':
                            return ip
            
        except Exception as e:
            self.logger.debug(f"Windows获取网关失败: {e}")
        
        return None
    
    def _get_gateway_mac(self):
        """macOS获取默认网关"""
        try:
            output = subprocess.check_output(
                ['netstat', '-rn'],
                text=True
            )
            
            for line in output.split('\n'):
                if 'default' in line.lower():
                    parts = line.split()
                    for part in parts:
                        if self._is_valid_ip(part):
                            return part
        except:
            pass
        
        return None
    
    def _get_gateway_linux(self):
        """Linux获取默认网关"""
        try:
            # 方法1: /proc/net/route
            with open('/proc/net/route', 'r') as f:
                for line in f:
                    fields = line.strip().split()
                    if fields[1] == '00000000':  # 默认路由
                        # 网关地址是十六进制的反向字节序
                        gw_hex = fields[2]
                        gw_bytes = bytes.fromhex(gw_hex)
                        gw = socket.inet_ntoa(gw_bytes[::-1])
                        if gw != '0.0.0.0':
                            return gw
            
            # 方法2: ip route
            output = subprocess.check_output(
                ['ip', 'route', 'show', 'default'],
                text=True
            )
            match = re.search(r'via\s+(\d+\.\d+\.\d+\.\d+)', output)
            if match:
                return match.group(1)
                
        except:
            pass
        
        return None
    
    def _get_netmask(self, ip):
        """获取指定IP的 netmask"""
        system = platform.system()
        
        try:
            if system == 'Windows':
                output = subprocess.check_output(
                    'ipconfig',
                    shell=True,
                    text=True,
                    encoding='gbk',
                    errors='ignore'
                )
                
                # 查找IP对应的子网掩码
                found_ip = False
                for line in output.split('\n'):
                    if ip in line:
                        found_ip = True
                    elif found_ip and ('子网掩码' in line or 'Subnet Mask' in line):
                        parts = line.split(':')
                        if len(parts) >= 2:
                            mask = parts[-1].strip()
                            if self._is_valid_ip(mask):
                                return mask
                        found_ip = False
            else:
                # Linux/macOS: 使用 ifconfig
                try:
                    output = subprocess.check_output(
                        ['ifconfig'],
                        text=True
                    )
                    
                    for line in output.split('\n'):
                        if ip in line:
                            # 查找netmask
                            match = re.search(r'netmask\s+([0-9a-fA-Fx\.]+)', output)
                            if match:
                                mask = match.group(1)
                                # 如果是十六进制格式，转换
                                if mask.startswith('0x'):
                                    mask_int = int(mask, 16)
                                    mask = socket.inet_ntoa(
                                        struct.pack('!I', mask_int)
                                    )
                                return mask
                except:
                    pass
        except:
            pass
        
        # 默认猜测
        if ip.startswith('192.168'):
            return '255.255.255.0'
        elif ip.startswith('10.'):
            return '255.0.0.0'
        elif ip.startswith('172.'):
            return '255.255.0.0'
        
        return '255.255.255.0'
    
    def _get_interface_name(self, ip):
        """获取接口名称"""
        system = platform.system()
        
        try:
            if system == 'Windows':
                output = subprocess.check_output(
                    'ipconfig',
                    shell=True,
                    text=True,
                    encoding='gbk',
                    errors='ignore'
                )
                
                current_adapter = 'Unknown'
                for line in output.split('\n'):
                    if '适配器' in line or 'adapter' in line.lower():
                        current_adapter = line.split(':')[0].strip()
                    elif ip in line:
                        return current_adapter
            else:
                try:
                    output = subprocess.check_output(
                        ['ifconfig'],
                        text=True
                    )
                    
                    current_iface = 'Unknown'
                    for line in output.split('\n'):
                        if line and not line.startswith('\t') and not line.startswith(' '):
                            current_iface = line.split(':')[0].strip()
                        elif ip in line:
                            return current_iface
                except:
                    pass
        except:
            pass
        
        return 'Network Interface'
    
    def _get_dns_servers(self):
        """获取DNS服务器"""
        dns_servers = []
        
        try:
            system = platform.system()
            
            if system == 'Windows':
                output = subprocess.check_output(
                    'ipconfig /all',
                    shell=True,
                    text=True,
                    encoding='gbk',
                    errors='ignore'
                )
                
                for line in output.split('\n'):
                    if 'DNS' in line and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            dns = parts[-1].strip()
                            if self._is_valid_ip(dns) and dns != '127.0.0.1':
                                dns_servers.append(dns)
            else:
                try:
                    with open('/etc/resolv.conf', 'r') as f:
                        for line in f:
                            if line.startswith('nameserver'):
                                parts = line.split()
                                if len(parts) >= 2:
                                    dns = parts[1]
                                    if dns and dns != '127.0.0.1':
                                        dns_servers.append(dns)
                except:
                    pass
        except:
            pass
        
        return dns_servers
    
    def _is_wireless_interface(self, ip):
        """判断是否为无线网卡"""
        try:
            system = platform.system()
            
            if system == 'Windows':
                output = subprocess.check_output(
                    'netsh wlan show interfaces',
                    shell=True,
                    text=True,
                    encoding='gbk',
                    errors='ignore'
                )
                return 'SSID' in output and ip in self._get_associated_ips(output)
            else:
                # Linux/macOS
                try:
                    output = subprocess.check_output(
                        ['iwconfig', '2>/dev/null'],
                        shell=True,
                        text=True
                    )
                    return 'ESSID' in output
                except:
                    pass
        except:
            pass
        
        return False
    
    def _get_associated_ips(self, text):
        """从文本中提取IP"""
        ips = []
        for match in re.finditer(r'\d+\.\d+\.\d+\.\d+', text):
            ips.append(match.group())
        return ips
    
    def _is_host_reachable(self, ip, timeout=2):
        """检查主机是否可达"""
        try:
            param = '-n' if platform.system() == 'Windows' else '-c'
            timeout_param = '-w' if platform.system() == 'Windows' else '-W'
            
            # Windows: ping -n 1 -w 2000 IP
            # Linux/Mac: ping -c 1 -W 2 IP
            if platform.system() == 'Windows':
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), ip]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 1
            )
            
            return result.returncode == 0
        except:
            return False
    
    def _is_port_open(self, ip, port, timeout=1):
        """检查端口是否开放"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    @staticmethod
    def _is_valid_ip(ip):
        """验证IP地址格式"""
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts)
        except:
            return False


# ==================== 便捷函数 ====================

def quick_check(target_ip):
    """
    快速检查目标IP的连接方式
    """
    detector = NetworkDetector()
    return detector.get_recommend_transfer_mode(target_ip)


def get_local_ip():
    """快速获取本地IP"""
    detector = NetworkDetector()
    return detector.get_primary_ip()