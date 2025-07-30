// 프록시 모니터링 시스템 - 관리 페이지 (PPAT)

let proxies = [];
let groups = [];
let editingProxy = null;
let editingGroup = null;
let modal = null;
let groupModal = null;

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('PPAT 시스템 초기화 중...');
    
    // Bootstrap 모달 초기화
    modal = new bootstrap.Modal(document.getElementById('proxyModal'));
    groupModal = new bootstrap.Modal(document.getElementById('groupModal'));
    
    // 초기 데이터 로드
    loadGroups();
    loadProxies();
    
    // 주기적으로 상태 업데이트 (30초마다)
    setInterval(() => {
        loadProxies();
        loadGroups();
    }, 30000);
});

// 탭 표시 (향후 확장용)
function showTab(tabName) {
    console.log('Tab:', tabName);
    // PRD 기준으로 향후 자원사용률, 세션브라우저, 정책조회 탭 추가 예정
}

// ==================== 프록시 그룹 관리 ====================

// 프록시 그룹 목록 로드
async function loadGroups() {
    console.log('프록시 그룹 로딩 시작...');
    try {
        const response = await fetch('/api/groups');
        console.log('Groups response status:', response.status);
        
        if (response.ok) {
            groups = await response.json();
            console.log('로드된 그룹 수:', groups.length);
            updateGroupTable();
            updateGroupSelect();
        } else {
            const errorText = await response.text();
            console.error('그룹 API 오류:', response.status, errorText);
            showNotification(`그룹 목록을 불러오는데 실패했습니다. (${response.status})`, 'danger');
        }
    } catch (error) {
        console.error('그룹 목록 로딩 오류:', error);
        showNotification('그룹 네트워크 오류: ' + error.message, 'danger');
    }
}

