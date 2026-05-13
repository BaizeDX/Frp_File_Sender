"""
流式HTTP服务器
支持大文件传输，不会将整个文件加载到内存
"""

import os
import socket
import threading
import mimetypes
import json
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.mime_types import get_mime_type
from shared.http_utils import (
    get_http_date,
    parse_range_header,
    format_content_disposition
)
from shared.logger import write_log, setup_logger
from shared.security import validate_file_path, generate_access_code
from shared.network_utils import quick_check, get_local_ip


class StreamServer:
    """流式文件服务器"""

    def __init__(self, host='0.0.0.0', port=8848, share_dir='./files',
                 access_code=None, max_request_size=65536):
        self.host = host
        self.port = port
        self.share_dir = os.path.abspath(share_dir)
        self.access_code = access_code or generate_access_code()
        self.max_request_size = max_request_size
        self.running = False
        self.server_socket = None
        self.logger = setup_logger('StreamServer', 'logs/stream_server.log')

        self.stats = {
            'total_requests': 0,
            'active_transfers': 0,
            'bytes_sent': 0,
        }
        self.stats_lock = threading.Lock()
        self.web_dir = os.path.join(os.path.dirname(__file__), '..', 'web')

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(20)
        self.server_socket.settimeout(1.0)

        self.running = True
        self.logger.info(f"流式服务器启动在 {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, client_addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client,
                                 args=(client_socket, client_addr),
                                 daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"接受连接错误: {e}")

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

    # ==================== 核心处理 ====================

    def _handle_client(self, client_socket, client_addr):
        client_ip = client_addr[0]

        try:
            request_data = self._recv_http_request(client_socket)
            if not request_data:
                return

            request_line = request_data.split('\r\n')[0]
            parts = request_line.split()
            if len(parts) != 3:
                self._send_error(client_socket, 400, "Bad Request")
                return

            method, raw_path, version = parts
            method = method.upper()
            parsed = urlparse(raw_path)
            path = unquote(parsed.path)
            headers = self._parse_headers(request_data)

            self.logger.info(f"{client_addr} | {method} {path}")

            with self.stats_lock:
                self.stats['total_requests'] += 1

            # ==================== 路由 ====================
            if method == 'OPTIONS':
                self._handle_cors(client_socket)
            elif path in ('/', '', '/index.html'):
                self._serve_web_file(client_socket, 'index.html')
            elif path == '/api/files':
                self._handle_file_list(client_socket)
            elif path == '/api/share':
                self._handle_share(client_socket)
            elif path.startswith('/api/download/'):
                self._handle_download(client_socket, path, headers)
            elif path == '/api/stats':
                self._handle_stats(client_socket)
            elif path.startswith('/api/check'):
                self._handle_network_check(client_socket, raw_path)
            elif path.startswith('/web/'):
                self._serve_web_file(client_socket, path[5:])
            else:
                self._send_error(client_socket, 404, "Not Found")

        except Exception as e:
            self.logger.error(f"处理客户端错误: {e}")
            try:
                self._send_error(client_socket, 500, "Internal Server Error")
            except:
                pass
        finally:
            try:
                client_socket.close()
            except:
                pass

    def _recv_http_request(self, client_socket):
        data = b''
        client_socket.settimeout(5)
        try:
            while b'\r\n\r\n' not in data:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if len(data) > self.max_request_size:
                    break
        except socket.timeout:
            pass
        finally:
            client_socket.settimeout(10)
        return data.decode('utf-8', errors='replace')

    def _parse_headers(self, request_data):
        headers = {}
        lines = request_data.split('\r\n')
        for line in lines[1:]:
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        return headers

    # ==================== API 处理 ====================

    def _handle_file_list(self, client_socket):
        """返回文件列表"""
        files = []
        try:
            for filename in os.listdir(self.share_dir):
                filepath = os.path.join(self.share_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    from datetime import datetime
                    files.append({
                        'name': filename,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'type': mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                    })
        except Exception as e:
            self.logger.error(f"读取文件列表错误: {e}")

        response = json.dumps({
            'files': files,
            'server': 'FileP2P-StreamServer',
            'access_code': self.access_code
        }, ensure_ascii=False)
        self._send_json(client_socket, 200, response)

    def _handle_share(self, client_socket):
        """生成分享链接 - 扫描files文件夹"""
        try:
            files = []
            total_size = 0

            for filename in os.listdir(self.share_dir):
                filepath = os.path.join(self.share_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    files.append({
                        'name': filename,
                        'size': stat.st_size,
                    })
                    total_size += stat.st_size

            local_ip = get_local_ip()

            self._send_json(client_socket, 200, {
                'success': True,
                'message': f'共 {len(files)} 个文件，{self._format_size(total_size)}',
                'files': files,
                'file_count': len(files),
                'total_size': total_size,
                'local_url': f'http://{local_ip}:{self.port}',
                'access_code': self.access_code,
            })

        except Exception as e:
            self.logger.error(f"生成分享链接错误: {e}")
            self._send_json(client_socket, 500, {'error': str(e)})

    def _handle_download(self, client_socket, path, headers):
        """流式下载文件"""
        filename = path[len('/api/download/'):]
        is_safe, filepath = validate_file_path(self.share_dir, filename)
        if not is_safe:
            self._send_error(client_socket, 403, "Forbidden")
            return
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            self._send_error(client_socket, 404, "File not found")
            return

        file_size = os.path.getsize(filepath)
        mime_type = get_mime_type(filepath)
        range_info = parse_range_header(headers.get('range', ''), file_size)

        with self.stats_lock:
            self.stats['active_transfers'] += 1

        try:
            if range_info:
                start, end = range_info
                content_length = end - start + 1
                resp = (
                    "HTTP/1.1 206 Partial Content\r\n"
                    f"Content-Type: {mime_type}\r\n"
                    f"Content-Length: {content_length}\r\n"
                    f"Content-Range: bytes {start}-{end}/{file_size}\r\n"
                    f"Content-Disposition: {format_content_disposition(filename)}\r\n"
                    "Accept-Ranges: bytes\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    "Connection: close\r\n\r\n"
                )
                client_socket.sendall(resp.encode('ascii'))
                with open(filepath, 'rb') as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk = f.read(min(65536, remaining))
                        if not chunk:
                            break
                        client_socket.sendall(chunk)
                        remaining -= len(chunk)
                        with self.stats_lock:
                            self.stats['bytes_sent'] += len(chunk)
            else:
                resp = (
                    "HTTP/1.1 200 OK\r\n"
                    f"Content-Type: {mime_type}\r\n"
                    f"Content-Length: {file_size}\r\n"
                    f"Content-Disposition: {format_content_disposition(filename)}\r\n"
                    "Accept-Ranges: bytes\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    "Connection: close\r\n\r\n"
                )
                client_socket.sendall(resp.encode('ascii'))
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        client_socket.sendall(chunk)
                        with self.stats_lock:
                            self.stats['bytes_sent'] += len(chunk)
        except Exception as e:
            self.logger.error(f"文件传输错误: {e}")
        finally:
            with self.stats_lock:
                self.stats['active_transfers'] -= 1

    def _handle_stats(self, client_socket):
        """服务器统计"""
        with self.stats_lock:
            stats = self.stats.copy()
        self._send_json(client_socket, 200, json.dumps(stats))

    def _handle_network_check(self, client_socket, raw_path):
        """网络检测"""
        target_ip = None
        if '?' in raw_path:
            query_string = raw_path.split('?')[1].split(' ')[0]
            params = parse_qs(query_string)
            target_ip = params.get('target', [None])[0]

        if not target_ip:
            self._send_json(client_socket, 400, {
                'error': 'Missing target parameter',
                'usage': '/api/check?target=192.168.1.100'
            })
            return

        try:
            result = quick_check(target_ip)
            result['local_ip'] = get_local_ip()
            self._send_json(client_socket, 200, result)
        except Exception as e:
            self._send_json(client_socket, 500, {'error': str(e)})

    # ==================== Web 服务 ====================

    def _serve_web_file(self, client_socket, file_path):
        file_path = file_path.lstrip('/').replace('\\', '/')
        if not file_path:
            file_path = 'index.html'
        full_path = os.path.join(self.web_dir, file_path)

        try:
            real_web = os.path.realpath(self.web_dir)
            real_file = os.path.realpath(full_path)
            if os.path.commonpath([real_web, real_file]) != real_web:
                self._send_error(client_socket, 403, "Forbidden")
                return
        except:
            self._send_error(client_socket, 500, "Error")
            return

        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            self._send_error(client_socket, 404, f"File not found: {file_path}")
            return

        try:
            if file_path.endswith('.html'):
                ct = 'text/html; charset=utf-8'
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read().encode('utf-8')
            elif file_path.endswith('.css'):
                ct = 'text/css; charset=utf-8'
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read().encode('utf-8')
            elif file_path.endswith('.js'):
                ct = 'application/javascript; charset=utf-8'
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read().encode('utf-8')
            else:
                ct = get_mime_type(full_path)
                with open(full_path, 'rb') as f:
                    content = f.read()

            resp = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Type: {ct}\r\n"
                f"Content-Length: {len(content)}\r\n"
                "Cache-Control: public, max-age=3600\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                "Connection: close\r\n\r\n"
            )
            client_socket.sendall(resp.encode('ascii') + content)
        except Exception as e:
            self.logger.error(f"提供文件错误: {e}")
            self._send_error(client_socket, 500, "Error")

    # ==================== 工具方法 ====================

    def _handle_cors(self, client_socket):
        resp = (
            "HTTP/1.1 204 No Content\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
            "Access-Control-Allow-Headers: Content-Type, X-Access-Code\r\n"
            "Access-Control-Max-Age: 86400\r\n"
            "Connection: close\r\n\r\n"
        )
        client_socket.sendall(resp.encode('ascii'))

    def _send_json(self, client_socket, code, data):
        if isinstance(data, str):
            body = data.encode('utf-8')
        else:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        resp = (
            f"HTTP/1.1 {code} OK\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Connection: close\r\n\r\n"
        )
        client_socket.sendall(resp.encode('ascii') + body)

    def _send_error(self, client_socket, code, message):
        body = f"""<!DOCTYPE html>
<html><head><title>{code}</title><meta charset="utf-8"></head>
<body style="text-align:center;padding:100px;font-family:sans-serif;">
<h1 style="color:#f56565;font-size:48px;">{code}</h1>
<p>{message}</p>
<a href="/" style="color:#667eea;">🏠 返回首页</a>
</body></html>"""
        resp = (
            f"HTTP/1.1 {code} {message}\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body.encode('utf-8'))}\r\n"
            "Connection: close\r\n\r\n"
        )
        client_socket.sendall(resp.encode('ascii') + body.encode('utf-8'))

    @staticmethod
    def _format_size(size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"