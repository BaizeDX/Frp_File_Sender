"""
检查项目依赖
"""

import sys
import importlib
from pathlib import Path


# 必需的依赖包
REQUIRED_PACKAGES = {
    # 包名: (导入名, 最低版本, 用途)
    'requests': ('requests', '2.31.0', 'HTTP客户端'),
    'tqdm': ('tqdm', '4.66.1', '进度条'),
    'click': ('click', '8.1.7', '命令行工具'),
    'pyyaml': ('yaml', '6.0.1', 'YAML配置'),
    'cryptography': ('cryptography', '41.0.7', '加密工具'),
}

# 可选依赖
OPTIONAL_PACKAGES = {
    'aiohttp': ('aiohttp', '3.9.1', '异步HTTP服务器'),
    'websockets': ('websockets', '12.0', 'WebSocket支持'),
}

# 标准库模块
STANDARD_LIBRARY = {
    'os', 'sys', 'json', 'time', 'threading', 'socket',
    'hashlib', 'secrets', 'string', 'email', 'urllib',
    'subprocess', 'argparse', 'logging', 'unittest',
}


def check_package(package_name, import_name, min_version, description):
    """检查单个包"""
    try:
        module = importlib.import_module(import_name)
        
        # 尝试获取版本
        version = getattr(module, '__version__', '未知')
        
        return {
            'name': package_name,
            'import': import_name,
            'required': min_version,
            'installed': version,
            'status': '✅',
            'description': description,
        }
    except ImportError:
        return {
            'name': package_name,
            'import': import_name,
            'required': min_version,
            'installed': '未安装',
            'status': '❌',
            'description': description,
        }


def main():
    print("=" * 60)
    print("FileP2P 依赖检查")
    print("=" * 60)
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print()
    
    # 检查必需依赖
    print("【必需依赖】")
    print("-" * 60)
    missing = []
    
    for package_name, (import_name, min_version, description) in REQUIRED_PACKAGES.items():
        result = check_package(package_name, import_name, min_version, description)
        print(f"{result['status']} {result['name']:20s} {result['installed']:15s} "
              f"(要求>={result['required']}) - {result['description']}")
        
        if result['status'] == '❌':
            missing.append(result['name'])
    
    print()
    
    # 检查可选依赖
    print("【可选依赖】")
    print("-" * 60)
    
    for package_name, (import_name, min_version, description) in OPTIONAL_PACKAGES.items():
        result = check_package(package_name, import_name, min_version, description)
        status_icon = '✅' if result['status'] == '✅' else '⚠️'
        print(f"{status_icon} {result['name']:20s} {result['installed']:15s} "
              f"(要求>={result['required']}) - {result['description']}")
    
    print()
    
    # 检查项目文件结构
    print("【项目结构】")
    print("-" * 60)
    
    required_files = [
        'server/main.py',
        'server/stream_server.py',
        'client/main.py',
        'client/gui.py',
        'shared/__init__.py',
        'config/server_config.yaml',
        'web/index.html',
    ]
    
    base_dir = Path(__file__).parent.parent
    
    for file_path in required_files:
        full_path = base_dir / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 缺失")
    
    print()
    
    # 总结
    print("=" * 60)
    if missing:
        print(f"❌ 缺失 {len(missing)} 个必需依赖: {', '.join(missing)}")
        print("\n安装命令:")
        print(f"  pip install {' '.join(missing)}")
    else:
        print("✅ 所有必需依赖已安装")
    
    print("=" * 60)


if __name__ == '__main__':
    main()