# 모니터링 모듈 vs 프록시 모듈 분리 가이드

## 🎯 **모듈 분리의 필요성**

`monitoring_module`과 `proxy_module`은 **반드시 분리되어야 합니다**. 각각 다른 목적과 책임을 가지고 있기 때문입니다.

## 📊 **모듈별 역할 비교**

| 구분 | proxy_module | monitoring_module |
|------|-------------|------------------|
| **주 목적** | 프록시 서버 연결 관리 | 실시간 리소스 모니터링 |
| **책임** | 연결/해제, 상태 관리 | 데이터 수집, 임계값 모니터링 |
| **데이터 수집** | 기본 연결 상태만 | CPU, Memory, SNMP, 세션 등 |
| **사용 시기** | 프록시 등록/설정 시 | 실시간 모니터링 시 |
| **의존성** | 최소한의 SSH | SSH + SNMP + 데이터베이스 |

## 🔧 **proxy_module (프록시 관리)**

### **목적**
- 프록시 서버 연결 관리
- 기본적인 연결 테스트
- 프록시 풀 관리

### **주요 클래스**
```python
# proxy_module/proxy_client.py
class ProxyClient:
    def __init__(self, host, port, username, password)
    def test_connection(self) -> bool
    def connect(self)
    def disconnect(self)

# proxy_module/proxy_manager.py  
class ProxyManager:
    def add_proxy(self, proxy_config)
    def remove_proxy(self, proxy_id)
    def get_active_proxies(self)
    def test_proxy_connection(self, proxy_id)
```

### **사용 예시**
```python
# 프록시 등록 시
from proxy_module import ProxyClient, ProxyManager

client = ProxyClient("192.168.1.10", 22, "admin", "pass")
if client.test_connection():
    proxy_manager.add_proxy(proxy_config)
```

## 📊 **monitoring_module (리소스 모니터링)**

### **목적**
- 실시간 시스템 리소스 모니터링
- SNMP 데이터 수집
- 세션 정보 분석
- 임계값 모니터링

### **주요 클래스**
```python
# monitoring_module/monitor.py
class ProxyMonitor:
    def __init__(self, host, username, password, snmp_port, snmp_community)
    def get_resource_data(self) -> Dict[str, Any]
    def get_memory_usage(self) -> int
    def get_session_info(self) -> Dict[str, Any]
    def get_snmp_data(self) -> Dict[str, int]
    def get_comprehensive_status(self) -> Dict[str, Any]
```

### **수집 데이터**
- **CPU**: SNMP 기반 CPU 사용률
- **Memory**: SSH 기반 메모리 사용률  
- **UC**: 고유 클라이언트 수
- **CC**: Connection Count
- **CS**: Connection Status
- **HTTP/HTTPS/FTP**: 프로토콜별 연결 수

### **사용 예시**
```python
# 실시간 모니터링 시
from monitoring_module import ProxyMonitor

monitor = ProxyMonitor("192.168.1.10", "admin", "pass", 161, "public")
resource_data = monitor.get_resource_data()
# {'cpu': '25', 'memory': '67', 'uc': '150', 'cc': '300', ...}
```

## 🔄 **모듈 간 협력**

### **API 레벨에서의 분리**
```python
# api/proxy.py - 프록시 관리
@proxy_bp.route('/proxies/<int:proxy_id>/test', methods=['POST'])
def test_proxy_connection(proxy_id):
    # proxy_module 사용
    from proxy_module import ProxyManager
    return proxy_manager.test_connection(proxy_id)

# api/monitoring.py - 리소스 모니터링  
@monitoring_bp.route('/resources', methods=['GET'])
def get_resources():
    # monitoring_module 사용
    from monitoring_module import ProxyMonitor
    monitor = ProxyMonitor(...)
    return monitor.get_resource_data()
```

## ⚡ **성능 및 확장성**

### **proxy_module**
- 빠른 연결 테스트에 최적화
- 최소한의 리소스 사용
- 연결 풀링 지원

### **monitoring_module**  
- 상세한 데이터 수집
- 데이터베이스 기반 설정
- 임계값 모니터링
- 백그라운드 수집 지원

## 🎯 **언제 어떤 모듈을 사용할까?**

### **proxy_module 사용 시기**
- ✅ 프록시 서버 등록/삭제
- ✅ 기본 연결 테스트
- ✅ 프록시 풀 관리
- ✅ 연결 상태 확인

### **monitoring_module 사용 시기**
- ✅ 실시간 자원사용률 모니터링
- ✅ 성능 데이터 수집
- ✅ 임계값 알림
- ✅ 통계 분석

## 🔧 **CLI 테스트**

```bash
# proxy_module 테스트
python3 test_monitoring.py test-proxy --host 192.168.1.10 --username admin --password pass

# monitoring_module 테스트  
python3 test_monitoring.py test-monitoring --host 192.168.1.10 --username admin --password pass

# 모듈 비교
python3 test_monitoring.py compare --host 192.168.1.10 --username admin --password pass
```

## 📋 **결론**

**proxy_module**과 **monitoring_module**은 서로 다른 책임을 가진 독립적인 모듈입니다:

- **proxy_module**: "연결 관리자" - 빠르고 가벼운 연결 관리
- **monitoring_module**: "데이터 수집가" - 상세하고 지속적인 모니터링

이런 분리를 통해 시스템의 유지보수성, 확장성, 성능을 모두 향상시킬 수 있습니다.