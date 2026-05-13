// ==================== 工具函数 ====================

/**
 * 格式化文件大小
 */
function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * 格式化速度
 */
function formatSpeed(bytesPerSec) {
    if (bytesPerSec === 0) return '0 B/s';
    return formatSize(bytesPerSec) + '/s';
}

/**
 * 根据文件扩展名获取图标
 */
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        // 图片
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 
        'bmp': '🖼️', 'svg': '🖼️', 'webp': '🖼️',
        // 视频
        'mp4': '🎬', 'avi': '🎬', 'mov': '🎬', 'mkv': '🎬',
        // 音频
        'mp3': '🎵', 'wav': '🎵', 'flac': '🎵', 'aac': '🎵',
        // 文档
        'pdf': '📕', 'doc': '📝', 'docx': '📝', 'txt': '📄',
        'xls': '📊', 'xlsx': '📊', 'ppt': '📽️', 'pptx': '📽️',
        // 压缩包
        'zip': '📦', 'rar': '📦', '7z': '📦', 'tar': '📦', 'gz': '📦',
        // 代码
        'py': '💻', 'js': '💻', 'html': '💻', 'css': '💻',
        'java': '💻', 'cpp': '💻', 'c': '💻',
        // 可执行文件
        'exe': '⚙️', 'msi': '⚙️', 'apk': '📱',
    };
    return icons[ext] || '📎';
}

/**
 * 复制URL到剪贴板
 */
function copyUrl(elementId) {
    const input = document.getElementById(elementId);
    input.select();
    document.execCommand('copy');
    
    // 显示提示
    const btn = input.nextElementSibling;
    const originalText = btn.textContent;
    btn.textContent = '✅ 已复制';
    btn.style.background = '#48bb78';
    btn.style.color = 'white';
    
    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = '';
        btn.style.color = '';
    }, 2000);
}

/**
 * 发送API请求
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API请求失败:', error);
        throw error;
    }
}

/**
 * 显示提示消息
 */
function showToast(message, type = 'info') {
    // 移除已有的toast
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? '#48bb78' : type === 'error' ? '#f56565' : '#4299e1'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1000;
        animation: fadeIn 0.3s ease;
        font-size: 14px;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}