// 프록시 모니터링 시스템 - 관리 페이지 (PPAT)

let proxies = [];
let groups = []; // New: Array to store proxy groups
let resources = []; // New: Array to store resource data
let editingProxy = null;
let editingGroup = null; // New: Variable for editing group
let modal = null;
let groupModal = null; // New: Bootstrap modal instance for groups
let currentTab = 'management'; // 현재 활성 탭

// 모니터링 관련 변수
let monitoringInterval = null;
let monitoringIntervalTime = 30; // 기본 30초
let isMonitoringActive = false;
let nextUpdateTimeout = null;

// 세션 브라우저 데이터
let sessions = [];
let resourcesGroupId = null;
let sessionsGroupId = null;
let sessionHeaders = [];
let sessionFilters = { protocol: '', status: '', client_ip: '', server_ip: '', user: '', url: '', q: '' };
let sessionPage = 1;
let sessionPageSize = 100;
let sessionTotal = 0;

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('PPAT 시스템 초기화 중...');
    
    // Bootstrap 모달 초기화
    modal = new bootstrap.Modal(document.getElementById('proxyModal'));
    groupModal = new bootstrap.Modal(document.getElementById('groupModal')); // New: Initialize group modal
    
    // 초기 데이터 로드
    loadGroups(); // New: Load groups on startup
    loadProxies();
    
    // 관리 탭은 주기적 업데이트 (30초마다)
    setInterval(() => {
        if (currentTab === 'management') {
            loadProxies();
            loadGroups();
        }
    }, 30000);

    // 관리 탭의 모니터링 설정 초기 로드
    loadMonitoringConfig();
    // 그룹 셀렉트 초기화
    initGroupSelectors();
});

async function initGroupSelectors() {
    try {
        const res = await fetch('/api/groups');
        if (!res.ok) return;
        const data = await res.json();
        // 자원 탭 그룹
        const resSel = document.getElementById('resourcesGroupSelect');
        if (resSel) {
            resSel.innerHTML = '<option value="">전체 그룹</option>' + data.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
            resSel.onchange = () => { resourcesGroupId = resSel.value ? parseInt(resSel.value) : null; if (isMonitoringActive) { loadResourcesData(); } };
        }
        // 세션 탭 그룹
        const sesSel = document.getElementById('sessionGroupSelect');
        if (sesSel) {
            sesSel.innerHTML = '<option value="">그룹 선택</option>' + data.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
            sesSel.onchange = () => { sessionsGroupId = sesSel.value ? parseInt(sesSel.value) : null; };
        }
    } catch(e) {
        console.error('그룹 셀렉트 초기화 실패', e);
    }
}

// 탭 전환 함수
function showTab(tabName) {
    console.log(`탭 전환: ${tabName}`);
    
    // 모든 탭 숨기기
    document.getElementById('managementTab').style.display = 'none';
    document.getElementById('resourcesTab').style.display = 'none';
    const sessionsTab = document.getElementById('sessionsTab');
    if (sessionsTab) sessionsTab.style.display = 'none';
    
    // 네비게이션 활성 클래스 제거
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // 선택된 탭 표시
    if (tabName === 'management') {
        document.getElementById('managementTab').style.display = 'block';
        document.querySelector('a[onclick="showTab(\'management\')"]').classList.add('active');
        loadGroups();
        loadProxies();
        loadMonitoringConfig();
        initGroupSelectors();
    } else if (tabName === 'resources') {
        document.getElementById('resourcesTab').style.display = 'block';
        document.querySelector('a[onclick="showTab(\'resources\')"]').classList.add('active');
        // 자동 호출 제거: 수동 시작만 가능
        // loadResourcesData();
        // loadMonitoringSummary();
        initGroupSelectors();
    } else if (tabName === 'sessions') {
        if (sessionsTab) sessionsTab.style.display = 'block';
        document.querySelector('a[onclick="showTab(\'sessions\')"]').classList.add('active');
        populateSessionProxySelect();
        initGroupSelectors();
        // 자동 조회 없음: 사용자가 명시적으로 조회/저장 버튼을 눌러야 함
    }
    
    currentTab = tabName;
}

