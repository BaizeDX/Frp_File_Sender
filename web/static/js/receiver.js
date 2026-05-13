// ==================== 接收端逻辑（完整版）====================

let connectedServer = null;
let availableFiles = [];
let downloadTasks = {};
let autoRefreshInterval = null;
let downloadDir = null;

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    // 恢复下载目录
    loadDownloadDir();
    
    // 尝试自动恢复连接
    autoReconnect();
    
    // 搜索过滤
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            displayFiles(availableFiles.filter(f => f.name.toLowerCase().includes(query)));
        });
    }
    
    // 加载最近连接
    loadRecentConnections();
    
    // 访问码输入框回车连接
    document.getElementById('access-code')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') connectToServer();
    });
    document.getElementById('server-url')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') connectToServer();
    });
});

// ==================== 下载目录管理 ====================

function loadDownloadDir() {
    const saved = localStorage.getItem('filep2p_download_dir');
    downloadDir = saved || '';
    updateDownloadDirDisplay();
}

function changeDownloadDir() {
    // 使用原生方式选择目录（需要浏览器支持）
    if ('showDirectoryPicker' in window) {
        // 现代浏览器
        window.showDirectoryPicker().then(dir => {
            downloadDir = dir.name;
            localStorage.setItem('filep2p_download_dir', downloadDir);
            updateDownloadDirDisplay();
            showToast('下载目录已设置为: ' + downloadDir, 'success');
        }).catch(() => {});
    } else {
        // 降级方案：手动输入
        const dir = prompt('请输入下载目录路径（留空使用浏览器默认下载位置）:\n\n例如: C:\\Downloads\\FileP2P', downloadDir);
        if (dir !== null) {
            downloadDir = dir.trim();
            localStorage.setItem('filep2p_download_dir', downloadDir);
            updateDownloadDirDisplay();
            showToast('下载目录已更新', 'success');
        }
    }
}

function updateDownloadDirDisplay() {
    const display = document.getElementById('download-dir-display');
    if (display) {
        display.textContent = downloadDir || '浏览器默认';
        display.title = downloadDir || '使用浏览器默认下载位置';
    }
}

// ==================== 自动重连 ====================

