"""
生成测试文件
"""

import os
import argparse
import time
from pathlib import Path


def generate_test_file(filepath, size_bytes, pattern='random'):
    """
    生成指定大小的测试文件
    
    Args:
        filepath: 输出文件路径
        size_bytes: 文件大小（字节）
        pattern: 填充模式 ('random', 'zero', 'increment')
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    
    print(f"生成测试文件: {filepath}")
    print(f"大小: {format_size(size_bytes)}")
    print(f"模式: {pattern}")
    
    start_time = time.time()
    
    chunk_size = 1024 * 1024  # 1MB块
    written = 0
    
    with open(filepath, 'wb') as f:
        while written < size_bytes:
            remaining = size_bytes - written
            current_chunk = min(chunk_size, remaining)
            
            if pattern == 'random':
                data = os.urandom(current_chunk)
            elif pattern == 'zero':
                data = b'\x00' * current_chunk
            elif pattern == 'increment':
                data = bytes([i % 256 for i in range(written, written + current_chunk)])
            else:
                data = b'\x00' * current_chunk
            
            f.write(data)
            written += current_chunk
            
            # 进度显示
            if size_bytes > 0:
                percent = written / size_bytes * 100
                print(f"\r进度: {percent:.1f}% ({format_size(written)}/{format_size(size_bytes)})", 
                      end='', flush=True)
    
    print()
    
    elapsed = time.time() - start_time
    speed = size_bytes / elapsed / 1024 / 1024 if elapsed > 0 else 0
    print(f"完成! 耗时: {elapsed:.1f}秒, 速度: {speed:.1f} MB/s")


def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def parse_size(size_str):
    """
    解析大小字符串
    支持: 100M, 1G, 500K, 1024
    """
    size_str = size_str.strip().upper()
    
    multipliers = {
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }
    
    if size_str[-1] in multipliers:
        number = float(size_str[:-1])
        return int(number * multipliers[size_str[-1]])
    else:
        return int(size_str)


def main():
    parser = argparse.ArgumentParser(
        description='生成测试文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --size 100M
  %(prog)s --size 1G --output test.bin
  %(prog)s --size 10G --pattern increment
        """
    )
    
    parser.add_argument(
        '--size', '-s',
        required=True,
        help='文件大小 (例如: 100M, 1G, 500K)'
    )
    parser.add_argument(
        '--output', '-o',
        default='test_file.bin',
        help='输出文件路径 (默认: test_file.bin)'
    )
    parser.add_argument(
        '--pattern', '-p',
        choices=['random', 'zero', 'increment'],
        default='zero',
        help='填充模式 (默认: zero)'
    )
    
    args = parser.parse_args()
    
    try:
        size = parse_size(args.size)
    except (ValueError, IndexError):
        print(f"错误: 无效的大小格式 '{args.size}'")
        print("使用格式: 100M, 1G, 500K")
        return
    
    generate_test_file(args.output, size, args.pattern)


if __name__ == '__main__':
    main()