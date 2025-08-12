// 프록시 모니터링 시스템 - 관리 페이지 (PPAT)

// 설정 관리 모듈
const ConfigManager = {
    // 기본 설정값
    defaults: {
        monitoring: {
            intervalTime: 30,
            cpuThreshold: 80,
            memoryThreshold: 80,
            defaultInterval: 30,
            pageSize: 100
        },
        proxy: {
            sshPort: 22,
            snmpPort: 161,
            snmpVersion: 'v2c',
            snmpCommunity: 'public',
            username: 'root'
        }
    },
    
    // 설정 로드
    async loadConfig() {
        try {
            const response = await fetch('/api/monitoring/config');
            if (response.ok) {
                const config = await response.json();
                return {
                    monitoring: {
                        intervalTime: config.default_interval || this.defaults.monitoring.intervalTime,
                        cpuThreshold: config.cpu_threshold || this.defaults.monitoring.cpuThreshold,
                        memoryThreshold: config.memory_threshold || this.defaults.monitoring.memoryThreshold,
                        defaultInterval: config.default_interval || this.defaults.monitoring.defaultInterval,
                        pageSize: this.defaults.monitoring.pageSize
                    },
                    proxy: { ...this.defaults.proxy }
                };
            }
        } catch (error) {
            console.error('설정 로드 실패:', error);
        }
        return {
            monitoring: { ...this.defaults.monitoring },
            proxy: { ...this.defaults.proxy }
        };
    },
    
    // 설정 저장
    async saveConfig(config) {
        try {
            const response = await fetch('/api/monitoring/config', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    default_interval: config.monitoring.defaultInterval,
                    cpu_threshold: config.monitoring.cpuThreshold,
                    memory_threshold: config.monitoring.memoryThreshold
                })
            });
            
            if (response.ok) {
                return true;
            }
            throw new Error('설정 저장 실패');
        } catch (error) {
            console.error('설정 저장 오류:', error);
            throw error;
        }
    }
};

// 상태 관리 모듈
const AppState = {
    // 프록시 관련 상태
    proxy: {
        list: [],
        editing: null,
        modal: null
    },
    
    // 그룹 관련 상태
    group: {
        list: [],
        editing: null,
        modal: null
    },
    
    // 모니터링 관련 상태
    monitoring: {
        resources: [],
        interval: null,
        intervalTime: 30,
        isActive: false,
        nextUpdateTimeout: null,
        config: {
            cpuThreshold: 80,
            memoryThreshold: 80,
            defaultInterval: 30
        }
    },
    
    // 세션 관련 상태
    session: {
        list: [],
        headers: [],
        groupId: null,
        resourcesGroupId: null,
        filters: {
            protocol: '',
            status: '',
            client_ip: '',
            server_ip: '',
            user: '',
            url: '',
            q: ''
        },
        pagination: {
            page: 1,
            pageSize: 100,
            total: 0
        }
    },
    
    // 현재 활성 탭
    currentTab: 'management',
    
    // 상태 업데이트 메서드들
    updateProxies(proxies) {
        this.proxy.list = proxies;
    },
    
    updateGroups(groups) {
        this.group.list = groups;
    },
    
    updateResources(resources) {
        this.monitoring.resources = resources;
    },
    
    updateSessions(sessions) {
        this.session.list = sessions;
    },
    
    setCurrentTab(tab) {
        this.currentTab = tab;
    },
    
    // 모니터링 상태 관리
    startMonitoring() {
        this.monitoring.isActive = true;
    },
    
    stopMonitoring() {
        this.monitoring.isActive = false;
        if (this.monitoring.interval) {
            clearInterval(this.monitoring.interval);
            this.monitoring.interval = null;
        }
        if (this.monitoring.nextUpdateTimeout) {
            clearTimeout(this.monitoring.nextUpdateTimeout);
            this.monitoring.nextUpdateTimeout = null;
        }
    },
    
    // 세션 페이지네이션 관리
    updateSessionPagination(page, total) {
        this.session.pagination.page = page;
        this.session.pagination.total = total;
    },
    
    setSessionPageSize(size) {
        this.session.pagination.pageSize = size;
    }
};

