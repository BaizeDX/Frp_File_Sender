// ==================== 接收端逻辑（带自动重连）====================

let connectedServer = null;
let availableFiles = [];
let downloadTasks = {};
let autoRefreshInterval = null;

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    // 尝试自动恢复连接
    autoReconnect();
    
    // 搜索框实时过滤
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const filtered = availableFiles.filter(f => 
                f.name.toLowerCase().includes(query)
            );
            displayFiles(filtered);
        });
    }
    
    // 加载最近连接
    loadRecentConnections();
});

// ==================== 自动重连 ====================

function autoReconnect() {
    const saved = getSavedConnection();
    
    if (saved && saved.url) {
        console.log('🔍 发现已保存的连接:', saved.url);
        
        // 显示重连提示
        const connectSection = document.getElementById('connect-section');
        if (connectSection) {
            const reconnectDiv = document.createElement('div');
            reconnectDiv.className = 'reconnect-banner';
            reconnectDiv.innerHTML = `
                <div class="reconnect-info">
                    <span>📡 检测到上次连接: <strong>${saved.url}</strong></span>
                    <button class="btn btn-primary btn-sm" onclick="quickReconnect()">重新连接</button>
                    <button class="btn btn-secondary btn-sm" onclick="clearSavedConnection()">忘记</button>
                </div>
            `;
            connectSection.insertBefore(reconnectDiv, connectSection.firstChild);
            
            // 自动填充
            document.getElementById('server-url').value = saved.url.replace('http://', '').replace('https://', '');
        }
    }
}

async function quickReconnect() {
    const saved = getSavedConnection();
    if (!saved || !saved.url) return;
    
    document.getElementById('server-url').value = saved.url.replace('http://', '').replace('https://', '');
    if (saved.accessCode) {
        document.getElementById('access-code').value = saved.accessCode;
    }
    
    await connectToServer();
}

// ==================== 连接管理 ====================

function getSavedConnection() {
    try {
        const data = localStorage.getItem('filep2p_connection');
        return data ? JSON.parse(data) : null;
    } catch {
        return null;
    }
}

function saveConnection(url, accessCode) {
    try {
        localStorage.setItem('filep2p_connection', JSON.stringify({
            url: url,
            accessCode: accessCode || '',
            timestamp: Date.now(),
        }));
    } catch (e) {
        console.warn('无法保存连接信息:', e);
    }
}

function clearSavedConnection() {
    localStorage.removeItem('filep2p_connection');
    document.querySelector('.reconnect-banner')?.remove();
    document.getElementById('server-url').value = '';
}

// ==================== 连接服务器 ====================

