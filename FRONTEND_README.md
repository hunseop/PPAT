# 프록시 모니터링 & 정책 관리 시스템 (PPAT) - 프론트엔드

프록시 서버 그룹의 리소스 사용량을 모니터링하고 정책을 관리하는 웹 애플리케이션의 프론트엔드 구현입니다.

## 🚀 주요 기능

### ✅ 구현 완료
- **대시보드**: 시스템 전체 현황 및 최신 리소스 상태
- **프록시 관리**: 프록시 그룹 및 서버 CRUD 기능
- **실시간 모니터링**: WebSocket을 통한 실시간 리소스 모니터링
- **세션 관리**: 세션 검색 및 통계 기능

### 🔄 향후 구현 예정
- **정책 관리**: 정책 조회 및 관리 기능
- **고급 차트**: 시계열 차트 및 고급 시각화

## 🛠️ 기술 스택

### Backend
- **Flask**: 웹 프레임워크
- **SQLAlchemy**: ORM 및 데이터베이스 관리
- **Flask-SocketIO**: 실시간 통신
- **SQLite**: 데이터베이스

### Frontend
- **Vue.js 3**: 프론트엔드 프레임워크
- **Bootstrap 5**: UI 프레임워크
- **Font Awesome**: 아이콘
- **Socket.IO**: 실시간 통신

## 📁 프로젝트 구조

```
/workspace/
├── api/                    # API 엔드포인트
│   ├── proxy.py           # 프록시 관리 API
│   └── monitoring.py      # 모니터링 API
├── templates/             # HTML 템플릿
│   └── index.html        # 메인 페이지
├── static/               # 정적 파일
│   ├── css/style.css     # 스타일시트
│   └── js/app.js         # Vue.js 애플리케이션
├── monitoring_module/    # 모니터링 모듈 (기존)
├── policy_module/        # 정책 모듈 (기존)
├── app.py               # Flask 애플리케이션
├── models.py            # 데이터베이스 모델
├── init_data.py         # 샘플 데이터 생성
└── requirements.txt     # Python 패키지 의존성
```

## 🏃‍♂️ 실행 방법

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 샘플 데이터 생성
```bash
python init_data.py
```

### 3. 애플리케이션 실행
```bash
python app.py
```

### 4. 웹 브라우저에서 접속
```
http://localhost:5000
```

## 📊 주요 화면

### 대시보드
- 시스템 전체 현황 (총 프록시, 온라인 서버, 세션 수, 그룹 수)
- 최신 리소스 현황 테이블 (CPU, 메모리, 디스크 사용률)
- 실시간 업데이트

### 프록시 관리
- **프록시 그룹 관리**
  - 그룹 추가/수정/삭제
  - 그룹별 프록시 현황 표시
- **프록시 서버 관리**
  - 서버 추가/수정/삭제
  - Main/Cluster 구분
  - 연결 테스트 기능
  - 그룹별 필터링

### 모니터링
- **모니터링 제어**
  - 모니터링 시작/중지
  - 갱신 간격 설정
  - 그룹별 필터링
- **실시간 리소스 현황**
  - CPU, 메모리, 디스크 사용률
  - 네트워크 트래픽
  - 세션 수
  - 임계값 초과 시 경고 표시

### 세션 관리
- **세션 검색**: IP, 사용자명, URL 기반 검색
- **프록시별 필터링**
- **세션 통계**: IP/프록시/URL별 세션 현황

## 🔧 API 엔드포인트

### 프록시 관리
- `GET /api/groups` - 그룹 목록 조회
- `POST /api/groups` - 그룹 생성
- `PUT /api/groups/<id>` - 그룹 수정
- `DELETE /api/groups/<id>` - 그룹 삭제
- `GET /api/servers` - 서버 목록 조회
- `POST /api/servers` - 서버 생성
- `PUT /api/servers/<id>` - 서버 수정
- `DELETE /api/servers/<id>` - 서버 삭제
- `POST /api/servers/<id>/test` - 연결 테스트

### 모니터링
- `POST /api/monitoring/start` - 모니터링 시작
- `POST /api/monitoring/stop` - 모니터링 중지
- `GET /api/monitoring/status` - 모니터링 상태
- `PUT /api/monitoring/interval` - 갱신 간격 설정
- `GET /api/monitoring/resources` - 리소스 통계 조회
- `GET /api/monitoring/resources/latest` - 최신 리소스 현황
- `GET /api/monitoring/sessions` - 세션 정보 조회
- `GET /api/monitoring/sessions/stats` - 세션 통계
- `GET /api/monitoring/thresholds` - 임계값 조회
- `PUT /api/monitoring/thresholds` - 임계값 설정

## 🎨 UI/UX 특징

### 반응형 디자인
- Bootstrap 5 기반 모바일 친화적 디자인
- 테이블 가로 스크롤 지원

### 실시간 업데이트
- WebSocket 기반 실시간 데이터 갱신
- 모니터링 상태 표시
- 자동 새로고침 (30초 간격)

### 사용자 친화적 인터페이스
- 직관적인 탭 네비게이션
- 모달 기반 폼
- 진행률 바 및 상태 배지
- 임계값 초과 시 경고 표시

### 시각적 피드백
- Progress bar로 리소스 사용률 표시
- 색상 코딩 (정상/경고/위험)
- 상태 배지 및 아이콘

## 🔄 데이터 흐름

1. **프록시 서버 등록**: 웹 UI → API → 데이터베이스
2. **모니터링 시작**: 웹 UI → API → 백그라운드 스레드
3. **실시간 데이터**: 백그라운드 스레드 → WebSocket → 웹 UI
4. **데이터 저장**: 백그라운드 스레드 → 데이터베이스
5. **데이터 조회**: 웹 UI → API → 데이터베이스

## 🧪 테스트용 샘플 데이터

`init_data.py` 실행 시 생성되는 샘플 데이터:
- **3개 프록시 그룹**: Production, Development, Testing
- **6개 프록시 서버**: 각 그룹별 Main/Cluster 구성
- **360개 리소스 통계**: 최근 1시간 데이터
- **50개 세션 데이터**: 다양한 IP/사용자/URL

## 🚨 주의사항

1. **보안**: 현재 구현에서는 인증/인가가 없습니다.
2. **비밀번호**: 하드코딩된 기본 비밀번호 사용 중
3. **실제 모니터링**: 현재는 모의 데이터 생성, 실제 환경에서는 `monitoring_module` 연동 필요
4. **데이터 정리**: 리소스 통계 데이터가 계속 누적되므로 주기적 정리 필요

## 🔮 향후 개선 계획

1. **정책 관리 기능 추가**
2. **차트 라이브러리 도입** (Chart.js 등)
3. **사용자 인증 시스템**
4. **데이터 정리 스케줄러**
5. **모바일 앱 버전**
6. **다국어 지원**

## 🐛 문제 해결

### 일반적인 문제들

1. **포트 충돌**: 5000번 포트가 사용 중인 경우 `app.py`에서 포트 변경
2. **WebSocket 연결 실패**: 방화벽 또는 프록시 설정 확인
3. **데이터베이스 오류**: `ppat.db` 파일 삭제 후 재실행

### 로그 확인
Flask 애플리케이션 콘솔에서 오류 메시지를 확인할 수 있습니다.

---

이 프론트엔드는 문서의 요구사항에 따라 프록시 장비 관리와 모니터링 기능을 우선 구현했습니다. 정책 관리 기능은 향후 추가될 예정입니다.