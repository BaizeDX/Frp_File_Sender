"""快速测试网络检测功能"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.network_utils import NetworkDetector, quick_check, get_local_ip

detector = NetworkDetector()
print('本机IP:', get_local_ip())
print()

# 测试几个IP
test_ips = ['192.168.1.100', '10.0.0.5', '8.8.8.8']

for ip in test_ips:
    result = quick_check(ip)
    mode = result['mode']
    recommendation = result['recommendation']
    print(f'{ip}: {mode} - {recommendation}')

print()
print('=' * 60)
print('详细网络信息:')
print('=' * 60)

info = detector.get_local_network_info()
print(f'主机名: {info["hostname"]}')
print(f'默认网关: {info["default_gateway"]}')
print(f'DNS服务器: {info["dns_servers"]}')
print()
print('网络接口:')
for iface in info['interfaces']:
    print(f'  - {iface["name"]}: {iface["ip"]}')
    print(f'    子网: {iface["network"]}')