function autoReconnect() {
    const saved = getSavedConnection();
    
    if (saved && saved.url) {
        const connectSection = document.getElementById('connect-section');
        if (connectSection) {
            const existing = document.querySelector('.reconnect-banner');
            if (existing) existing.remove();
            
            const reconnectDiv = document.createElement('div');
            reconnectDiv.className = 'reconnect-banner';
            reconnectDiv.innerHTML = `
                <div style="background:#ebf8ff;border:1px solid #4299e1;border-radius:8px;padding:12px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                    <span>📡 上次连接: <strong>${saved.url}</strong></span>
                    <button class="btn btn-primary btn-sm" onclick="quickReconnect()" style="padding:6px 14px;font-size:13px;">重新连接</button>
                    <button class="btn btn-secondary btn-sm" onclick="clearSavedConnection()" style="padding:6px 14px;font-size:13px;">忘记</button>
                </div>
            `;
            connectSection.insertBefore(reconnectDiv, connectSection.firstChild);
            
            document.getElementById('server-url').value = saved.url.replace(/^https?:\/\//, '');
        }
    }
}

async function quickReconnect() {
    const saved = getSavedConnection();
    if (!saved) return;
    
    document.getElementById('server-url').value = saved.url.replace(/^https?:\/\//, '');
    if (saved.accessCode) {
        document.getElementById('access-code').value = saved.accessCode;
    }
    await connectToServer();
}

function getSavedConnection() {
    try {
        return JSON.parse(localStorage.getItem('filep2p_connection') || 'null');
    } catch { return null; }
}

function saveConnection(url, accessCode) {
    try {
        localStorage.setItem('filep2p_connection', JSON.stringify({
            url, accessCode: accessCode || '', timestamp: Date.now()
        }));
    } catch (e) {}
}

function clearSavedConnection() {
    localStorage.removeItem('filep2p_connection');
    document.querySelector('.reconnect-banner')?.remove();
    document.getElementById('server-url').value = '';
    document.getElementById('access-code').value = '';
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
    
    const btn = document.querySelector('.manual-connect .btn-primary');
    const originalText = btn?.textContent;
    if (btn) { btn.textContent = '连接中...'; btn.disabled = true; }
    
    try {
        const headers = {};
        if (accessCode) {
            headers['X-Access-Code'] = accessCode;
        }
        
        const response = await fetch(`${serverUrl}/api/files`, { headers });
        const data = await response.json();
        
        // 检查是否需要访问码
        if (response.status === 401 || data.need_access_code) {
            document.getElementById('access-code').focus();
            document.getElementById('access-code').style.border = '2px solid #f56565';
            showToast('🔒 需要输入访问码', 'error');
            setTimeout(() => {
                document.getElementById('access-code').style.border = '';
            }, 2000);
            return;
        }
        
        if (!response.ok) {
            throw new Error(`服务器返回: ${response.status}`);
        }
        
        connectedServer = serverUrl;
        availableFiles = data.files || [];
        
        saveConnection(serverUrl, accessCode);
        saveRecentConnection(serverUrl);
        
        showFileBrowser();
        startAutoRefresh();
        
        document.querySelector('.reconnect-banner')?.remove();
        showToast(`✅ 已连接 · ${availableFiles.length} 个文件`, 'success');
        
    } catch (error) {
        showToast(`❌ 连接失败: ${error.message}`, 'error');
    } finally {
        if (btn) { btn.textContent = originalText || '连接'; btn.disabled = false; }
    }
}

// ==================== 自动刷新 ====================

function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshInterval = setInterval(async () => {
        if (!connectedServer) return;
        try {
            const headers = {};
            const code = document.getElementById('access-code')?.value;
            if (code) headers['X-Access-Code'] = code;
            
            const response = await fetch(`${connectedServer}/api/files`, { headers });
            if (response.ok) {
                const data = await response.json();
                const newFiles = data.files || [];
                
                const oldNames = availableFiles.map(f => f.name).sort().join(',');
                const newNames = newFiles.map(f => f.name).sort().join(',');
                
                if (oldNames !== newNames) {
                    availableFiles = newFiles;
                    displayFiles(newFiles);
                    console.log('🔄 文件列表已自动更新');
                }
            } else if (response.status === 401) {
                // 需要重新验证
                stopAutoRefresh();
                showToast('⚠️ 连接已过期，请重新输入访问码', 'warning');
            }
        } catch (e) {}
    }, 10000);
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
            <div style="grid-column:1/-1;text-align:center;padding:40px;color:#718096;">
                <div style="font-size:48px;">📭</div>
                <p>暂无文件</p>
                <p style="font-size:13px;">等待发送方添加文件（每10秒自动刷新）</p>
                <button class="btn btn-secondary" onclick="manualRefresh()">🔄 手动刷新</button>
            </div>`;
        return;
    }
    
    grid.innerHTML = files.map(f => `
        <div class="file-card" onclick="toggleFileSelection(this,'${f.name}')" data-filename="${f.name}">
            <input type="checkbox" class="file-card-checkbox">
            <span class="file-card-icon">${getFileIcon(f.name)}</span>
            <div class="file-card-name">${f.name}</div>
            <div class="file-card-size">${formatSize(f.size)}</div>
            <div class="file-card-meta">
                <span>${f.type||'文件'}</span>
                <span>${f.modified||''}</span>
            </div>
        </div>`).join('');
}

function manualRefresh() {
    if (!connectedServer) return;
    const headers = {};
    const code = document.getElementById('access-code')?.value;
    if (code) headers['X-Access-Code'] = code;
    
    fetch(`${connectedServer}/api/files`, { headers })
        .then(r => r.json())
        .then(d => { availableFiles = d.files || []; displayFiles(availableFiles); })
        .catch(() => showToast('刷新失败', 'error'));
}

// ==================== 文件选择 ====================

function toggleFileSelection(card, name) {
    card.classList.toggle('selected');
    card.querySelector('.file-card-checkbox').checked = card.classList.contains('selected');
    updateSelectionSummary();
}

function selectAll() {
    document.querySelectorAll('.file-card').forEach(c => { c.classList.add('selected'); c.querySelector('.file-card-checkbox').checked = true; });
    updateSelectionSummary();
}

function deselectAll() {
    document.querySelectorAll('.file-card').forEach(c => { c.classList.remove('selected'); c.querySelector('.file-card-checkbox').checked = false; });
    updateSelectionSummary();
}

function updateSelectionSummary() {
    const selected = document.querySelectorAll('.file-card.selected');
    let totalSize = 0;
    selected.forEach(c => {
        const f = availableFiles.find(x => x.name === c.dataset.filename);
        if (f) totalSize += f.size;
    });
    const summary = document.getElementById('transfer-summary');
    if (selected.length > 0) {
        summary.style.display = 'flex';
        document.getElementById('selected-count').textContent = selected.length;
        document.getElementById('selected-size').textContent = formatSize(totalSize);
    } else {
        summary.style.display = 'none';
    }
}

function sortFiles() {
    const by = document.getElementById('sort-select').value;
    availableFiles.sort((a, b) => {
        if (by === 'name') return a.name.localeCompare(b.name);
        if (by === 'size') return b.size - a.size;
        return (b.modified||'').localeCompare(a.modified||'');
    });
    displayFiles(availableFiles);
}

// ==================== 智能检测 ====================

async function detectConnection() {
    const ip = document.getElementById('target-ip').value.trim();
    if (!ip) { showToast('请输入IP', 'error'); return; }
    
    const div = document.getElementById('detect-result');
    div.className = 'detect-result show';
    div.innerHTML = '<p>⏳ 检测中...</p>';
    
    try {
        const r = await fetch(`/api/check?target=${ip}`);
        const d = await r.json();
        div.className = `detect-result show ${d.mode}`;
        div.innerHTML = `<p><strong>${d.recommendation}</strong></p>
            <p style="font-size:13px;">${d.reason}</p>
            ${d.connection_url ? `<button class="btn btn-primary btn-sm" onclick="document.getElementById('server-url').value='${d.connection_url.replace('http://','')}';connectToServer();">使用此地址</button>` : ''}`;
    } catch {
        div.innerHTML = '<p style="color:#f56565;">检测失败</p>';
    }
}

// ==================== 下载 ====================

async function downloadSelected() {
    const selected = document.querySelectorAll('.file-card.selected');
    if (!selected.length) { showToast('请先选择文件', 'error'); return; }
    if (!connectedServer) { showToast('请先连接', 'error'); return; }
    
    document.getElementById('download-section').style.display = 'block';
    
    for (const card of selected) {
        await downloadFile(card.dataset.filename);
    }
}

async function downloadFile(filename) {
    const taskId = 'task-' + Date.now();
    const div = document.createElement('div');
    div.className = 'download-task';
    div.id = taskId;
    div.innerHTML = `<div class="task-header"><span>📥 ${filename}</span><span class="task-status transferring">下载中</span></div>
        <div class="progress-bar"><div class="progress-fill" style="width:0%"></div></div>
        <div class="task-info"><span class="task-downloaded">0 B</span><span class="task-speed">-</span></div>`;
    document.getElementById('download-tasks').appendChild(div);
    
    try {
        const resp = await fetch(`${connectedServer}/api/download/${encodeURIComponent(filename)}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        
        const total = parseInt(resp.headers.get('Content-Length') || '0');
        const reader = resp.body.getReader();
        let downloaded = 0;
        const chunks = [];
        let lastTime = Date.now(), lastBytes = 0;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            chunks.push(value);
            downloaded += value.length;
            
            const now = Date.now();
            if (now - lastTime > 200) {
                const speed = (downloaded - lastBytes) / ((now - lastTime) / 1000);
                updateTask(taskId, downloaded, total, speed, 'transferring');
                lastTime = now; lastBytes = downloaded;
            }
        }
        
        const blob = new Blob(chunks);
        
        // 如果指定了下载目录，尝试保存到指定位置
        if (downloadDir && 'showDirectoryPicker' in window) {
            // 这里简化处理，使用浏览器下载
        }
        
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
        
        updateTask(taskId, total, total, 0, 'completed');
    } catch (e) {
        updateTask(taskId, 0, 0, 0, 'error');
    }
}