// DOM 로드 완료 후 초기화
// 애플리케이션 초기화 컨트롤러
const AppInitializer = {
    // 초기화 실행
    async initialize() {
        console.log('PPAT 시스템 초기화 중...');
        
        try {
            // 설정 로드
            const config = await ConfigManager.loadConfig();
            this.applyConfig(config);
            
            // Bootstrap 모달 초기화
            this.initializeModals();
            
            // 초기 데이터 로드
            await this.loadInitialData();
            
            // 자동 새로고침 설정
            this.setupAutoRefresh();
            
            // 페이지 언로드 핸들러 설정
            this.setupUnloadHandler();
            
            console.log('PPAT 시스템 초기화 완료');
        } catch (error) {
            console.error('시스템 초기화 실패:', error);
            showNotification('시스템 초기화 중 오류가 발생했습니다.', 'danger');
        }
    },
    
    // 설정 적용
    applyConfig(config) {
        AppState.monitoring.intervalTime = config.monitoring.intervalTime;
        AppState.monitoring.config = {
            cpuThreshold: config.monitoring.cpuThreshold,
            memoryThreshold: config.monitoring.memoryThreshold,
            defaultInterval: config.monitoring.defaultInterval
        };
        AppState.session.pagination.pageSize = config.monitoring.pageSize;
    },
    
    // 모달 초기화
    initializeModals() {
        AppState.proxy.modal = new bootstrap.Modal(document.getElementById('proxyModal'));
        AppState.group.modal = new bootstrap.Modal(document.getElementById('groupModal'));
    },
    
    // 초기 데이터 로드
    async loadInitialData() {
        await Promise.all([
            loadGroups(),
            loadProxies(),
            initGroupSelectors()
        ]);
    },
    
    // 자동 새로고침 설정
    setupAutoRefresh() {
        const interval = AppState.monitoring.config.defaultInterval * 1000;
        AppState.monitoring.autoRefreshInterval = setInterval(() => {
            if (AppState.currentTab === 'management') {
                this.refreshManagementData();
            }
        }, interval);
    },
    
    // 관리 탭 데이터 새로고침
    async refreshManagementData() {
        await Promise.all([
            loadProxies(),
            loadGroups()
        ]);
    },
    
    // 언로드 핸들러 설정
    setupUnloadHandler() {
        window.addEventListener('beforeunload', () => {
            if (AppState.monitoring.autoRefreshInterval) {
                clearInterval(AppState.monitoring.autoRefreshInterval);
            }
            if (AppState.monitoring.interval) {
                clearInterval(AppState.monitoring.interval);
            }
            if (AppState.monitoring.nextUpdateTimeout) {
                clearTimeout(AppState.monitoring.nextUpdateTimeout);
            }
        });
    }
};

