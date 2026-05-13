"""
客户端入口
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger
from client.downloader import StreamDownloader
from client.resume_manager import ResumeManager


def main():
    parser = argparse.ArgumentParser(
        description='FileP2P Client - 文件下载客户端'
    )
    
    parser.add_argument(
        '--url', '-u',
        required=True,
        help='下载URL'
    )
    parser.add_argument(
        '--output', '-o',
        default='./downloads',
        help='保存目录 (默认: ./downloads)'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='禁用断点续传'
    )
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logger('FileP2P-Client', 'logs/client.log')
    
    # 创建下载器
    downloader = StreamDownloader()
    resume_mgr = ResumeManager()
    
    def progress_callback(downloaded, total, speed):
        """进度回调"""
        if total > 0:
            percent = downloaded / total * 100
        else:
            percent = 0
        
        speed_mb = speed / 1024 / 1024 if speed > 0 else 0
        
        # 格式化大小
        downloaded_str = format_size(downloaded)
        total_str = format_size(total) if total > 0 else '未知'
        
        print(f"\r下载进度: {percent:.1f}% ({downloaded_str}/{total_str}) "
              f"速度: {speed_mb:.1f} MB/s", end='')
    
    print(f"开始下载: {args.url}")
    print(f"保存到: {args.output}")
    
    success, message, file_path = downloader.download(
        url=args.url,
        save_path=args.output,
        resume=not args.no_resume,
        progress_callback=progress_callback
    )
    
    print()  # 换行
    
    if success:
        print(f"✅ {message}")
        print(f"文件保存到: {file_path}")
    else:
        print(f"❌ {message}")
        sys.exit(1)


def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


if __name__ == '__main__':
    main()