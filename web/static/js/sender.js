// ==================== 发送端逻辑（简化版）====================

document.addEventListener('DOMContentLoaded', () => {
    // 页面加载时自动获取文件夹路径
    const shareDir = document.getElementById('share-dir');
    if (shareDir) {
        shareDir.textContent = window.location.origin + '/files/';
    }
});

async function generateShareLink() {
    const btn = document.getElementById('share-btn');
    if (btn) {
        btn.textContent = '⏳ 生成中...';
        btn.disabled = true;
    }

    try {
        const response = await fetch('/api/share');
        const data = await response.json();

        if (data.success) {
            document.getElementById('info-section').style.display = 'none';
            document.getElementById('share-section').style.display = 'block';
            
            document.getElementById('local-url').value = data.local_url;
            document.getElementById('access-code-display').textContent = data.access_code || '无';
            
            const summary = document.getElementById('file-summary');
            if (data.files && data.files.length > 0) {
                summary.innerHTML = `
                    <p>共 <strong>${data.file_count}</strong> 个文件</p>
                    <p>总大小: <strong>${formatSize(data.total_size)}</strong></p>
                    <ul class="file-mini-list">
                        ${data.files.map(f => `
                            <li>📎 ${f.name} (${formatSize(f.size)})</li>
                        `).join('')}
                    </ul>
                `;
            } else {
                summary.innerHTML = '<p style="color: #f56565;">⚠️ 文件夹为空</p>';
            }
            
            showToast('✅ ' + data.message, 'success');
        } else {
            showToast('❌ ' + (data.error || '生成失败'), 'error');
        }
    } catch (error) {
        showToast('❌ 请求失败: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.textContent = '🚀 生成分享链接';
            btn.disabled = false;
        }
    }
}

async function refreshShare() {
    await generateShareLink();
}