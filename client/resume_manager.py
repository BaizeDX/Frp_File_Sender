"""
断点续传管理器
"""

import os
import json
import time
import threading
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.logger import setup_logger


class ResumeManager:
    """管理下载任务的断点续传状态"""
    
    def __init__(self, state_dir='./downloads/.states'):
        self.state_dir = state_dir
        self.logger = setup_logger('ResumeManager', 'logs/resume.log')
        self.lock = threading.Lock()
        
        os.makedirs(self.state_dir, exist_ok=True)
    
    def save_state(self, task_id, state):
        """
        保存下载状态
        
        Args:
            task_id: 任务ID（通常是文件URL的哈希）
            state: 状态字典 {
                'url': str,
                'file_path': str,
                'downloaded': int,
                'total_size': int,
                'chunks': list,  # 已下载的块索引
                'timestamp': float
            }
        """
        state_file = self._get_state_file(task_id)
        
        with self.lock:
            try:
                state['timestamp'] = time.time()
                
                # 先写入临时文件
                temp_file = state_file + '.tmp'
                with open(temp_file, 'w') as f:
                    json.dump(state, f, indent=2)
                
                # 原子重命名
                os.replace(temp_file, state_file)
                
            except Exception as e:
                self.logger.error(f"保存状态失败: {e}")
    
    def load_state(self, task_id):
        """
        加载下载状态
        
        Returns:
            dict or None: 状态字典
        """
        state_file = self._get_state_file(task_id)
        
        if not os.path.exists(state_file):
            return None
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            # 检查状态是否过期（24小时）
            if time.time() - state.get('timestamp', 0) > 86400:
                self.logger.info(f"状态已过期: {task_id}")
                self.remove_state(task_id)
                return None
            
            return state
            
        except Exception as e:
            self.logger.error(f"加载状态失败: {e}")
            return None
    
    def remove_state(self, task_id):
        """删除状态文件"""
        state_file = self._get_state_file(task_id)
        
        try:
            if os.path.exists(state_file):
                os.remove(state_file)
            # 同时删除临时文件
            temp_file = state_file + '.tmp'
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            self.logger.error(f"删除状态失败: {e}")
    
    def get_downloaded_chunks(self, task_id):
        """
        获取已下载的块列表
        
        Returns:
            set: 已下载的块索引集合
        """
        state = self.load_state(task_id)
        if state and 'chunks' in state:
            return set(state['chunks'])
        return set()
    
    def mark_chunk_downloaded(self, task_id, chunk_index):
        """标记块已下载"""
        state = self.load_state(task_id)
        if state is None:
            return
        
        if 'chunks' not in state:
            state['chunks'] = []
        
        if chunk_index not in state['chunks']:
            state['chunks'].append(chunk_index)
            state['downloaded'] = len(state['chunks'])
            self.save_state(task_id, state)
    
    def cleanup_expired_states(self, max_age=86400):
        """清理过期的状态文件"""
        try:
            current_time = time.time()
            cleaned = 0
            
            for filename in os.listdir(self.state_dir):
                if filename.endswith('.tmp'):
                    os.remove(os.path.join(self.state_dir, filename))
                    continue
                
                filepath = os.path.join(self.state_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        state = json.load(f)
                    
                    if current_time - state.get('timestamp', 0) > max_age:
                        os.remove(filepath)
                        cleaned += 1
                except:
                    # 损坏的文件直接删除
                    os.remove(filepath)
                    cleaned += 1
            
            if cleaned > 0:
                self.logger.info(f"清理了 {cleaned} 个过期状态")
                
        except Exception as e:
            self.logger.error(f"清理状态文件错误: {e}")
    
    def _get_state_file(self, task_id):
        """获取状态文件路径"""
        # 使用哈希确保文件名安全
        import hashlib
        safe_id = hashlib.md5(task_id.encode()).hexdigest()
        return os.path.join(self.state_dir, f"{safe_id}.json")
    
    def create_task_id(self, url, file_path):
        """创建任务ID"""
        import hashlib
        content = f"{url}|{file_path}"
        return hashlib.md5(content.encode()).hexdigest()