// ==================== 관리 탭: 모니터링 설정 CRUD ====================
async function loadMonitoringConfig() {
    try {
        const res = await fetch('/api/monitoring/config');
        if (!res.ok) return;
        const cfg = await res.json();
        document.getElementById('configSessionCmd').value = cfg.session_cmd || '';
        document.getElementById('configSnmpOids').value = JSON.stringify(cfg.snmp_oids || {}, null, 2);
        document.getElementById('configCpuThreshold').value = cfg.cpu_threshold ?? 80;
        document.getElementById('configMemoryThreshold').value = cfg.memory_threshold ?? 80;
        document.getElementById('configDefaultInterval').value = cfg.default_interval ?? 30;
    } catch (e) {
        console.error('모니터링 설정 로드 실패:', e);
    }
}

async function saveMonitoringConfig() {
    try {
        const snmpText = document.getElementById('configSnmpOids').value || '{}';
        let snmpObj = {};
        try { snmpObj = JSON.parse(snmpText); } catch (e) { return showNotification('SNMP OIDs JSON 형식이 올바르지 않습니다.', 'warning'); }
        const body = {
            session_cmd: document.getElementById('configSessionCmd').value,
            snmp_oids: snmpObj,
            cpu_threshold: parseInt(document.getElementById('configCpuThreshold').value) || 80,
            memory_threshold: parseInt(document.getElementById('configMemoryThreshold').value) || 80,
            default_interval: parseInt(document.getElementById('configDefaultInterval').value) || 30,
        };
        const res = await fetch('/api/monitoring/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            showNotification('모니터링 설정이 저장되었습니다.', 'success');
        } else {
            const txt = await res.text();
            showNotification(`저장 실패: ${txt}`, 'danger');
        }
    } catch (e) {
        showNotification('설정 저장 중 오류가 발생했습니다.', 'danger');
    }
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
    document.getElementById('proxySnmpVersion').value = 'v2c';
    document.getElementById('proxySnmpCommunity').value = 'public';
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
            snmp_version: document.getElementById('proxySnmpVersion').value,
            snmp_community: document.getElementById('proxySnmpCommunity').value,
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
    document.getElementById('proxySnmpVersion').value = editingProxy.snmp_version || 'v2c';
    document.getElementById('proxySnmpCommunity').value = editingProxy.snmp_community || 'public';
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
    const originalHtml = testBtn.innerHTML;
    
    try {
        testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        testBtn.disabled = true;
        
        const response = await fetch(`/api/monitoring/test/${proxyId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`연결 테스트 성공: ${result.message}`, 'success');
            // 연결 성공 시 프록시 목록 새로고침하여 상태 업데이트 반영
            await loadProxies();
        } else {
            showNotification(`연결 테스트 실패: ${result.message}`, 'danger');
        }
    } catch (error) {
        console.error('연결 테스트 오류:', error);
        showNotification('연결 테스트 중 오류가 발생했습니다.', 'danger');
    } finally {
        testBtn.innerHTML = originalHtml;
        testBtn.disabled = false;
    }
}

// ==================== 자원사용률 관리 ====================

// 자원사용률 데이터 로드
async function loadResourcesData() {
    console.log('자원사용률 데이터 로딩 시작...');
    try {
        const qs = resourcesGroupId ? `?group_id=${resourcesGroupId}` : '';
        const response = await fetch(`/api/monitoring/resources${qs}`);
        console.log('Resources response status:', response.status);
        
        if (response.ok) {
            const result = await response.json();
            resources = result.data || [];
            console.log('로드된 자원 수:', resources.length);
            updateResourcesTable(resources); // Pass resources directly
            updateLastUpdate();
            updateCollectedItemsCount(); // 수집된 항목 수 업데이트
        } else {
            const errorText = await response.text();
            console.error('자원 API 오류:', response.status, errorText);
            showNotification(`자원 목록을 불러오는데 실패했습니다. (${response.status})`, 'danger');
        }
    } catch (error) {
        console.error('자원 목록 로딩 오류:', error);
        showNotification('자원 네트워크 오류: ' + error.message, 'danger');
    }
}

// 모니터링 요약 통계 로드
async function loadMonitoringSummary() {
    console.log('모니터링 요약 로딩 시작...');
    try {
        const response = await fetch('/api/monitoring/summary');
        
        if (response.ok) {
            const summary = await response.json();
            updateSummaryCards(summary);
        } else {
            console.error('요약 API 오류:', response.status);
        }
    } catch (error) {
        console.error('요약 로딩 오류:', error);
    }
}

// 요약 카드 업데이트
function updateSummaryCards(summary) {
    document.getElementById('totalProxiesCount').textContent = summary.total_proxies || 0;
    document.getElementById('activeProxiesCount').textContent = summary.active_proxies || 0;
    document.getElementById('offlineProxiesCount').textContent = summary.offline_proxies || 0;
}

// 자원사용률 테이블 업데이트
function updateResourcesTable(data) {
    const tbody = document.getElementById('resourcesTableBody');
    const emptyMessage = document.getElementById('resourcesEmptyMessage');
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '';
        emptyMessage.style.display = 'block';
        return;
    }
    
    emptyMessage.style.display = 'none';
    
    tbody.innerHTML = data.map(item => {
        const resource = item.resource_data;
        const cpuClass = getCpuClass(resource.cpu);
        const memoryClass = getMemoryClass(resource.memory);
        const role = item.is_main ? '메인' : '서브';
        const roleClass = item.is_main ? 'badge bg-primary' : 'badge bg-secondary';
        
        // 값이 'error' 또는 '-1'인 경우 '-'로 표시
        const formatValue = (value) => {
            if (value === 'error' || value === '-1' || value === -1) return '-';
            return value;
        };
        
        return `
            <tr>
                <td class="ps-3">
                    <div class="fw-medium">${item.proxy_name}</div>
                    <small class="text-muted">${item.host}</small>
                </td>
                <td>${item.group_name || '-'}</td>
                <td><span class="${roleClass}">${role}</span></td>
                <td><span class="${cpuClass}">${formatValue(resource.cpu)}${resource.cpu !== 'error' && resource.cpu !== '-1' ? '%' : ''}</span></td>
                <td><span class="${memoryClass}">${formatValue(resource.memory)}${resource.memory !== 'error' && resource.memory !== '-1' ? '%' : ''}</span></td>
                <td>${formatValue(resource.uc)}</td>
                <td>${formatValue(resource.cc)}</td>
                <td>${formatValue(resource.cs)}</td>
                <td>${formatValue(resource.http)}</td>
                <td>${formatValue(resource.https)}</td>
                <td>${formatValue(resource.ftp)}</td>
                <td>
                    ${resource.cpu === 'error' || resource.memory === 'error' ? 
                        '<span class="badge bg-danger">오류</span>' : 
                        '<span class="badge bg-success">정상</span>'}
                </td>
                <td>
                    <small class="text-muted">${resource.time || '-'}</small>
                </td>
            </tr>
        `;
    }).join('');
}

// CPU 사용률에 따른 CSS 클래스 반환
function getCpuClass(cpu) {
    if (cpu === 'error') return 'bg-secondary';
    const value = parseInt(cpu);
    if (value >= 80) return 'bg-danger';
    if (value >= 60) return 'bg-warning';
    return 'bg-success';
}

// 메모리 사용률에 따른 CSS 클래스 반환
function getMemoryClass(memory) {
    if (memory === 'error') return 'bg-secondary';
    const value = parseInt(memory);
    if (value >= 80) return 'bg-danger';
    if (value >= 60) return 'bg-warning';
    return 'bg-success';
}

// 마지막 업데이트 시간 갱신
function updateLastUpdate() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('ko-KR');
    document.getElementById('lastUpdate').textContent = timeString;
}

// 자원사용률 새로고침
async function refreshResources() {
    console.log('자원사용률 수동 새로고침');
    await loadResourcesData();
    await loadMonitoringSummary();
    showNotification('자원사용률이 업데이트되었습니다.', 'info');
}

// ==================== 모니터링 컨트롤 ====================

// 모니터링 시작
function startMonitoring() {
    if (isMonitoringActive) return;
    
    console.log(`모니터링 시작 - 주기: ${monitoringIntervalTime}초`);
    isMonitoringActive = true;
    
    // UI 업데이트
    updateMonitoringUI();
    // 수동 새로고침 버튼 활성화
    const refreshBtn = document.getElementById('manualRefreshBtn');
    if (refreshBtn) refreshBtn.disabled = false;
    
    // 즉시 첫 번째 데이터 로드
    loadResourcesData();
    loadMonitoringSummary();
    
    // 주기적 업데이트 시작
    monitoringInterval = setInterval(() => {
        loadResourcesData();
        loadMonitoringSummary();
    }, monitoringIntervalTime * 1000);
    
    // 다음 업데이트 시간 표시 시작
    updateNextUpdateTime();
    
    showNotification('모니터링이 시작되었습니다.', 'success');
}

// 모니터링 중지
function stopMonitoring() {
    if (!isMonitoringActive) return;
    
    console.log('모니터링 중지');
    isMonitoringActive = false;
    
    // 인터벌 정리
    if (monitoringInterval) {
        clearInterval(monitoringInterval);
        monitoringInterval = null;
    }
    
    if (nextUpdateTimeout) {
        clearTimeout(nextUpdateTimeout);
        nextUpdateTimeout = null;
    }
    
    // 수동 새로고침 버튼 비활성화
    const refreshBtn = document.getElementById('manualRefreshBtn');
    if (refreshBtn) refreshBtn.disabled = true;

    // UI 업데이트
    updateMonitoringUI();
    document.getElementById('nextUpdate').textContent = '-';
    
    showNotification('모니터링이 중지되었습니다.', 'warning');
}

// 모니터링 주기 업데이트
function updateMonitoringInterval() {
    const newInterval = parseInt(document.getElementById('monitoringInterval').value);
    monitoringIntervalTime = newInterval;
    
    console.log(`모니터링 주기 변경: ${monitoringIntervalTime}초`);
    
    // 모니터링이 활성 상태라면 재시작
    if (isMonitoringActive) {
        stopMonitoring();
        setTimeout(() => startMonitoring(), 100);
    }
    
    showNotification(`모니터링 주기가 ${monitoringIntervalTime}초로 변경되었습니다.`, 'info');
}

// 모니터링 UI 업데이트
function updateMonitoringUI() {
    const status = document.getElementById('monitoringStatus');
    const startBtn = document.getElementById('startMonitoringBtn');
    const stopBtn = document.getElementById('stopMonitoringBtn');
    
    if (isMonitoringActive) {
        status.textContent = '실행중';
        status.className = 'badge bg-success';
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        status.textContent = '정지됨';
        status.className = 'badge bg-secondary';
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

// 다음 업데이트 시간 표시
function updateNextUpdateTime() {
    if (!isMonitoringActive) return;
    
    let countdown = monitoringIntervalTime;
    
    const updateCountdown = () => {
        if (!isMonitoringActive) return;
        
        document.getElementById('nextUpdate').textContent = `${countdown}초 후`;
        countdown--;
        
        if (countdown >= 0) {
            nextUpdateTimeout = setTimeout(updateCountdown, 1000);
        } else {
            countdown = monitoringIntervalTime;
            nextUpdateTimeout = setTimeout(updateCountdown, 1000);
        }
    };
    
    updateCountdown();
}

// 수집된 항목 수 업데이트
function updateCollectedItemsCount() {
    const countElement = document.getElementById('collectedItemsCount');
    if (countElement) {
        // 수집되는 항목: CPU, Memory, UC, CC, CS, HTTP, HTTPS, FTP = 8개
        countElement.textContent = '8';
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

// ==================== 세션 브라우저 ====================
function populateSessionProxySelect() {
    // 그룹 기반으로 수집하도록 변경되어 프록시 단일 선택은 보조로 유지하거나 미사용
    const select = document.getElementById('sessionProxySelect');
    if (!select) return;
    select.innerHTML = '';
    const allOption = document.createElement('option');
    allOption.value = '';
    allOption.textContent = '전체 활성 프록시';
    select.appendChild(allOption);
    proxies
        .filter(p => p.is_active)
        .forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = `${p.name} (${p.host})`;
            select.appendChild(opt);
        });
}

async function loadSessions() {
    const select = document.getElementById('sessionProxySelect');
    const gsel = document.getElementById('sessionGroupSelect');
    const proxyId = select && select.value ? parseInt(select.value) : null;
    sessionsGroupId = gsel && gsel.value ? parseInt(gsel.value) : sessionsGroupId;
    try {
        // 그룹 또는 프록시를 선택한 경우에만 조회
        if (!proxyId && !sessionsGroupId) {
            return showNotification('그룹 또는 프록시를 선택하세요.', 'warning');
        }
        const params = new URLSearchParams();
        if (!proxyId && sessionsGroupId) { params.set('group_id', sessionsGroupId); params.set('persist','1'); }
        const url = proxyId ? `/api/monitoring/sessions/${proxyId}?persist=1` : `/api/monitoring/sessions?${params.toString()}`;
        const res = await fetch(url);
        if (!res.ok) {
            const txt = await res.text();
            return showNotification(`세션 조회 실패: ${txt}`, 'danger');
        }
        const data = await res.json();
        const list = proxyId ? [data] : (data.data || []);
        // 동적 헤더 구성: 각 항목의 headers 사용, 없으면 첫 세션의 키 합침
        const headerSet = new Set();
        list.forEach(item => {
            (item.headers || []).forEach(h => headerSet.add(h));
        });
        if (headerSet.size === 0) {
            list.forEach(item => {
                const s = (item.sessions || [])[0];
                if (s) Object.keys(s).forEach(k => headerSet.add(k));
            });
        }
        sessionHeaders = Array.from(headerSet);
        sessions = list;
        renderSessionsTable(sessions, sessionHeaders);
    } catch (e) {
        console.error('세션 로드 오류:', e);
        showNotification('세션 로드 중 오류가 발생했습니다.', 'danger');
    }
}

function renderSessionsTable(items, headers) {
    const thead = document.getElementById('sessionsTableHead');
    const tbody = document.getElementById('sessionsTableBody');
    const emptyMessage = document.getElementById('sessionsEmptyMessage');
    if (!tbody || !thead) return;

    // 헤더 렌더링
    const headerCells = ['<th class="border-0 ps-3 sticky-col">Proxy</th>'].concat(
        headers.map(h => `<th class="border-0">${escapeHtml(h)}</th>`) 
    );
    thead.innerHTML = `<tr>${headerCells.join('')}</tr>`;

    if (!items || items.length === 0) {
        tbody.innerHTML = '';
        if (emptyMessage) emptyMessage.style.display = 'block';
        return;
    }

    if (emptyMessage) emptyMessage.style.display = 'none';

    const rows = [];
    items.forEach(item => {
        const proxyName = item.proxy_name || item.host || '';
        (item.sessions || []).forEach(s => {
            const tds = [`<td class="ps-3 sticky-col">${proxyName}</td>`];
            headers.forEach(h => {
                let val = s[h];
                if (h === 'User Name' && !val) val = s['User'];
                if (h === 'Age(seconds)' && !val) val = s['Status'] || s['Age(seconds) Status'];
                val = (val === undefined || val === null || val === '') ? '-' : val;
                tds.push(`<td class="truncate">${escapeHtml(String(val))}</td>`);
            });
            rows.push(`<tr>${tds.join('')}</tr>`);
        });
    });
    tbody.innerHTML = rows.join('');
}

async function collectSessionsByGroup() {
    const sel = document.getElementById('sessionGroupSelect');
    sessionsGroupId = sel && sel.value ? parseInt(sel.value) : null;
    if (!sessionsGroupId) return showNotification('그룹을 선택하세요.', 'warning');
    try {
        const res = await fetch(`/api/monitoring/sessions/group/${sessionsGroupId}?persist=1`);
        if (!res.ok) {
            const txt = await res.text();
            return showNotification(`저장 실패: ${txt}`, 'danger');
        }
        showNotification('세션 저장이 완료되었습니다.', 'success');
    } catch (e) {
        showNotification('세션 저장 중 오류가 발생했습니다.', 'danger');
    }
}

async function searchSessions() {
    const qInput = document.getElementById('sessionSearchInput');
    sessionFilters.q = qInput ? qInput.value.trim() : '';
    sessionPage = 1;
    await loadSessionSearchPage();
}

function updateSessionsSearchTable(items) {
    const tbody = document.getElementById('sessionsTableBody');
    const emptyMessage = document.getElementById('sessionsEmptyMessage');
    if (!tbody) return;
    if (!items || items.length === 0) {
        tbody.innerHTML = '';
        if (emptyMessage) emptyMessage.style.display = 'block';
        return;
    }
    if (emptyMessage) emptyMessage.style.display = 'none';
    tbody.innerHTML = items.map(r => `
        <tr>
            <td class="ps-3">${r.proxy_id || '-'}</td>
            <td>${escapeHtml(r.client_ip || '-')}</td>
            <td>${escapeHtml(r.server_ip || '-')}</td>
            <td>${escapeHtml(r.protocol || '-')}</td>
            <td>${escapeHtml(r.user || '-')}</td>
            <td class="truncate">${escapeHtml(r.policy || '-')}</td>
            <td>${escapeHtml(r.category || '-')}</td>
        </tr>
    `).join('');
}

async function loadSessionSearchPage() {
    const params = new URLSearchParams();
    if (sessionsGroupId) params.set('group_id', sessionsGroupId);
    if (sessionFilters.q) params.set('q', sessionFilters.q);
    if (sessionFilters.protocol) params.set('protocol', sessionFilters.protocol);
    if (sessionFilters.status) params.set('status', sessionFilters.status);
    if (sessionFilters.client_ip) params.set('client_ip', sessionFilters.client_ip);
    if (sessionFilters.server_ip) params.set('server_ip', sessionFilters.server_ip);
    if (sessionFilters.user) params.set('user', sessionFilters.user);
    if (sessionFilters.url) params.set('url', sessionFilters.url);
    params.set('page', sessionPage);
    params.set('page_size', sessionPageSize);
    const res = await fetch(`/api/monitoring/sessions/search?${params.toString()}`);
    if (!res.ok) {
        const txt = await res.text();
        return showNotification(`검색 실패: ${txt}`, 'danger');
    }
    const data = await res.json();
    sessionTotal = data.total || 0;
    updateSessionsSearchTable(data.data || []);
    renderSessionPagination();
}

function renderSessionPagination() {
    const totalPages = Math.max(1, Math.ceil(sessionTotal / sessionPageSize));
    let html = '';
    html += `<nav><ul class="pagination pagination-sm justify-content-end m-2">`;
    const disabledPrev = sessionPage <= 1 ? ' disabled' : '';
    const disabledNext = sessionPage >= totalPages ? ' disabled' : '';
    html += `<li class="page-item${disabledPrev}"><a class="page-link" href="#" onclick="changeSessionPage(${sessionPage-1});return false;">이전</a></li>`;
    html += `<li class="page-item disabled"><span class="page-link">${sessionPage} / ${totalPages}</span></li>`;
    html += `<li class="page-item${disabledNext}"><a class="page-link" href="#" onclick="changeSessionPage(${sessionPage+1});return false;">다음</a></li>`;
    html += `</ul></nav>`;
    const container = document.getElementById('sessionsPagination');
    if (container) container.innerHTML = html;
}

function changeSessionPage(p) {
    if (p < 1) return;
    const totalPages = Math.max(1, Math.ceil(sessionTotal / sessionPageSize));
    if (p > totalPages) return;
    sessionPage = p;
    loadSessionSearchPage();
}

function changeSessionPageSize(v) {
    const n = parseInt(v || '100');
    sessionPageSize = isNaN(n) ? 100 : n;
    sessionPage = 1;
    loadSessionSearchPage();
}

function downloadSessionsCsv() {
    const params = new URLSearchParams();
    if (sessionsGroupId) params.set('group_id', sessionsGroupId);
    if (sessionFilters.q) params.set('q', sessionFilters.q);
    if (sessionFilters.protocol) params.set('protocol', sessionFilters.protocol);
    if (sessionFilters.status) params.set('status', sessionFilters.status);
    if (sessionFilters.client_ip) params.set('client_ip', sessionFilters.client_ip);
    if (sessionFilters.server_ip) params.set('server_ip', sessionFilters.server_ip);
    if (sessionFilters.user) params.set('user', sessionFilters.user);
    if (sessionFilters.url) params.set('url', sessionFilters.url);
    window.location.href = `/api/monitoring/sessions/export?${params.toString()}`;
}

function escapeHtml(s) {
    return s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

function bindSessionFilters() {
    const p = document.getElementById('filterProtocol');
    const s = document.getElementById('filterStatus');
    const cip = document.getElementById('filterClientIP');
    const sip = document.getElementById('filterServerIP');
    const u = document.getElementById('filterUser');
    const url = document.getElementById('filterUrl');
    const debounce = (fn, ms) => { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); }; };
    const onChange = debounce(() => {
        sessionFilters.protocol = p ? p.value.trim() : '';
        sessionFilters.status = s ? s.value.trim() : '';
        sessionFilters.client_ip = cip ? cip.value.trim() : '';
        sessionFilters.server_ip = sip ? sip.value.trim() : '';
        sessionFilters.user = u ? u.value.trim() : '';
        sessionFilters.url = url ? url.value.trim() : '';
        sessionPage = 1;
        loadSessionSearchPage();
    }, 300);
    ;[p,s,cip,sip,u,url].forEach(el => el && el.addEventListener('input', onChange));
}