async function connectToServer() {
    let serverUrl = document.getElementById('server-url').value.trim();
    const accessCode = document.getElementById('access-code').value.trim();
    
    if (!serverUrl) {
        showToast('请输入服务器地址', 'error');
        return;
    }
    
    if (!serverUrl.startsWith('http')) {
        serverUrl = 'http://' + serverUrl;
    }
    
    try {
        showToast('正在连接...', 'info');
        
        const headers = {};
        if (accessCode) {
            headers['X-Access-Code'] = accessCode;
        }
        
        const response = await fetch(`${serverUrl}/api/files`, { headers });
        
        if (!response.ok) {
            throw new Error(`服务器返回: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 连接成功
        connectedServer = serverUrl;
        availableFiles = data.files || [];
        
        // 保存连接
        saveConnection(serverUrl, accessCode);
        saveRecentConnection(serverUrl);
        
        // 显示文件浏览器
        showFileBrowser();
        
        // 启动自动刷新
        startAutoRefresh();
        
        // 隐藏重连横幅
        document.querySelector('.reconnect-banner')?.remove();
        
        showToast(`✅ 连接成功！${availableFiles.length} 个文件可用`, 'success');
        
    } catch (error) {
        console.error('连接错误:', error);
        showToast(`❌ 连接失败: ${error.message}`, 'error');
    }
}

function disconnect() {
    connectedServer = null;
    availableFiles = [];
    
    stopAutoRefresh();
    
    document.getElementById('connect-section').style.display = 'block';
    document.getElementById('browse-section').style.display = 'none';
    document.getElementById('download-section').style.display = 'none';
    
    showToast('已断开连接', 'info');
}

// ==================== 自动刷新 ====================

function startAutoRefresh() {
    stopAutoRefresh();  // 先清除旧的
    
    // 每10秒自动刷新文件列表
    autoRefreshInterval = setInterval(async () => {
        if (!connectedServer) return;
        
        try {
            const response = await fetch(`${connectedServer}/api/files`);
            if (!response.ok) return;
            
            const data = await response.json();
            const newFiles = data.files || [];
            
            // 检查是否有变化
            const oldNames = availableFiles.map(f => f.name).sort().join(',');
            const newNames = newFiles.map(f => f.name).sort().join(',');
            
            if (oldNames !== newNames) {
                availableFiles = newFiles;
                displayFiles(newFiles);
                console.log('🔄 文件列表已更新');
            }
        } catch (e) {
            // 静默处理
        }
    }, 10000);  // 10秒
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// ==================== 文件显示 ====================

function showFileBrowser() {
    document.getElementById('connect-section').style.display = 'none';
    document.getElementById('browse-section').style.display = 'block';
    
    displayFiles(availableFiles);
}

function displayFiles(files) {
    const grid = document.getElementById('file-grid');
    
    if (!files || files.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #718096;">
                <div style="font-size: 48px; margin-bottom: 15px;">📭</div>
                <p>没有可用文件</p>
                <p style="font-size: 13px;">等待发送方添加文件...（每10秒自动刷新）</p>
                <button class="btn btn-secondary" onclick="manualRefresh()" style="margin-top: 10px;">
                    🔄 手动刷新
                </button>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = files.map(file => `
        <div class="file-card" onclick="toggleFileSelection(this, '${file.name}')" data-filename="${file.name}">
            <input type="checkbox" class="file-card-checkbox">
            <span class="file-card-icon">${getFileIcon(file.name)}</span>
            <div class="file-card-name">${file.name}</div>
            <div class="file-card-size">${formatSize(file.size)}</div>
            <div class="file-card-meta">
                <span>${file.type || '文件'}</span>
                <span>${file.modified || ''}</span>
            </div>
        </div>
    `).join('');
}

function manualRefresh() {
    if (!connectedServer) return;
    
    fetch(`${connectedServer}/api/files`)
        .then(res => res.json())
        .then(data => {
            availableFiles = data.files || [];
            displayFiles(availableFiles);
            showToast('✅ 已刷新', 'success');
        })
        .catch(err => {
            showToast('❌ 刷新失败', 'error');
        });
}

// ==================== 文件选择 ====================

function toggleFileSelection(cardElement, filename) {
    cardElement.classList.toggle('selected');
    const checkbox = cardElement.querySelector('.file-card-checkbox');
    checkbox.checked = cardElement.classList.contains('selected');
    updateSelectionSummary();
}

function selectAll() {
    document.querySelectorAll('.file-card').forEach(card => {
        card.classList.add('selected');
        card.querySelector('.file-card-checkbox').checked = true;
    });
    updateSelectionSummary();
}

function deselectAll() {
    document.querySelectorAll('.file-card').forEach(card => {
        card.classList.remove('selected');
        card.querySelector('.file-card-checkbox').checked = false;
    });
    updateSelectionSummary();
}

function updateSelectionSummary() {
    const selectedCards = document.querySelectorAll('.file-card.selected');
    const count = selectedCards.length;
    let totalSize = 0;
    
    selectedCards.forEach(card => {
        const filename = card.dataset.filename;
        const file = availableFiles.find(f => f.name === filename);
        if (file) totalSize += file.size;
    });
    
    const summary = document.getElementById('transfer-summary');
    if (count > 0) {
        summary.style.display = 'flex';
        document.getElementById('selected-count').textContent = count;
        document.getElementById('selected-size').textContent = formatSize(totalSize);
    } else {
        summary.style.display = 'none';
    }
}

function sortFiles() {
    const sortBy = document.getElementById('sort-select').value;
    
    availableFiles.sort((a, b) => {
        if (sortBy === 'name') return a.name.localeCompare(b.name);
        if (sortBy === 'size') return b.size - a.size;
        if (sortBy === 'modified') return (b.modified || '').localeCompare(a.modified || '');
        return 0;
    });
    
    displayFiles(availableFiles);
}

// ==================== 智能检测 ====================

async function detectConnection() {
    const ip = document.getElementById('target-ip').value.trim();
    if (!ip) {
        showToast('请输入目标IP地址', 'error');
        return;
    }
    
    const resultDiv = document.getElementById('detect-result');
    resultDiv.className = 'detect-result show';
    resultDiv.innerHTML = '<p>⏳ 正在检测...</p>';
    
    try {
        const response = await fetch(`/api/check?target=${encodeURIComponent(ip)}`);
        const data = await response.json();
        
        resultDiv.className = `detect-result show ${data.mode}`;
        resultDiv.innerHTML = `
            <p><strong>${data.recommendation}</strong></p>
            <p style="font-size:13px;color:#666;">${data.reason}</p>
            ${data.connection_url ? `
                <button class="btn btn-primary btn-sm" onclick="useDetectedUrl('${data.connection_url}')">
                    使用此地址
                </button>
            ` : ''}
        `;
    } catch (error) {
        resultDiv.innerHTML = '<p style="color:#f56565;">检测失败</p>';
    }
}

function useDetectedUrl(url) {
    document.getElementById('server-url').value = url.replace('http://', '');
    connectToServer();
}

// ==================== 文件下载 ====================

async function downloadSelected() {
    const selectedCards = document.querySelectorAll('.file-card.selected');
    
    if (selectedCards.length === 0) {
        showToast('请先选择要下载的文件', 'error');
        return;
    }
    
    if (!connectedServer) {
        showToast('请先连接到服务器', 'error');
        return;
    }
    
    document.getElementById('download-section').style.display = 'block';
    
    for (const card of selectedCards) {
        const filename = card.dataset.filename;
        await downloadFile(filename);
    }
}

async function downloadFile(filename) {
    const taskId = `task-${Date.now()}`;
    
    const taskElement = document.createElement('div');
    taskElement.className = 'download-task';
    taskElement.id = taskId;
    taskElement.innerHTML = `
        <div class="task-header">
            <span class="task-name">📥 ${filename}</span>
            <span class="task-status transferring">下载中</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:0%"></div></div>
        <div class="task-info">
            <span class="task-downloaded">0 B</span>
            <span class="task-speed">-</span>
        </div>
    `;
    document.getElementById('download-tasks').appendChild(taskElement);
    
    try {
        const url = `${connectedServer}/api/download/${encodeURIComponent(filename)}`;
        const response = await fetch(url);
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const total = parseInt(response.headers.get('Content-Length') || '0');
        const reader = response.body.getReader();
        
        let downloaded = 0;
        const chunks = [];
        let lastTime = Date.now();
        let lastBytes = 0;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            chunks.push(value);
            downloaded += value.length;
            
            const now = Date.now();
            if (now - lastTime > 200) {
                const speed = (downloaded - lastBytes) / ((now - lastTime) / 1000);
                updateTaskUI(taskId, downloaded, total, speed, 'transferring');
                lastTime = now;
                lastBytes = downloaded;
            }
        }
        
        // 完成
        const blob = new Blob(chunks);
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
        URL.revokeObjectURL(link.href);
        
        updateTaskUI(taskId, total, total, 0, 'completed');
        
    } catch (error) {
        updateTaskUI(taskId, 0, 0, 0, 'error');
        console.error('下载错误:', error);
    }
}

function updateTaskUI(taskId, downloaded, total, speed, status) {
    const el = document.getElementById(taskId);
    if (!el) return;
    
    const percent = total > 0 ? (downloaded / total * 100) : 0;
    
    el.querySelector('.progress-fill').style.width = percent + '%';
    el.querySelector('.task-downloaded').textContent = formatSize(downloaded);
    el.querySelector('.task-speed').textContent = status === 'transferring' ? formatSpeed(speed) : '';
    
    const statusEl = el.querySelector('.task-status');
    statusEl.textContent = status === 'completed' ? '✅ 完成' : status === 'error' ? '❌ 失败' : '下载中';
    statusEl.className = 'task-status ' + status;
}

// ==================== 最近连接 ====================

function saveRecentConnection(url) {
    let recent = JSON.parse(localStorage.getItem('filep2p_recent') || '[]');
    recent = recent.filter(r => r !== url);
    recent.unshift(url);
    if (recent.length > 5) recent.pop();
    localStorage.setItem('filep2p_recent', JSON.stringify(recent));
    loadRecentConnections();
}

function loadRecentConnections() {
    const recent = JSON.parse(localStorage.getItem('filep2p_recent') || '[]');
    const container = document.getElementById('recent-connections');
    const list = document.getElementById('recent-list');
    
    if (recent.length > 0) {
        container.style.display = 'block';
        list.innerHTML = recent.map(url => `
            <div style="cursor:pointer;padding:8px 12px;border-bottom:1px solid #eee;"
                 onclick="document.getElementById('server-url').value='${url.replace('http://', '')}';connectToServer();">
                📋 ${url}
            </div>
        `).join('');
    }
}

// ==================== 页面卸载时停止刷新 ====================

window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});