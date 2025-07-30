const { createApp } = Vue;

createApp({
    data() {
        return {
            proxies: [],
            showModal: false,
            editing: false,
            saving: false,
            testing: null,
            form: {
                id: null,
                name: '',
                host: '',
                ssh_port: 22,
                username: 'root',
                password: '',
                description: '',
                is_active: true
            }
        }
    },
    computed: {
        totalProxies() {
            return this.proxies.length;
        },
        onlineProxies() {
            return this.proxies.filter(p => p.is_active).length;
        },
        offlineProxies() {
            return this.proxies.filter(p => !p.is_active).length;
        }
    },
    async mounted() {
        await this.loadProxies();
    },
    methods: {
        async loadProxies() {
            try {
                const response = await fetch('/api/proxies');
                if (response.ok) {
                    this.proxies = await response.json();
                } else {
                    console.error('프록시 목록을 불러오는데 실패했습니다.');
                }
            } catch (error) {
                console.error('프록시 목록 로딩 오류:', error);
            }
        },

        async saveProxy() {
            if (!this.form.name || !this.form.host) {
                alert('이름과 IP 주소는 필수 항목입니다.');
                return;
            }

            this.saving = true;
            try {
                const method = this.editing ? 'PUT' : 'POST';
                const url = this.editing ? `/api/proxies/${this.form.id}` : '/api/proxies';
                
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: this.form.name,
                        host: this.form.host,
                        ssh_port: parseInt(this.form.ssh_port) || 22,
                        username: this.form.username || 'root',
                        password: this.form.password || '123456',
                        description: this.form.description,
                        is_active: this.form.is_active,
                        group_id: 1  // 기본 그룹 ID
                    })
                });

                if (response.ok) {
                    await this.loadProxies();
                    this.closeModal();
                    this.showNotification(this.editing ? '프록시가 수정되었습니다.' : '프록시가 추가되었습니다.', 'success');
                } else {
                    const error = await response.json();
                    alert('저장 실패: ' + (error.message || '알 수 없는 오류'));
                }
            } catch (error) {
                console.error('저장 오류:', error);
                alert('저장 중 오류가 발생했습니다.');
            } finally {
                this.saving = false;
            }
        },

        async deleteProxy(id) {
            if (!confirm('정말로 이 프록시를 삭제하시겠습니까?')) {
                return;
            }

            try {
                const response = await fetch(`/api/proxies/${id}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    await this.loadProxies();
                    this.showNotification('프록시가 삭제되었습니다.', 'success');
                } else {
                    alert('삭제에 실패했습니다.');
                }
            } catch (error) {
                console.error('삭제 오류:', error);
                alert('삭제 중 오류가 발생했습니다.');
            }
        },

        async testConnection(id) {
            this.testing = id;
            try {
                const response = await fetch(`/api/proxies/${id}/test`, {
                    method: 'POST'
                });

                const result = await response.json();
                if (result.success) {
                    this.showNotification('연결 테스트 성공!', 'success');
                    // 상태 업데이트
                    const proxy = this.proxies.find(p => p.id === id);
                    if (proxy) {
                        proxy.is_active = true;
                    }
                } else {
                    this.showNotification('연결 테스트 실패: ' + result.message, 'danger');
                    // 상태 업데이트
                    const proxy = this.proxies.find(p => p.id === id);
                    if (proxy) {
                        proxy.is_active = false;
                    }
                }
            } catch (error) {
                console.error('연결 테스트 오류:', error);
                this.showNotification('연결 테스트 중 오류가 발생했습니다.', 'danger');
            } finally {
                this.testing = null;
            }
        },

        editProxy(proxy) {
            this.editing = true;
            this.form = {
                id: proxy.id,
                name: proxy.name,
                host: proxy.host,
                ssh_port: proxy.ssh_port,
                username: proxy.username,
                password: '', // 보안상 비밀번호는 비워둠
                description: proxy.description || '',
                is_active: proxy.is_active
            };
            this.showModal = true;
        },

        closeModal() {
            this.showModal = false;
            this.editing = false;
            this.form = {
                id: null,
                name: '',
                host: '',
                ssh_port: 22,
                username: 'root',
                password: '',
                description: '',
                is_active: true
            };
        },

        formatDate(dateString) {
            if (!dateString) return '-';
            const date = new Date(dateString);
            return date.toLocaleString('ko-KR');
        },

        showNotification(message, type = 'info') {
            // 간단한 알림 표시 (실제로는 toast 라이브러리를 사용하는 것이 좋음)
            const alertClass = type === 'success' ? 'alert-success' : 
                              type === 'danger' ? 'alert-danger' : 'alert-info';
            
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
            alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
            `;
            
            document.body.appendChild(alertDiv);
            
            setTimeout(() => {
                if (alertDiv.parentElement) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }
}).mount('#app');