// 그룹 테이블 업데이트
function updateGroupTable() {
    console.log('그룹 테이블 업데이트 중...');
    const tbody = document.getElementById('groupTableBody');
    
    if (groups.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">등록된 그룹이 없습니다</td></tr>';
        return;
    }
    
    tbody.innerHTML = groups.map(group => `
        <tr>
            <td class="ps-3">
                <strong>${group.name}</strong>
                ${group.name === '기본그룹' ? '<span class="badge bg-info ms-2 small">기본</span>' : ''}
            </td>
            <td><small class="text-muted">${group.description || '-'}</small></td>
            <td>
                <span class="badge bg-light text-dark">${group.proxy_count || 0}대</span>
            </td>
            <td>
                ${group.main_server ? `<span class="badge bg-warning text-dark">${group.main_server}</span>` : '<span class="text-muted small">미지정</span>'}
            </td>
            <td class="text-center">
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary btn-sm" 
                            onclick="editGroup(${group.id})"
                            title="수정">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${group.name !== '기본그룹' ? `
                        <button class="btn btn-outline-danger btn-sm" 
                                onclick="deleteGroup(${group.id})"
                                title="삭제">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
    console.log('그룹 테이블 업데이트 완료');
}

// 그룹 선택 드롭다운 업데이트
function updateGroupSelect() {
    const select = document.getElementById('proxyGroup');
    select.innerHTML = '<option value="">그룹을 선택하세요</option>';
    
    groups.forEach(group => {
        const option = document.createElement('option');
        option.value = group.id;
        option.textContent = group.name;
        select.appendChild(option);
    });
}

// 그룹 모달 표시
function showGroupModal() {
    console.log('그룹 모달 표시');
    editingGroup = null;
    document.getElementById('groupModalTitle').textContent = '프록시 그룹 추가';
    clearGroupForm();
    groupModal.show();
}

// 그룹 모달 닫기
function closeGroupModal() {
    console.log('그룹 모달 닫기');
    groupModal.hide();
    editingGroup = null;
    clearGroupForm();
}

// 그룹 폼 초기화
function clearGroupForm() {
    document.getElementById('groupName').value = '';
    document.getElementById('groupDescription').value = '';
}

// 그룹 저장
async function saveGroup() {
    console.log('그룹 저장 시작');
    const name = document.getElementById('groupName').value.trim();
    
    console.log('그룹 입력값:', { name });
    
    if (!name) {
        showNotification('그룹 이름은 필수 항목입니다.', 'warning');
        return;
    }
    
    const saveButton = document.getElementById('saveGroupButton');
    const originalText = saveButton.innerHTML;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>저장중...';
    saveButton.disabled = true;
    
    try {
        const data = {
            name: name,
            description: document.getElementById('groupDescription').value
        };
        
        const method = editingGroup ? 'PUT' : 'POST';
        const url = editingGroup ? `/api/groups/${editingGroup.id}` : '/api/groups';
        
        console.log('그룹 요청 데이터:', data);
        console.log('그룹 요청 URL:', url, 'Method:', method);
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        console.log('그룹 응답 상태:', response.status);
        
        if (response.ok) {
            const result = await response.json();
            console.log('그룹 저장 성공:', result);
            await loadGroups();
            closeGroupModal();
            showNotification(
                editingGroup ? '그룹이 수정되었습니다.' : '그룹이 추가되었습니다.', 
                'success'
            );
        } else {
            const errorText = await response.text();
            console.error('그룹 서버 오류:', response.status, errorText);
            
            let errorMessage = '알 수 없는 오류';
            try {
                const error = JSON.parse(errorText);
                errorMessage = error.message || error.error || errorText;
            } catch {
                errorMessage = errorText;
            }
            
            showNotification('그룹 저장 실패: ' + errorMessage, 'danger');
        }
    } catch (error) {
        console.error('그룹 저장 오류:', error);
        showNotification('그룹 저장 중 오류: ' + error.message, 'danger');
    } finally {
        saveButton.innerHTML = originalText;
        saveButton.disabled = false;
    }
}

// 그룹 수정
function editGroup(groupId) {
    editingGroup = groups.find(g => g.id === groupId);
    if (!editingGroup) return;
    
    document.getElementById('groupModalTitle').textContent = '프록시 그룹 수정';
    document.getElementById('groupName').value = editingGroup.name;
    document.getElementById('groupDescription').value = editingGroup.description || '';
    
    groupModal.show();
}

// 그룹 삭제
async function deleteGroup(groupId) {
    const group = groups.find(g => g.id === groupId);
    if (!group) return;
    
    if (group.name === '기본그룹') {
        showNotification('기본 그룹은 삭제할 수 없습니다.', 'warning');
        return;
    }
    
    if (!confirm(`정말로 "${group.name}" 그룹을 삭제하시겠습니까?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/groups/${groupId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            await loadGroups();
            await loadProxies(); // 프록시 목록도 갱신
            showNotification('그룹이 삭제되었습니다.', 'success');
        } else {
            const error = await response.json();
            showNotification('삭제 실패: ' + (error.message || error.error), 'danger');
        }
    } catch (error) {
        console.error('그룹 삭제 오류:', error);
        showNotification('그룹 삭제 중 오류가 발생했습니다.', 'danger');
    }
}

// ==================== 프록시 서버 관리 ====================

// 프록시 목록 로드
async function loadProxies() {
    console.log('프록시 목록 로딩 시작...');
    try {
        const response = await fetch('/api/proxies');
        console.log('Proxies response status:', response.status);
        
        if (response.ok) {
            proxies = await response.json();
            console.log('로드된 프록시 수:', proxies.length);
            updateProxyTable();
        } else {
            const errorText = await response.text();
            console.error('프록시 API 오류:', response.status, errorText);
            showNotification(`프록시 목록을 불러오는데 실패했습니다. (${response.status})`, 'danger');
        }
    } catch (error) {
        console.error('프록시 목록 로딩 오류:', error);
        showNotification('프록시 네트워크 오류: ' + error.message, 'danger');
    }
}

// 프록시 테이블 업데이트 (PRD 기준: Main/Cluster Appliance 구분)
function updateProxyTable() {
    console.log('프록시 테이블 업데이트 중...');
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
            <td class="ps-3">
                <strong>${proxy.name}</strong>
                <br><small class="text-muted">${proxy.description || ''}</small>
            </td>
            <td>
                <code class="text-primary">${proxy.host}</code>
                <br><small class="text-muted">SSH: ${proxy.ssh_port} | SNMP: ${proxy.snmp_port}</small>
            </td>
            <td>
                <span class="badge bg-light text-dark">${proxy.group_name || '미지정'}</span>
            </td>
            <td>
                ${proxy.is_main ? 
                    '<span class="badge bg-warning text-dark">메인</span>' : 
                    '<span class="badge bg-secondary">클러스터</span>'
                }
            </td>
            <td>
                <span class="badge ${proxy.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${proxy.is_active ? '온라인' : '오프라인'}
                </span>
            </td>
            <td class="text-center">
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-info btn-sm" 
                            onclick="testConnection(${proxy.id})" 
                            id="testBtn-${proxy.id}"
                            title="연결 테스트">
                        <i class="fas fa-plug"></i>
                    </button>
                    <button class="btn btn-outline-primary btn-sm" 
                            onclick="editProxy(${proxy.id})"
                            title="수정">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" 
                            onclick="deleteProxy(${proxy.id})"
                            title="삭제">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    console.log('프록시 테이블 업데이트 완료');
}

// 프록시 모달 표시
function showModal() {
    console.log('프록시 모달 표시');
    editingProxy = null;
    document.getElementById('modalTitle').textContent = '프록시 추가';
    clearForm();
    modal.show();
}

// 프록시 모달 닫기
function closeModal() {
    console.log('프록시 모달 닫기');
    modal.hide();
    editingProxy = null;
    clearForm();
}

// 프록시 폼 초기화
function clearForm() {
    document.getElementById('proxyName').value = '';
    document.getElementById('proxyHost').value = '';
    document.getElementById('proxySshPort').value = '22';
    document.getElementById('proxySnmpPort').value = '161';
    document.getElementById('proxyUsername').value = 'root';
    document.getElementById('proxyPassword').value = '';
    document.getElementById('proxyDescription').value = '';
    document.getElementById('proxyIsActive').checked = false; // PRD 반영: 최초 오프라인
    document.getElementById('proxyIsMain').checked = false;
    document.getElementById('proxyGroup').value = '';
}

// 프록시 저장
async function saveProxy() {
    console.log('프록시 저장 시작');
    const name = document.getElementById('proxyName').value.trim();
    const host = document.getElementById('proxyHost').value.trim();
    
    console.log('프록시 입력값:', { name, host });
    
    if (!name || !host) {
        showNotification('이름과 IP 주소는 필수 항목입니다.', 'warning');
        return;
    }
    
    const saveButton = document.getElementById('saveButton');
    const originalText = saveButton.innerHTML;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>저장중...';
    saveButton.disabled = true;
    
    try {
        const groupId = document.getElementById('proxyGroup').value;
        const data = {
            name: name,
            host: host,
            ssh_port: parseInt(document.getElementById('proxySshPort').value) || 22,
            snmp_port: parseInt(document.getElementById('proxySnmpPort').value) || 161,
            username: document.getElementById('proxyUsername').value || 'root',
            password: document.getElementById('proxyPassword').value || '123456',
            description: document.getElementById('proxyDescription').value,
            is_active: document.getElementById('proxyIsActive').checked,
            is_main: document.getElementById('proxyIsMain').checked,
            group_id: groupId ? parseInt(groupId) : null
        };
        
        const method = editingProxy ? 'PUT' : 'POST';
        const url = editingProxy ? `/api/proxies/${editingProxy.id}` : '/api/proxies';
        
        console.log('프록시 요청 데이터:', data);
        console.log('프록시 요청 URL:', url, 'Method:', method);
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        console.log('프록시 응답 상태:', response.status);
        
        if (response.ok) {
            const result = await response.json();
            console.log('프록시 저장 성공:', result);
            await loadProxies();
            await loadGroups(); // 그룹 카운트 업데이트
            closeModal();
            showNotification(
                editingProxy ? '프록시가 수정되었습니다.' : '프록시가 추가되었습니다.', 
                'success'
            );
        } else {
            const errorText = await response.text();
            console.error('프록시 서버 오류:', response.status, errorText);
            
            let errorMessage = '알 수 없는 오류';
            try {
                const error = JSON.parse(errorText);
                errorMessage = error.message || error.error || errorText;
            } catch {
                errorMessage = errorText;
            }
            
            showNotification('프록시 저장 실패: ' + errorMessage, 'danger');
        }
    } catch (error) {
        console.error('프록시 저장 오류:', error);
        showNotification('프록시 저장 중 오류: ' + error.message, 'danger');
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
    document.getElementById('proxySnmpPort').value = editingProxy.snmp_port || 161;
    document.getElementById('proxyUsername').value = editingProxy.username;
    document.getElementById('proxyPassword').value = ''; // 보안상 비워둠
    document.getElementById('proxyDescription').value = editingProxy.description || '';
    document.getElementById('proxyIsActive').checked = editingProxy.is_active;
    document.getElementById('proxyIsMain').checked = editingProxy.is_main || false;
    document.getElementById('proxyGroup').value = editingProxy.group_id || '';
    
    modal.show();
}

// 프록시 삭제
async function deleteProxy(proxyId) {
    const proxy = proxies.find(p => p.id === proxyId);
    if (!proxy) return;
    
    if (!confirm(`정말로 "${proxy.name}" 프록시를 삭제하시겠습니까?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/proxies/${proxyId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            await loadProxies();
            await loadGroups(); // 그룹 카운트 업데이트
            showNotification('프록시가 삭제되었습니다.', 'success');
        } else {
            showNotification('삭제에 실패했습니다.', 'danger');
        }
    } catch (error) {
        console.error('프록시 삭제 오류:', error);
        showNotification('프록시 삭제 중 오류가 발생했습니다.', 'danger');
    }
}

// 연결 테스트 (PRD 기준: SSH/SNMP 연결 확인)
async function testConnection(proxyId) {
    const testBtn = document.getElementById(`testBtn-${proxyId}`);
    const originalHTML = testBtn.innerHTML;
    
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    testBtn.disabled = true;
    
    try {
        const response = await fetch(`/api/proxies/${proxyId}/test`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('연결 테스트 성공!', 'success');
        } else {
            showNotification('연결 테스트 실패: ' + result.message, 'warning');
        }
        
        // 상태 업데이트를 위해 목록 다시 로드
        await loadProxies();
        
    } catch (error) {
        console.error('연결 테스트 오류:', error);
        showNotification('연결 테스트 중 오류가 발생했습니다.', 'danger');
    } finally {
        testBtn.innerHTML = originalHTML;
        testBtn.disabled = false;
    }
}

// ==================== 공통 유틸리티 ====================

// 알림 표시 (PRD 기준: 미니멀 디자인)
function showNotification(message, type = 'info') {
    const alertClass = type === 'success' ? 'alert-success' : 
                      type === 'danger' ? 'alert-danger' : 
                      type === 'warning' ? 'alert-warning' : 'alert-info';
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas ${getIconForType(type)} me-2"></i>
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

// 알림 타입별 아이콘
function getIconForType(type) {
    switch(type) {
        case 'success': return 'fa-check-circle';
        case 'danger': return 'fa-exclamation-circle';
        case 'warning': return 'fa-exclamation-triangle';
        default: return 'fa-info-circle';
    }
}