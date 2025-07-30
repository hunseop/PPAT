# 📊 monitoring_module vs proxy_module 비교

## 🎯 **핵심 차이점 요약**

| 구분 | monitoring_module | proxy_module |
|------|------------------|--------------|
| **목적** | 실시간 리소스 모니터링 | 프록시 서버 관리 및 제어 |
| **프로토콜** | SSH + SNMP | SSH만 사용 |
| **데이터** | CPU, 메모리, 세션, SNMP 메트릭 | 프록시 상태, 설정 정보 |
| **설정 관리** | 데이터베이스 기반 | 코드/파일 기반 |
| **사용 시점** | 자원사용률 페이지 | 프록시 연결 테스트, 관리 |

---

## 🔧 **proxy_module (프록시 관리)**

### 📋 **목적**
- 프록시 서버의 **기본 관리 기능**
- SSH 연결을 통한 **상태 확인**
- 프록시 서버 **연결 테스트**

### 🏗️ **구조**
```
proxy_module/
├── proxy_manager.py    # 프록시 매니저 (통합 관리)
├── proxy_client.py     # 개별 프록시 클라이언트
└── __init__.py
```

### 🔌 **주요 기능**
- **연결 테스트**: `test_connection()`
- **상태 조회**: `get_status()`
- **리소스 정보**: `get_resources()`
- **프록시 관리**: 추가/제거/업데이트

### 💻 **사용 예시**
```python
from proxy_module.proxy_client import ProxyClient

client = ProxyClient(host='192.168.1.10', port=22, username='root', password='123456')
if client.test_connection():
    status = client.get_status()
    resources = client.get_resources()
```

---

## 📊 **monitoring_module (리소스 모니터링)**

### 📋 **목적**
- **실시간 리소스 모니터링**
- **SNMP 기반 메트릭 수집**
- **세션 정보 분석**
- **임계값 기반 알림**

### 🏗️ **구조**
```
monitoring_module/
├── resource.py         # 리소스 모니터링 핵심
├── session.py          # 세션 관리
├── config.py           # 설정 관리 (사용 안함)
├── utils.py            # 유틸리티 함수
└── client/
    └── ssh.py          # SSH 클라이언트
```

### 🔌 **주요 기능**
- **SNMP 데이터 수집**: CPU, 메모리, 네트워크 메트릭
- **SSH 기반 정보**: 메모리 사용률, 세션 정보
- **데이터베이스 설정**: `MonitoringConfig`에서 OID, 임계값 조회
- **실시간 모니터링**: 주기적 데이터 수집

### 💻 **사용 예시**
```python
from monitoring_module import ResourceMonitor

monitor = ResourceMonitor(
    host='192.168.1.10',
    username='root',
    password='123456',
    snmp_port=161,
    snmp_community='public'
)

# 전체 리소스 데이터 수집
resource_data = monitor.get_resource_data()
# 결과: {'cpu': '45', 'memory': '67', 'uc': '12', ...}
```

---

## 🔍 **상세 비교**

### 1️⃣ **데이터 수집 방식**

#### **proxy_module**
- SSH 명령어만 사용
- 기본적인 시스템 정보
- 연결 상태 확인 중심

#### **monitoring_module**
- SSH + SNMP 병행
- 상세한 메트릭 수집
- 실시간 모니터링 중심

### 2️⃣ **설정 관리**

#### **proxy_module**
```python
# 하드코딩된 설정
client = ProxyClient(host, port, username, password)
```

#### **monitoring_module**
```python
# 데이터베이스 기반 설정
class MonitoringConfig(db.Model):
    snmp_oids = db.Column(db.JSON)  # OID 설정
    session_cmd = db.Column(db.Text)  # 세션 명령어
    cpu_threshold = db.Column(db.Integer)  # 임계값
```

### 3️⃣ **반환 데이터**

#### **proxy_module 결과**
```json
{
  "connection": true,
  "status": {
    "uptime": "5 days",
    "load": "0.45"
  },
  "resources": {
    "cpu": "basic info",
    "memory": "basic info"
  }
}
```

#### **monitoring_module 결과**
```json
{
  "date": "2025-07-30",
  "time": "06:55:02",
  "device": "192.168.1.10",
  "cpu": "45",
  "memory": "67", 
  "uc": "12",
  "cc": "156",
  "cs": "89",
  "http": "45",
  "https": "23",
  "ftp": "5"
}
```

---

## 🎯 **언제 어떤 모듈을 사용할까?**

### ✅ **proxy_module 사용 시기**
- 프록시 서버 **연결 테스트**
- 프록시 **기본 상태 확인**
- 프록시 **추가/제거/수정**
- **관리 탭**에서 사용

### ✅ **monitoring_module 사용 시기**
- **실시간 모니터링** 필요
- **상세한 메트릭** 수집
- **임계값 기반 알림**
- **자원사용률 탭**에서 사용

---

## 🧪 **CLI 테스트 도구 사용법**

### 🚀 **기본 사용법**
```bash
# 도움말
python test_monitoring.py --help

# proxy_module 테스트
python test_monitoring.py test-proxy --host 192.168.1.10

# monitoring_module 테스트  
python test_monitoring.py test-monitoring --host 192.168.1.10

# 두 모듈 비교
python test_monitoring.py compare --host 192.168.1.10

# 데이터베이스 설정 테스트
python test_monitoring.py test-db

# 대화형 모드
python test_monitoring.py interactive
```

### 🎮 **대화형 모드 예시**
```
🎮 === 대화형 테스트 모드 ===

선택하세요:
1. proxy_module 테스트
2. monitoring_module 테스트
3. 모듈 비교 테스트
4. 데이터베이스 설정 테스트
5. 종료

선택 (1-5): 3
호스트 IP (기본값: 127.0.0.1): 192.168.1.10
SSH 사용자명 (기본값: root): 
SSH 비밀번호 (기본값: 123456): 
SSH 포트 (기본값: 22): 
SNMP 포트 (기본값: 161): 
SNMP 커뮤니티 (기본값: public): 
```

---

## 🔧 **테스트 시나리오**

### 1️⃣ **로컬 테스트** (연결 실패 예상)
```bash
python test_monitoring.py compare --host 127.0.0.1
```

### 2️⃣ **실제 서버 테스트**
```bash
python test_monitoring.py compare --host 192.168.1.100 --username admin --password yourpass
```

### 3️⃣ **SNMP 설정 테스트**
```bash
python test_monitoring.py test-monitoring --host 192.168.1.100 --snmp-community private
```

### 4️⃣ **데이터베이스 설정 확인**
```bash
python test_monitoring.py test-db
```

이 CLI 도구로 두 모듈이 어떻게 다르게 작동하는지 명확히 확인할 수 있습니다! 🎯