// DOM 로드 완료 시 초기화 실행
document.addEventListener('DOMContentLoaded', () => {
    AppInitializer.initialize();
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
            resSel.onchange = () => { AppState.session.resourcesGroupId = resSel.value ? parseInt(resSel.value) : null; if (AppState.monitoring.isActive) { loadResourcesData(); } };
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
    AppState.proxy.editing = null;
    document.getElementById('modalTitle').textContent = '프록시 추가';
    clearForm();
    AppState.proxy.modal.show();
}

// 프록시 모달 닫기
function closeModal() {
    console.log('프록시 모달 닫기');
    AppState.proxy.modal.hide();
    AppState.proxy.editing = null;
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
    
    // 입력값 수집 및 검증
    const formData = {
        name: document.getElementById('proxyName').value.trim(),
        host: document.getElementById('proxyHost').value.trim(),
        ssh_port: document.getElementById('proxySshPort').value,
        snmp_port: document.getElementById('proxySnmpPort').value,
        snmp_version: document.getElementById('proxySnmpVersion').value,
        snmp_community: document.getElementById('proxySnmpCommunity').value,
        username: document.getElementById('proxyUsername').value,
        password: document.getElementById('proxyPassword').value,
        description: document.getElementById('proxyDescription').value,
        is_active: document.getElementById('proxyIsActive').checked,
        is_main: document.getElementById('proxyIsMain').checked,
        group_id: document.getElementById('proxyGroup').value
    };
    
    // 필수 필드 검증
    const requiredFields = ['name', 'host'];
    for (const field of requiredFields) {
        const error = ErrorHandler.validateInput(formData[field], [ValidationRules.required]);
        if (error) {
            showNotification(`${field === 'name' ? '이름' : 'IP 주소'}은(는) ${error}`, 'warning');
            return;
        }
    }
    
    // IP 주소 형식 검증
    const ipError = ErrorHandler.validateInput(formData.host, [ValidationRules.ipAddress]);
    if (ipError) {
        showNotification(ipError, 'warning');
        return;
    }
    
    // 비밀번호 검증 (새로운 프록시 추가 시 또는 비밀번호 변경 시)
    if (!AppState.proxy.editing && !formData.password) {
        showNotification('비밀번호는 필수 항목입니다.', 'warning');
        return;
    }
    if (formData.password) {
        const passwordError = ErrorHandler.validateInput(formData.password, [ValidationRules.password]);
        if (passwordError) {
            showNotification(passwordError, 'warning');
            return;
        }
    }
    
    // 포트 번호 검증
    const portFields = ['ssh_port', 'snmp_port'];
    for (const field of portFields) {
        const portError = ErrorHandler.validateInput(formData[field], [ValidationRules.port]);
        if (portError) {
            showNotification(`${field === 'ssh_port' ? 'SSH' : 'SNMP'} ${portError}`, 'warning');
            return;
        }
    }
    
    const saveButton = document.getElementById('saveButton');
    const originalText = saveButton.innerHTML;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>저장중...';
    saveButton.disabled = true;
    
    try {
        // 데이터 정제
        const data = {
            ...formData,
            ssh_port: parseInt(formData.ssh_port),
            snmp_port: parseInt(formData.snmp_port),
            group_id: formData.group_id ? parseInt(formData.group_id) : null
        };
        
        const method = AppState.proxy.editing ? 'PUT' : 'POST';
        const url = AppState.proxy.editing ? 
            `/api/proxies/${AppState.proxy.editing.id}` : 
            '/api/proxies';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('프록시 저장 성공:', result);
            
            // 데이터 새로고침
            await Promise.all([
                loadProxies(),
                loadGroups()
            ]);
            
            AppState.proxy.modal.hide();
            showNotification(
                AppState.proxy.editing ? '프록시가 수정되었습니다.' : '프록시가 추가되었습니다.', 
                'success'
            );
        } else {
            const errorMessage = await ErrorHandler.handleApiError(response, {
                409: '동일한 이름 또는 IP 주소를 가진 프록시가 이미 존재합니다.'
            });
            showNotification('프록시 저장 실패: ' + errorMessage, 'danger');
        }
    } catch (error) {
        console.error('프록시 저장 오류:', error);
        showNotification('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'danger');
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
        const qs = AppState.session.resourcesGroupId ? `?group_id=${AppState.session.resourcesGroupId}` : '';
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
    await MonitoringController.executeMonitoringTask();
    showNotification('자원사용률이 업데이트되었습니다.', 'info');
}

// ==================== 모니터링 컨트롤 ====================

// 모니터링 컨트롤러
const MonitoringController = {
    // 모니터링 작업 큐
    taskQueue: Promise.resolve(),
    
    // 모니터링 시작
    async startMonitoring() {
        if (AppState.monitoring.isActive) return;
        
        console.log(`모니터링 시작 - 주기: ${AppState.monitoring.intervalTime}초`);
        AppState.monitoring.isActive = true;
        
        // UI 업데이트
        this.updateUI();
        
        // 수동 새로고침 버튼 활성화
        const refreshBtn = document.getElementById('manualRefreshBtn');
        if (refreshBtn) refreshBtn.disabled = false;
        
        // 초기 데이터 로드
        await this.executeMonitoringTask();
        
        // 주기적 업데이트 시작
        AppState.monitoring.interval = setInterval(() => {
            this.executeMonitoringTask();
        }, AppState.monitoring.intervalTime * 1000);
        
        // 다음 업데이트 시간 표시 시작
        this.startCountdown();
        
        showNotification('모니터링이 시작되었습니다.', 'success');
    },
    
    // 모니터링 중지
    stopMonitoring() {
        if (!AppState.monitoring.isActive) return;
        
        console.log('모니터링 중지');
        AppState.monitoring.isActive = false;
        
        // 인터벌 정리
        if (AppState.monitoring.interval) {
            clearInterval(AppState.monitoring.interval);
            AppState.monitoring.interval = null;
        }
        
        if (AppState.monitoring.nextUpdateTimeout) {
            clearTimeout(AppState.monitoring.nextUpdateTimeout);
            AppState.monitoring.nextUpdateTimeout = null;
        }
        
        // 수동 새로고침 버튼 비활성화
        const refreshBtn = document.getElementById('manualRefreshBtn');
        if (refreshBtn) refreshBtn.disabled = true;
        
        // UI 업데이트
        this.updateUI();
        document.getElementById('nextUpdate').textContent = '-';
        
        showNotification('모니터링이 중지되었습니다.', 'warning');
    },
    
    // 모니터링 주기 업데이트
    async updateInterval(newInterval) {
        AppState.monitoring.intervalTime = parseInt(newInterval);
        
        console.log(`모니터링 주기 변경: ${AppState.monitoring.intervalTime}초`);
        
        // 모니터링이 활성 상태라면 재시작
        if (AppState.monitoring.isActive) {
            this.stopMonitoring();
            await new Promise(resolve => setTimeout(resolve, 100));
            await this.startMonitoring();
        }
        
        showNotification(`모니터링 주기가 ${AppState.monitoring.intervalTime}초로 변경되었습니다.`, 'info');
    },
    
    // UI 업데이트
    updateUI() {
        const status = document.getElementById('monitoringStatus');
        const startBtn = document.getElementById('startMonitoringBtn');
        const stopBtn = document.getElementById('stopMonitoringBtn');
        
        if (AppState.monitoring.isActive) {
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
    },
    
    // 카운트다운 시작
    startCountdown() {
        if (!AppState.monitoring.isActive) return;
        
        let countdown = AppState.monitoring.intervalTime;
        
        const updateCountdown = () => {
            if (!AppState.monitoring.isActive) return;
            
            document.getElementById('nextUpdate').textContent = `${countdown}초 후`;
            countdown--;
            
            if (countdown >= 0) {
                AppState.monitoring.nextUpdateTimeout = setTimeout(updateCountdown, 1000);
            } else {
                countdown = AppState.monitoring.intervalTime;
                AppState.monitoring.nextUpdateTimeout = setTimeout(updateCountdown, 1000);
            }
        };
        
        updateCountdown();
    },
    
    // 모니터링 작업 실행 (큐 사용)
    async executeMonitoringTask() {
        // 이전 작업이 완료될 때까지 대기
        this.taskQueue = this.taskQueue.then(async () => {
            try {
                // 병렬로 데이터 로드
                await Promise.all([
                    loadResourcesData(),
                    loadMonitoringSummary()
                ]);
            } catch (error) {
                console.error('모니터링 작업 실행 중 오류:', error);
                showNotification('모니터링 데이터 수집 중 오류가 발생했습니다.', 'danger');
            }
        });
        
        return this.taskQueue;
    }
};

// 수집된 항목 수 업데이트
function updateCollectedItemsCount() {
    const countElement = document.getElementById('collectedItemsCount');
    if (countElement) {
        // 수집되는 항목: CPU, Memory, UC, CC, CS, HTTP, HTTPS, FTP = 8개
        countElement.textContent = '8';
    }
}

// ==================== 공통 유틸리티 ====================

// 에러 처리 유틸리티
const ErrorHandler = {
    // API 에러 처리
    async handleApiError(response, customErrorMap = {}) {
        let errorMessage = '알 수 없는 오류가 발생했습니다.';
        
        try {
            const errorData = await response.json();
            
            // 커스텀 에러 매핑 확인
            if (customErrorMap[response.status]) {
                errorMessage = customErrorMap[response.status];
            } else if (errorData.message) {
                errorMessage = errorData.message;
            } else if (errorData.error) {
                errorMessage = errorData.error;
            }
        } catch (e) {
            // JSON 파싱 실패 시 HTTP 상태 기반 메시지
            errorMessage = this.getHttpStatusMessage(response.status);
        }
        
        return errorMessage;
    },
    
    // HTTP 상태 코드별 기본 메시지
    getHttpStatusMessage(status) {
        const statusMessages = {
            400: '잘못된 요청입니다.',
            401: '인증이 필요합니다.',
            403: '접근이 거부되었습니다.',
            404: '요청한 리소스를 찾을 수 없습니다.',
            409: '요청이 현재 서버의 상태와 충돌합니다.',
            500: '서버 내부 오류가 발생했습니다.',
            502: '게이트웨이 오류가 발생했습니다.',
            503: '서비스를 사용할 수 없습니다.',
            504: '게이트웨이 시간 초과가 발생했습니다.'
        };
        
        return statusMessages[status] || '서버와 통신 중 오류가 발생했습니다.';
    },
    
    // 입력 값 검증
    validateInput(value, rules) {
        for (const rule of rules) {
            if (!rule.validate(value)) {
                return rule.message;
            }
        }
        return null;
    }
};

// 입력 검증 규칙
const ValidationRules = {
    required: {
        validate: value => value !== undefined && value !== null && value.toString().trim() !== '',
        message: '이 필드는 필수입니다.'
    },
    ipAddress: {
        validate: value => /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(value),
        message: '올바른 IP 주소 형식이 아닙니다.'
    },
    password: {
        validate: value => /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$/.test(value),
        message: '비밀번호는 8자 이상이며, 영문, 숫자, 특수문자를 포함해야 합니다.'
    },
    port: {
        validate: value => {
            const port = parseInt(value);
            return !isNaN(port) && port >= 1 && port <= 65535;
        },
        message: '포트는 1-65535 사이의 숫자여야 합니다.'
    }
};

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
    AppState.session.groupId = gsel && gsel.value ? parseInt(gsel.value) : AppState.session.groupId;

    try {
        // 그룹 또는 프록시를 선택한 경우에만 조회
        if (!proxyId && !AppState.session.groupId) {
            return showNotification('그룹 또는 프록시를 선택하세요.', 'warning');
        }

        // 기존 DataTable 제거
        const table = $('#sessionsTable').DataTable();
        if (table) {
            table.destroy();
        }

        // DataTables 초기화
        $('#sessionsTable').DataTable({
            serverSide: true,
            processing: true,
            ajax: {
                url: '/api/monitoring/sessions/datatables',
                data: function(d) {
                    d.group_id = AppState.session.groupId;
                    d.proxy_id = proxyId;
                }
            },
            columns: [
                { title: 'ID', data: 0 },
                { title: 'Proxy', data: 1 },
                { title: 'Client IP', data: 2 },
                { title: 'Server IP', data: 3 },
                { title: 'User', data: 4 },
                { title: 'URL Host', data: 5 },
                { title: 'Category', data: 6 },
                { 
                    title: 'Bytes Sent',
                    data: 7,
                    render: function(data) {
                        return data ? formatBytes(data) : '-';
                    }
                },
                { 
                    title: 'Bytes Received',
                    data: 8,
                    render: function(data) {
                        return data ? formatBytes(data) : '-';
                    }
                },
                { 
                    title: 'Age',
                    data: 9,
                    render: function(data) {
                        return data ? formatDuration(data) : '-';
                    }
                },
                { 
                    title: 'Created At',
                    data: 10,
                    render: function(data) {
                        return data ? new Date(data).toLocaleString() : '-';
                    }
                }
            ],
            columnDefs: [
                { targets: [0], visible: false, searchable: false }
            ],
            order: [[10, 'desc']], // 생성일시 기준 내림차순
            pageLength: AppState.session.pagination.pageSize,
            dom: 'Bfrtip',
            buttons: [
                'copy',
                'excel',
                'csv',
                {
                    extend: 'colvis',
                    text: '컬럼 설정'
                }
            ],
            language: {
                processing: "처리 중...",
                search: "검색:",
                lengthMenu: "_MENU_ 개씩 보기",
                info: "_START_ - _END_ / _TOTAL_",
                infoEmpty: "데이터 없음",
                infoFiltered: "(_MAX_ 개의 데이터에서 필터링됨)",
                infoPostFix: "",
                loadingRecords: "로딩중...",
                zeroRecords: "검색 결과가 없습니다",
                emptyTable: "데이터가 없습니다",
                paginate: {
                    first: "처음",
                    previous: "이전",
                    next: "다음",
                    last: "마지막"
                }
            },
            responsive: true
        });

        // 행 클릭 시 상세 보기
        $('#sessionsTable tbody').off('click').on('click', 'tr', async function() {
            const table = $('#sessionsTable').DataTable();
            const rowData = table.row(this).data();
            if (!rowData) return;
            const id = rowData[0];
            try {
                const res = await fetch(`/api/monitoring/sessions/detail/${id}`);
                const json = await res.json();
                if (json && json.success) {
                    showSessionDetailModal(json.data);
                } else {
                    showNotification('상세 정보를 불러오지 못했습니다.', 'danger');
                }
            } catch (e) {
                console.error(e);
                showNotification('상세 조회 중 오류가 발생했습니다.', 'danger');
            }
        });

    } catch (e) {
        console.error('세션 로드 오류:', e);
        showNotification('세션 로드 중 오류가 발생했습니다.', 'danger');
    }
}

async function fetchSessionsFromSource() {
    const gsel = document.getElementById('sessionGroupSelect');
    const psel = document.getElementById('sessionProxySelect');
    const groupId = gsel && gsel.value ? parseInt(gsel.value) : null;
    const proxyId = psel && psel.value ? parseInt(psel.value) : null;
    if (!groupId && !proxyId) {
        return showNotification('그룹 또는 프록시를 선택하세요.', 'warning');
    }
    try {
        if (groupId) {
            const res = await fetch(`/api/monitoring/sessions/group/${groupId}?persist=1`);
            const json = await res.json();
            if (!json || json.success !== true) {
                showNotification('그룹 세션 수집 실패', 'danger');
            }
        } else if (proxyId) {
            const res = await fetch(`/api/monitoring/sessions/${proxyId}?persist=1`);
            const json = await res.json();
            if (!json || json.error) {
                showNotification('프록시 세션 수집 실패', 'danger');
            }
        }
        // 수집 후 테이블 새로 고침
        loadSessions();
        showNotification('세션을 수집했습니다.', 'success');
    } catch (e) {
        console.error(e);
        showNotification('세션 수집 중 오류가 발생했습니다.', 'danger');
    }
}

// 바이트 크기 포맷팅
function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showSessionDetailModal(data) {
    const modalEl = document.getElementById('sessionDetailModal');
    if (!modalEl) return;
    const lines = [];
    const orderedKeys = [
        'id','group_id','proxy_id','client_ip','server_ip','protocol','user','category',
        'url_host','url','transaction','cust_id','user_name','client_side_mwg_ip','server_side_mwg_ip',
        'cl_bytes_sent','cl_bytes_received','srv_bytes_sent','srv_bytes_received','age_seconds','in_use',
        'creation_time','created_at'
    ];
    const keys = new Set(Object.keys(data));
    // Primary fields first
    orderedKeys.forEach(k => { if (keys.has(k)) { lines.push(`${k}: ${data[k] ?? ''}`); keys.delete(k); } });
    // Remaining fields
    Array.from(keys).sort().forEach(k => { lines.push(`${k}: ${data[k] ?? ''}`); });
    document.getElementById('sessionDetailContent').textContent = lines.join('\n');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}

// 시간 간격 포맷팅
function formatDuration(seconds) {
    if (!seconds) return '0s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    const parts = [];
    if (h > 0) parts.push(h + 'h');
    if (m > 0) parts.push(m + 'm');
    if (s > 0 || parts.length === 0) parts.push(s + 's');
    return parts.join(' ');
}

