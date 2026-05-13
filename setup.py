from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="frp-file-sender",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="基于frp的大文件点对点传输工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/frp-file-sender",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiofiles>=23.2.1",
        "aiohttp>=3.9.1",
        "websockets>=12.0",
        "pyyaml>=6.0.1",
        "tqdm>=4.66.1",
        "requests>=2.31.0",
        "cryptography>=41.0.7",
    ],
    entry_points={
        "console_scripts": [
            "filep2p-send=server.main:main",
            "filep2p-recv=client.main:main",
        ],
    },
)