"""
WebSocket进度推送处理器
"""

import json
import asyncio
import websockets
import threading
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger


class WebSocketProgressHandler:
    """WebSocket进度推送"""
    
    def __init__(self, host='0.0.0.0', port=8850):
        self.host = host
        self.port = port
        self.logger = setup_logger('WebSocket', 'logs/websocket.log')
        
        self.clients = set()
        self.server = None
        self.running = False
        
        # 传输状态
        self.transfer_stats = {
            'active_transfers': {},
            'total_bytes_sent': 0,
            'total_bytes_received': 0,
        }
    
    async def start(self):
        """启动WebSocket服务器"""
        self.running = True
        
        async def handler(websocket, path):
            """处理WebSocket连接"""
            self.clients.add(websocket)
            client_ip = websocket.remote_address[0]
            self.logger.info(f"WebSocket客户端连接: {client_ip}")
            
            try:
                async for message in websocket:
                    # 处理客户端消息
                    try:
                        data = json.loads(message)
                        await self._handle_message(websocket, data)
                    except json.JSONDecodeError:
                        pass
                        
            except websockets.exceptions.ConnectionClosed:
                self.logger.info(f"WebSocket客户端断开: {client_ip}")
            finally:
                self.clients.remove(websocket)
        
        try:
            self.server = await websockets.serve(
                handler,
                self.host,
                self.port
            )
            self.logger.info(f"WebSocket服务器启动在 {self.host}:{self.port}")
            
            await self.server.wait_closed()
            
        except Exception as e:
            self.logger.error(f"WebSocket服务器错误: {e}")
    
    async def stop(self):
        """停止WebSocket服务器"""
        self.running = False
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # 关闭所有客户端连接
        for client in self.clients.copy():
            try:
                await client.close()
            except:
                pass
        
        self.clients.clear()
        self.logger.info("WebSocket服务器已停止")
    
    async def broadcast(self, message):
        """广播消息给所有连接的客户端"""
        if not self.clients:
            return
        
        if isinstance(message, dict):
            message = json.dumps(message, ensure_ascii=False)
        
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        # 移除断开的客户端
        self.clients -= disconnected
    
    async def update_transfer_progress(self, transfer_id, filename, 
                                       downloaded, total, speed, status='transferring'):
        """
        更新传输进度并广播
        
        Args:
            transfer_id: 传输任务ID
            filename: 文件名
            downloaded: 已传输字节
            total: 总字节
            speed: 传输速度 (bytes/s)
            status: 状态 (transferring, paused, completed, error)
        """
        progress = (downloaded / total * 100) if total > 0 else 0
        
        message = {
            'type': 'transfer_progress',
            'data': {
                'transfer_id': transfer_id,
                'filename': filename,
                'downloaded': downloaded,
                'total': total,
                'progress': round(progress, 2),
                'speed': speed,
                'status': status,
            }
        }
        
        # 更新本地状态
        self.transfer_stats['active_transfers'][transfer_id] = message['data']
        
        # 广播
        await self.broadcast(message)
    
    def start_in_thread(self):
        """在独立线程中启动WebSocket服务器"""
        def run():
            asyncio.run(self.start())
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
    
    async def _handle_message(self, websocket, data):
        """处理客户端消息"""
        msg_type = data.get('type', '')
        
        if msg_type == 'ping':
            await websocket.send(json.dumps({'type': 'pong'}))
        
        elif msg_type == 'subscribe':
            transfer_id = data.get('transfer_id')
            if transfer_id:
                self.logger.info(f"客户端订阅传输: {transfer_id}")