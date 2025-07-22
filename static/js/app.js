// Vue.js 애플리케이션
const { createApp } = Vue;

createApp({
    data() {
        return {
            // 현재 탭
            currentTab: 'dashboard',
            
            // 데이터
            groups: [],
            servers: [],
            resources: [],
            sessions: [],
            latestResources: [],
            
            // 모니터링 상태
            monitoringStatus: {
                active: false,
                interval: 5
            },
            monitoringInterval: 5,
            
            // 필터 및 검색
            selectedGroupId: '',
            selectedGroupIdForMonitoring: '',
            selectedProxyIdForSessions: '',
            sessionSearch: '',
            
            // 모달 상태
            showGroupModal: false,
            showServerModal: false,
            showSessionStats: false,
            
            // 폼 데이터
            groupForm: {
                name: '',
                description: ''
            },
            serverForm: {
                name: '',
                host: '',
                group_id: '',
                username: 'root',
                password: '123456',
                ssh_port: 22,
                snmp_port: 161,
                is_main: false,
                is_active: true,
                description: ''
            },
            
            // 편집 상태
            editingGroup: null,
            editingServer: null,
            
            // 임계값
            thresholds: {
                cpu: 80,
                memory: 85,
                disk: 90,
                network_in: 1000,
                network_out: 1000
            },
            
            // 세션 통계
            sessionStats: {
                by_ip: [],
                by_proxy: [],
                by_url: []
            },
            
            // Socket.IO
            socket: null
        }
    },
    
    computed: {
        // 대시보드 통계
        totalProxies() {
            return this.servers.length;
        },
        onlineProxies() {
            return this.latestResources.filter(r => r.status === 'online').length;
        },
        totalSessions() {
            return this.latestResources.reduce((sum, r) => sum + (r.session_count || 0), 0);
        },
        totalGroups() {
            return this.groups.length;
        },
        
        // 필터된 서버 목록
        filteredServers() {
            if (!this.selectedGroupId) return this.servers;
            return this.servers.filter(server => server.group_id == this.selectedGroupId);
        },
        
        // 필터된 리소스 목록
        filteredResources() {
            if (!this.selectedGroupIdForMonitoring) return this.latestResources;
            const groupProxyIds = this.servers
                .filter(s => s.group_id == this.selectedGroupIdForMonitoring)
                .map(s => s.id);
            return this.latestResources.filter(r => groupProxyIds.includes(r.proxy_id));
        }
    },
    
    methods: {
        // 초기화
        async init() {
            await Promise.all([
                this.loadGroups(),
                this.loadServers(),
                this.loadMonitoringStatus(),
                this.loadLatestResources(),
                this.loadThresholds()
            ]);
            
            this.initSocket();
        },
        
        // Socket.IO 초기화
        initSocket() {
            this.socket = io();
            
            this.socket.on('resource_update', (data) => {
                // 실시간 리소스 업데이트
                const index = this.latestResources.findIndex(r => r.proxy_id === data.proxy_id);
                if (index >= 0) {
                    this.latestResources[index] = {
                        ...this.latestResources[index],
                        ...data.data,
                        proxy_name: data.proxy_name,
                        timestamp: data.timestamp
                    };
                } else {
                    this.latestResources.push({
                        proxy_id: data.proxy_id,
                        proxy_name: data.proxy_name,
                        timestamp: data.timestamp,
                        ...data.data
                    });
                }
            });
        },
        
        // API 호출 헬퍼
        async apiCall(url, options = {}) {
            try {
                const response = await fetch(url, {
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || `HTTP ${response.status}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error('API 호출 오류:', error);
                alert(`오류: ${error.message}`);
                throw error;
            }
        },
        
        // 데이터 로딩
        async loadGroups() {
            this.groups = await this.apiCall('/api/groups');
        },
        
        async loadServers() {
            this.servers = await this.apiCall('/api/servers');
        },
        
        async loadMonitoringStatus() {
            this.monitoringStatus = await this.apiCall('/api/monitoring/status');
            this.monitoringInterval = this.monitoringStatus.interval;
        },
        
        async loadLatestResources() {
            this.latestResources = await this.apiCall('/api/monitoring/resources/latest');
        },
        
        async loadThresholds() {
            this.thresholds = await this.apiCall('/api/monitoring/thresholds');
        },
        
        // 그룹 관리
        async saveGroup() {
            try {
                if (this.editingGroup) {
                    await this.apiCall(`/api/groups/${this.editingGroup.id}`, {
                        method: 'PUT',
                        body: JSON.stringify(this.groupForm)
                    });
                } else {
                    await this.apiCall('/api/groups', {
                        method: 'POST',
                        body: JSON.stringify(this.groupForm)
                    });
                }
                
                this.closeGroupModal();
                await this.loadGroups();
            } catch (error) {
                // 에러는 apiCall에서 처리됨
            }
        },
        
        editGroup(group) {
            this.editingGroup = group;
            this.groupForm = {
                name: group.name,
                description: group.description || ''
            };
            this.showGroupModal = true;
        },
        
        async deleteGroup(groupId) {
            if (!confirm('정말로 이 그룹을 삭제하시겠습니까?')) return;
            
            try {
                await this.apiCall(`/api/groups/${groupId}`, {
                    method: 'DELETE'
                });
                await this.loadGroups();
            } catch (error) {
                // 에러는 apiCall에서 처리됨
            }
        },
        
        closeGroupModal() {
            this.showGroupModal = false;
            this.editingGroup = null;
            this.groupForm = {
                name: '',
                description: ''
            };
        },
        
        // 서버 관리
        async saveServer() {
            try {
                if (this.editingServer) {
                    await this.apiCall(`/api/servers/${this.editingServer.id}`, {
                        method: 'PUT',
                        body: JSON.stringify(this.serverForm)
                    });
                } else {
                    await this.apiCall('/api/servers', {
                        method: 'POST',
                        body: JSON.stringify(this.serverForm)
                    });
                }
                
                this.closeServerModal();
                await this.loadServers();
            } catch (error) {
                // 에러는 apiCall에서 처리됨
            }
        },
        
        editServer(server) {
            this.editingServer = server;
            this.serverForm = {
                name: server.name,
                host: server.host,
                group_id: server.group_id,
                username: server.username,
                password: '123456', // 보안상 실제 비밀번호는 표시하지 않음
                ssh_port: server.ssh_port,
                snmp_port: server.snmp_port,
                is_main: server.is_main,
                is_active: server.is_active,
                description: server.description || ''
            };
            this.showServerModal = true;
        },
        
        async deleteServer(serverId) {
            if (!confirm('정말로 이 서버를 삭제하시겠습니까?')) return;
            
            try {
                await this.apiCall(`/api/servers/${serverId}`, {
                    method: 'DELETE'
                });
                await this.loadServers();
            } catch (error) {
                // 에러는 apiCall에서 처리됨
            }
        },
        
        async testConnection(serverId) {
            try {
                const result = await this.apiCall(`/api/servers/${serverId}/test`, {
                    method: 'POST'
                });
                alert(result.message);
            } catch (error) {
                // 에러는 apiCall에서 처리됨
            }
        },
        
        closeServerModal() {
            this.showServerModal = false;
            this.editingServer = null;
            this.serverForm = {
                name: '',
                host: '',
                group_id: '',
                username: 'root',
                password: '123456',
                ssh_port: 22,
                snmp_port: 161,
                is_main: false,
                is_active: true,
                description: ''
            };
        },
        
        // 모니터링 관리
        async toggleMonitoring() {
            try {
                if (this.monitoringStatus.active) {
                    await this.apiCall('/api/monitoring/stop', { method: 'POST' });
                } else {
                    await this.apiCall('/api/monitoring/start', { method: 'POST' });
                }
                await this.loadMonitoringStatus();
            } catch (error) {
                // 에러는 apiCall에서 처리됨
            }
        },
        
        async updateInterval() {
            try {
                await this.apiCall('/api/monitoring/interval', {
                    method: 'PUT',
                    body: JSON.stringify({ interval: this.monitoringInterval })
                });
                await this.loadMonitoringStatus();
            } catch (error) {
                // 에러는 apiCall에서 처리됨
            }
        },
        
        // 세션 관리
        async searchSessions() {
            try {
                const params = new URLSearchParams();
                if (this.selectedProxyIdForSessions) {
                    params.append('proxy_id', this.selectedProxyIdForSessions);
                }
                if (this.sessionSearch) {
                    params.append('search', this.sessionSearch);
                }
                
                this.sessions = await this.apiCall(`/api/monitoring/sessions?${params}`);
            } catch (error) {
                // 에러는 apiCall에서 처리됨
            }
        },
        
        async loadSessionStats() {
            try {
                this.sessionStats = await this.apiCall('/api/monitoring/sessions/stats');
                this.showSessionStats = true;
            } catch (error) {
                // 에러는 apiCall에서 처리됨
            }
        },
        
        // 유틸리티 함수
        formatDateTime(dateStr) {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return date.toLocaleString('ko-KR');
        },
        
        formatDate(dateStr) {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return date.toLocaleDateString('ko-KR');
        },
        
        formatBytes(bytes) {
            if (!bytes) return '0 B';
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        },
        
        getStatusClass(status) {
            switch (status) {
                case 'online': return 'bg-success';
                case 'offline': return 'bg-danger';
                case 'warning': return 'bg-warning';
                default: return 'bg-secondary';
            }
        },
        
        getProgressClass(value, threshold) {
            if (value >= threshold) return 'bg-danger';
            if (value >= threshold * 0.8) return 'bg-warning';
            return 'bg-success';
        },
        
        hasAlert(stat) {
            return stat.cpu_usage >= this.thresholds.cpu ||
                   stat.memory_usage >= this.thresholds.memory ||
                   stat.disk_usage >= this.thresholds.disk;
        }
    },
    
    watch: {
        // 탭 변경 시 데이터 새로고침
        currentTab(newTab) {
            switch (newTab) {
                case 'dashboard':
                    this.loadLatestResources();
                    break;
                case 'proxy':
                    this.loadGroups();
                    this.loadServers();
                    break;
                case 'monitoring':
                    this.loadLatestResources();
                    break;
                case 'sessions':
                    this.searchSessions();
                    break;
            }
        },
        
        // 세션 통계 모달 열릴 때 데이터 로드
        showSessionStats(show) {
            if (show) {
                this.loadSessionStats();
            }
        }
    },
    
    mounted() {
        this.init();
        
        // 주기적으로 데이터 갱신
        setInterval(() => {
            if (this.currentTab === 'dashboard' || this.currentTab === 'monitoring') {
                this.loadLatestResources();
            }
        }, 30000); // 30초마다
    }
}).mount('#app');