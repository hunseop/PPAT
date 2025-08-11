# 프록시 모니터링 시스템

미니멀하고 직관적인 프록시 서버 관리 시스템입니다.

## 주요 기능

### 📋 관리 페이지 (현재 구현)
- **프록시 서버 등록**: 새로운 프록시 서버를 쉽게 추가
- **서버 관리**: 등록된 프록시 서버 정보 수정 및 삭제
- **연결 테스트**: SSH 연결을 통한 서버 상태 확인
- **실시간 상태**: 온라인/오프라인 상태 표시

### 🚧 개발 예정
- **자원사용률**: CPU, 메모리, 디스크 모니터링
- **세션브라우저**: 실시간 세션 모니터링
- **정책조회**: 프록시 정책 관리

## 설치 및 실행

### 1. 필요한 패키지 설치
```bash
pip install --break-system-packages -r requirements.txt
```

### 2. 애플리케이션 실행
```bash
python app.py
```

### 3. 웹 브라우저에서 접속
```
http://localhost:5007
```

## 사용법

### 프록시 서버 관리
1. 메인 페이지에서 "프록시 추가" 버튼 클릭
2. 필수 정보 입력:
   - **이름**: 프록시 서버 식별명
   - **IP 주소**: 프록시 서버의 IP 주소
   - **SSH 포트**: SSH 접속 포트 (기본값: 22)
   - **사용자명**: SSH 접속 사용자명 (기본값: root)
   - **비밀번호**: SSH 접속 비밀번호
   - **설명**: 서버에 대한 간단한 설명
3. "저장" 버튼 클릭

### 연결 테스트
- 서버 목록에서 플러그 아이콘 클릭
- SSH 포트로의 TCP 연결을 테스트
- 결과에 따라 서버 상태가 자동으로 업데이트

### 서버 수정/삭제
- **수정**: 목록에서 편집 아이콘 클릭
- **삭제**: 목록에서 삭제 아이콘 클릭 (확인 메시지 후 삭제)

## 기술 스택

- **백엔드**: Flask + SQLAlchemy + Paramiko
- **프론트엔드**: 순수 JavaScript + Bootstrap 5
- **데이터베이스**: SQLite
- **SSH 연결**: Paramiko (실제 SSH 인증 지원)
- **포트**: 5007

## 프로젝트 구조

```
.
├── app.py                      # 메인 애플리케이션
├── models.py                   # 데이터베이스 모델
├── requirements.txt            # 필요한 패키지
├── backend/                    # 단일 백엔드 모듈
│   ├── __init__.py             # ProxyClient, ProxyMonitor, managers, services 재노출
│   ├── proxy_client.py         # SSH 연결 클라이언트
│   ├── proxy_manager.py        # 프록시 통합 관리자
│   ├── monitoring.py           # 모니터링 로직
│   ├── utils.py                # 공용 유틸리티
│   └── services.py             # device_manager, monitoring_service
├── api/
│   ├── proxy.py                # 프록시 관리 API
│   └── monitoring.py           # 모니터링 API
└── static/
    ├── index.html             # 메인 페이지
    └── js/
        └── app.js             # JavaScript 애플리케이션
```

## API 엔드포인트

### 기본 CRUD
- `GET /api/proxies` - 프록시 서버 목록 조회
- `POST /api/proxies` - 프록시 서버 추가
- `PUT /api/proxies/<id>` - 프록시 서버 수정
- `DELETE /api/proxies/<id>` - 프록시 서버 삭제
- `POST /api/proxies/<id>/test` - 연결 테스트

### 고급 기능 (개발 완료)
- `GET /api/proxies/<id>/info` - 시스템 정보 조회
- `GET /api/proxies/<id>/resources` - 리소스 사용률 조회
- `GET /api/proxies/<id>/services` - 서비스 상태 확인
- `POST /api/proxies/<id>/command` - 원격 명령 실행

### 모니터링
- `POST /api/monitoring/start` - 자동 모니터링 시작
- `POST /api/monitoring/stop` - 자동 모니터링 중지
- `GET /api/monitoring/status` - 모니터링 상태 조회

## 현재 상태

✅ **완료된 기능**
- 미니멀한 관리 페이지 UI
- 프록시 서버 CRUD 기능
- 실제 SSH 연결 테스트
- 실시간 상태 모니터링
- 단일 `backend` 모듈로 구조 간소화

🚧 **개발 예정**
- 자원사용률 페이지
- 세션브라우저 페이지
- 정책조회 페이지

## 특징

- **미니멀 디자인**: 불필요한 요소 제거, 핵심 기능에 집중
- **실제 SSH 연결**: Paramiko를 통한 정확한 연결 상태 확인
- **단일 모듈 구조**: `backend` 하나로만 사용, 관리 간소화
- **확장 가능**: 추가 페이지를 위한 탭 구조 준비
