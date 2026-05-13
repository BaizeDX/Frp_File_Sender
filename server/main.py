"""
发送端服务器入口（增强版 - 支持智能路由、自动打开浏览器）
"""

import os
import sys
import signal
import argparse
import threading
import time as time_module
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger
from shared.network_utils import NetworkDetector, quick_check, get_local_ip
from server.stream_server import StreamServer
from server.discovery import DiscoveryService
from server.tunnel_manager import TunnelManager


def main():
    parser = argparse.ArgumentParser(
        description='FileP2P Sender - 大文件点对点传输发送端',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                                    # 智能模式启动
  %(prog)s --dir ./files                      # 指定共享目录
  %(prog)s --port 9000 --no-discover          # 自定义端口
  %(prog)s --tunnel                           # 强制启用frp
  %(prog)s --check 192.168.1.100             # 检测目标IP
  %(prog)s --scan                             # 扫描局域网设备
  %(prog)s --no-browser                       # 不自动打开浏览器
        """
    )
    
    parser.add_argument(
        '--dir', '-d',
        default='./files',
        help='要共享的文件夹路径 (默认: ./files)'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8848,
        help='服务器端口 (默认: 8848)'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='绑定地址 (默认: 0.0.0.0)'
    )
    parser.add_argument(
        '--no-discover',
        action='store_true',
        help='禁用局域网自动发现'
    )
    parser.add_argument(
        '--tunnel',
        action='store_true',
        help='强制启用frp远程访问隧道'
    )
    parser.add_argument(
        '--auto-tunnel',
        action='store_true',
        help='自动判断是否需要隧道（智能模式）'
    )
    parser.add_argument(
        '--access-code',
        help='设置访问码保护'
    )
    parser.add_argument(
        '--log-file',
        default='logs/server.log',
        help='日志文件路径'
    )
    parser.add_argument(
        '--check',
        metavar='IP',
        help='检查与目标IP的连接方式'
    )
    parser.add_argument(
        '--scan',
        action='store_true',
        help='扫描局域网内的FileP2P设备'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='不自动打开浏览器'
    )
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logger('FileP2P-Sender', args.log_file)
    
    # ==================== 扫描模式 ====================
    if args.scan:
        logger.info("正在扫描局域网内的FileP2P设备...")
        detector = NetworkDetector()
        devices = detector.scan_lan_devices(args.port)
        
        if devices:
            print(f"\n发现 {len(devices)} 个设备:")
            print("-" * 60)
            for device in devices:
                print(f"  IP: {device['ip']}")
                print(f"  信息: {device['info']}")
                print("-" * 60)
        else:
            print("未发现其他FileP2P设备")
        return
    
    # ==================== 检测模式 ====================
    if args.check:
        target_ip = args.check
        logger.info(f"检测目标IP: {target_ip}")
        
        result = quick_check(target_ip)
        
        print("\n" + "=" * 60)
        print("  网络连接分析")
        print("=" * 60)
        print(f"  目标IP: {target_ip}")
        print(f"  本机IP: {get_local_ip()}")
        print(f"  推荐模式: {result['mode']}")
        print(f"  原因: {result['reason']}")
        print(f"  预计速度: {result['estimated_speed']}")
        print(f"  建议: {result['recommendation']}")
        if result['mode'] == 'direct':
            print(f"  直连地址: {result.get('connection_url', 'N/A')}")
        print("=" * 60)
        print()
        return
    
    # ==================== 服务器模式 ====================
    logger.info("=" * 50)
    logger.info("FileP2P Sender 启动中...")
    logger.info("=" * 50)
    
    # 确保共享目录存在
    share_dir = os.path.abspath(args.dir)
    os.makedirs(share_dir, exist_ok=True)
    logger.info(f"共享目录: {share_dir}")
    
    # 网络检测
    detector = NetworkDetector()
    local_ip = detector.get_primary_ip()
    network_info = detector.get_local_network_info()
    
    logger.info(f"本机IP: {local_ip}")
    logger.info(f"网关: {network_info.get('default_gateway', '未知')}")
    
    # 显示所有网络接口
    print("\n网络接口:")
    for iface in network_info.get('interfaces', []):
        print(f"  {iface['name']}: {iface['ip']} ({iface['network']})")
    print()
    
    # 启动流式服务器
    server = StreamServer(
        host=args.host,
        port=args.port,
        share_dir=share_dir,
        access_code=args.access_code
    )
    
    # 启动局域网发现服务
    discovery = None
    if not args.no_discover:
        discovery = DiscoveryService(
            server_port=args.port,
            share_dir=share_dir
        )
        discovery.start()
        logger.info("局域网发现已启用")
    
    # 启动frp隧道
    tunnel = None
    use_tunnel = args.tunnel or args.auto_tunnel
    
    if use_tunnel:
        tunnel = TunnelManager(args.port)
        if tunnel.start():
            remote_url = tunnel.get_remote_url()
            logger.info(f"远程访问地址: {remote_url}")
            print(f"\n🔗 远程访问地址: {remote_url}")
        else:
            logger.error("frp隧道启动失败")
            if args.tunnel:
                logger.error("强制隧道模式，启动失败")
                sys.exit(1)
            else:
                logger.warning("自动隧道失败，仅提供局域网服务")
    
    # ===== 自动打开浏览器 =====
    local_url = f"http://127.0.0.1:{args.port}"
    
    if not args.no_browser:
        def open_browser():
            time_module.sleep(1.5)
            try:
                webbrowser.open(local_url)
                logger.info(f"浏览器已打开: {local_url}")
            except Exception as e:
                logger.warning(f"无法自动打开浏览器: {e}")
        
        threading.Thread(target=open_browser, daemon=True).start()
    
    # 处理退出信号
    def shutdown(signum, frame):
        logger.info("正在关闭服务...")
        server.stop()
        if discovery:
            discovery.stop()
        if tunnel:
            tunnel.stop()
        logger.info("服务已关闭")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    # 显示服务信息
    print("\n" + "=" * 60)
    print("  🚀 FileP2P 服务已启动")
    print("=" * 60)
    print(f"  本地地址: http://127.0.0.1:{args.port}")
    print(f"  局域网地址: http://{local_ip}:{args.port}")
    print(f"  Web界面: http://{local_ip}:{args.port}")
    print(f"  共享目录: {share_dir}")
    
    if args.access_code:
        print(f"  访问码: {args.access_code}")
    
    if tunnel and tunnel.get_remote_url():
        print(f"  远程地址: {tunnel.get_remote_url()}")
    
    print(f"\n  提示: 使用 --check <IP> 检测与目标设备的连接方式")
    print("  按 Ctrl+C 停止服务器")
    print("=" * 60)
    print()
    
    try:
        server.start()
    except KeyboardInterrupt:
        shutdown(None, None)
    except Exception as e:
        logger.error(f"服务器错误: {e}")
        shutdown(None, None)


if __name__ == '__main__':
    main()