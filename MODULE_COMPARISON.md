# 📦 단일 백엔드 모듈 안내 (기존 모듈 비교 포함)

현재 프로젝트는 `backend` 단일 모듈로 통합되어 운영됩니다. 과거에는 `monitoring_module`과 `proxy_module`로 나뉘어 있었으나, 유지보수성과 사용성 향상을 위해 하나로 합쳐졌습니다.

## ✅ 지금은 이렇게 사용하세요

```python
from backend import (
  ProxyClient,       # SSH 연결/명령/상태/리소스
  ProxyMonitor,      # 모니터링(SNMP/세션/메모리 등)
  proxy_manager,     # 프록시 일괄 관리
  device_manager,    # DB 기반 프록시 클라이언트 풀 관리
  monitoring_service # 모니터링 수집/검색 서비스
)
```

- API 레이어에서도 모두 `from backend import ...` 만 사용하면 됩니다.
- 내부적으로 필요한 유틸/서비스는 `backend` 내부에서 결합해 제공합니다.

---

## 🗃️ 통합 전 비교(참고용)

| 구분 | monitoring_module | proxy_module |
|------|------------------|--------------|
| 목적 | 실시간 리소스 모니터링 | 프록시 서버 관리 및 제어 |
| 프로토콜 | SSH + SNMP | SSH |
| 데이터 | CPU, 메모리, 세션, SNMP 메트릭 | 프록시 상태, 리소스 |
| 설정 관리 | 데이터베이스 기반 | 코드/파일 기반 |

이제 위 기능들은 `backend`에서 일괄 제공됩니다.

---

## 🧪 CLI 테스트 도구

```bash
# 도움말
python test_monitoring.py --help

# ProxyClient 테스트
python test_monitoring.py test-proxy --host 192.168.1.10

# ProxyMonitor 테스트
python test_monitoring.py test-monitoring --host 192.168.1.10

# 두 기능 비교
python test_monitoring.py compare --host 192.168.1.10

# 데이터베이스 설정 테스트
python test_monitoring.py test-db

# 대화형 모드
python test_monitoring.py interactive
```

> 기존 모듈명(`monitoring_module`, `proxy_module`) 표기는 더 이상 사용하지 않으며, 문서/코드에서 `backend`로 통일되었습니다.