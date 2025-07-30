// 프록시 모니터링 시스템 - 순수 JavaScript

let proxies = [];
let editingProxy = null;
let modal = null;

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap 모달 초기화
    modal = new bootstrap.Modal(document.getElementById('proxyModal'));
    
    // 초기 데이터 로드
    loadProxies();
    
    // 주기적으로 상태 업데이트 (30초마다)
    setInterval(loadProxies, 30000);
});

// 프록시 목록 로드
async function loadProxies() {
    try {
        const response = await fetch('/api/proxies');
        if (response.ok) {
            proxies = await response.json();
            updateUI();
        } else {
            console.error('프록시 목록을 불러오는데 실패했습니다.');
        }
    } catch (error) {
        console.error('프록시 목록 로딩 오류:', error);
    }
}

// UI 업데이트
function updateUI() {
    updateStatistics();
    updateProxyTable();
}

// 통계 업데이트
function updateStatistics() {
    const total = proxies.length;
    const online = proxies.filter(p => p.is_active).length;
    const offline = total - online;
    
    document.getElementById('totalProxies').textContent = total;
    document.getElementById('onlineProxies').textContent = online;
    document.getElementById('offlineProxies').textContent = offline;
}

// 프록시 테이블 업데이트
function updateProxyTable() {
    const tbody = document.getElementById('proxyTableBody');
    const emptyMessage = document.getElementById('emptyMessage');
    
    if (proxies.length === 0) {
        tbody.innerHTML = '';
        emptyMessage.style.display = 'block';
        return;
    }
    
    emptyMessage.style.display = 'none';
    
    tbody.innerHTML = proxies.map(proxy => `
        <tr>
            <td>${proxy.name}</td>
            <td>${proxy.host}</td>
            <td>${proxy.ssh_port}</td>
            <td>
                <span class="badge ${proxy.is_active ? 'bg-success' : 'bg-danger'}">
                    ${proxy.is_active ? '온라인' : '오프라인'}
                </span>
            </td>
            <td>${formatDate(proxy.updated_at)}</td>
            <td>
                <button class="btn btn-sm btn-outline-info me-1" 
                        onclick="testConnection(${proxy.id})" 
                        id="testBtn-${proxy.id}">
                    <i class="fas fa-plug"></i>
                    연결테스트
                </button>
                <button class="btn btn-sm btn-outline-primary me-1" 
                        onclick="editProxy(${proxy.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" 
                        onclick="deleteProxy(${proxy.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// 모달 표시
function showModal() {
    editingProxy = null;
    document.getElementById('modalTitle').textContent = '프록시 추가';
    clearForm();
    modal.show();
}

// 모달 닫기
function closeModal() {
    modal.hide();
    editingProxy = null;
    clearForm();
}

// 폼 초기화
function clearForm() {
    document.getElementById('proxyName').value = '';
    document.getElementById('proxyHost').value = '';
    document.getElementById('proxySshPort').value = '22';
    document.getElementById('proxyUsername').value = 'root';
    document.getElementById('proxyPassword').value = '';
    document.getElementById('proxyDescription').value = '';
    document.getElementById('proxyIsActive').checked = true;
}

// 프록시 저장
async function saveProxy() {
    const name = document.getElementById('proxyName').value.trim();
    const host = document.getElementById('proxyHost').value.trim();
    
    if (!name || !host) {
        showNotification('이름과 IP 주소는 필수 항목입니다.', 'danger');
        return;
    }
    
    const saveButton = document.getElementById('saveButton');
    const originalText = saveButton.innerHTML;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>저장중...';
    saveButton.disabled = true;
    
    try {
        const data = {
            name: name,
            host: host,
            ssh_port: parseInt(document.getElementById('proxySshPort').value) || 22,
            username: document.getElementById('proxyUsername').value || 'root',
            password: document.getElementById('proxyPassword').value || '123456',
            description: document.getElementById('proxyDescription').value,
            is_active: document.getElementById('proxyIsActive').checked
        };
        
        const method = editingProxy ? 'PUT' : 'POST';
        const url = editingProxy ? `/api/proxies/${editingProxy.id}` : '/api/proxies';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            await loadProxies();
            closeModal();
            showNotification(editingProxy ? '프록시가 수정되었습니다.' : '프록시가 추가되었습니다.', 'success');
        } else {
            const error = await response.json();
            showNotification('저장 실패: ' + (error.message || error.error || '알 수 없는 오류'), 'danger');
        }
    } catch (error) {
        console.error('저장 오류:', error);
        showNotification('저장 중 오류가 발생했습니다.', 'danger');
    } finally {
        saveButton.innerHTML = originalText;
        saveButton.disabled = false;
    }
}

// 프록시 수정
function editProxy(proxyId) {
    editingProxy = proxies.find(p => p.id === proxyId);
    if (!editingProxy) return;
    
    document.getElementById('modalTitle').textContent = '프록시 수정';
    document.getElementById('proxyName').value = editingProxy.name;
    document.getElementById('proxyHost').value = editingProxy.host;
    document.getElementById('proxySshPort').value = editingProxy.ssh_port;
    document.getElementById('proxyUsername').value = editingProxy.username;
    document.getElementById('proxyPassword').value = ''; // 보안상 비워둠
    document.getElementById('proxyDescription').value = editingProxy.description || '';
    document.getElementById('proxyIsActive').checked = editingProxy.is_active;
    
    modal.show();
}

// 프록시 삭제
async function deleteProxy(proxyId) {
    if (!confirm('정말로 이 프록시를 삭제하시겠습니까?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/proxies/${proxyId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            await loadProxies();
            showNotification('프록시가 삭제되었습니다.', 'success');
        } else {
            showNotification('삭제에 실패했습니다.', 'danger');
        }
    } catch (error) {
        console.error('삭제 오류:', error);
        showNotification('삭제 중 오류가 발생했습니다.', 'danger');
    }
}

// 연결 테스트
async function testConnection(proxyId) {
    const testBtn = document.getElementById(`testBtn-${proxyId}`);
    const originalHTML = testBtn.innerHTML;
    
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 테스트중...';
    testBtn.disabled = true;
    
    try {
        const response = await fetch(`/api/proxies/${proxyId}/test`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('연결 테스트 성공!', 'success');
            // 상태 업데이트를 위해 목록 다시 로드
            await loadProxies();
        } else {
            showNotification('연결 테스트 실패: ' + result.message, 'danger');
            // 상태 업데이트를 위해 목록 다시 로드
            await loadProxies();
        }
    } catch (error) {
        console.error('연결 테스트 오류:', error);
        showNotification('연결 테스트 중 오류가 발생했습니다.', 'danger');
    } finally {
        testBtn.innerHTML = originalHTML;
        testBtn.disabled = false;
    }
}

// 날짜 포맷팅
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR');
}

// 알림 표시
function showNotification(message, type = 'info') {
    const alertClass = type === 'success' ? 'alert-success' : 
                      type === 'danger' ? 'alert-danger' : 'alert-info';
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    const notifications = document.getElementById('notifications');
    notifications.appendChild(alertDiv);
    
    // 5초 후 자동 제거
    setTimeout(() => {
        if (alertDiv.parentElement) {
            alertDiv.remove();
        }
    }, 5000);
}