function updateTask(id, downloaded, total, speed, status) {
    const el = document.getElementById(id);
    if (!el) return;
    el.querySelector('.progress-fill').style.width = (total > 0 ? downloaded / total * 100 : 0) + '%';
    el.querySelector('.task-downloaded').textContent = formatSize(downloaded);
    el.querySelector('.task-speed').textContent = status === 'transferring' ? formatSpeed(speed) : '';
    const s = el.querySelector('.task-status');
    s.textContent = status === 'completed' ? '✅ 完成' : status === 'error' ? '❌ 失败' : '下载中';
    s.className = 'task-status ' + status;
}

// ==================== 最近连接 ====================

function saveRecentConnection(url) {
    let r = JSON.parse(localStorage.getItem('filep2p_recent') || '[]');
    r = r.filter(x => x !== url);
    r.unshift(url);
    if (r.length > 5) r.pop();
    localStorage.setItem('filep2p_recent', JSON.stringify(r));
    loadRecentConnections();
}

function loadRecentConnections() {
    const r = JSON.parse(localStorage.getItem('filep2p_recent') || '[]');
    const c = document.getElementById('recent-connections');
    const l = document.getElementById('recent-list');
    if (r.length > 0 && c && l) {
        c.style.display = 'block';
        l.innerHTML = r.map(url => `<div style="cursor:pointer;padding:8px;border-bottom:1px solid #eee;" onclick="document.getElementById('server-url').value='${url.replace(/^https?:\/\//, '')}';connectToServer();">📋 ${url}</div>`).join('');
    }
}

window.addEventListener('beforeunload', stopAutoRefresh);