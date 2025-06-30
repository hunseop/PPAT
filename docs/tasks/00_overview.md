# Flask 앱 재구축 개요

## 참조 문서
- 01_cleanup_old_app.md
- 02_project_structure.md
- 03_proxy_cluster_crud.md
- 04_resource_monitoring.md
- 05_session_monitoring.md
- 06_notes.md

## 목표
기존 `app.py` 중심 코드를 정리하고 블루프린트 구조로 다시 작성한다. 프록시 장비 관리와 모니터링 기능을 우선 개발하고 정책 조회는 나중에 구현한다.

## 작업 단계

1. **프로젝트 구조 정비**
   - 기존 `app.py` 대신 블루프린트 구조를 사용하는 새 Flask 애플리케이션 생성
   - `ppat_db` 모듈을 활용하여 데이터베이스 초기화 로직 정리
   - 설정 파일 분리 및 로딩 방식 정의

2. **프록시 클러스터 관리 기능**
   - 모델 점검 및 필요한 필드 추가 여부 검토 (`ProxyGroup`, `ProxyServer`)
   - API 엔드포인트 설계
     - `GET /api/groups` – 클러스터 목록 조회
     - `POST /api/groups` – 클러스터 생성
     - `PUT /api/groups/<id>` – 클러스터 수정
     - `DELETE /api/groups/<id>` – 클러스터 삭제
     - `GET /api/servers` – 모든 프록시 조회 (필터로 그룹/메인여부 지정 가능)
     - `POST /api/servers` – 프록시 등록
     - `PUT /api/servers/<id>` – 프록시 수정
     - `DELETE /api/servers/<id>` – 프록시 삭제
   - 클러스터별 프록시 조회 로직 구현
   - Vue 기반 프론트엔드에서 CRUD 화면 제공

3. **리소스 모니터링 기능**
   - `monitoring_module.resource.ResourceMonitor` 사용
   - 백그라운드 스케줄러(예: `APScheduler` 또는 단순 쓰레드)로 주기적 수집 구현
     - 모니터링 시작/종료 컨트롤 API 필요 (`/api/monitoring/start`, `/api/monitoring/stop`)
     - 수집 주기 설정 API (`/api/monitoring/interval`)
   - 수집 결과를 저장할 테이블 설계 (`ResourceStat`: timestamp, proxy_id, cpu, memory, ...)
   - 클러스터 전체/특정 프록시별 조회 API 제공 (`/api/monitoring/resources?group=<id>&proxy=<id>`) 
   - 프론트엔드 리소스 모니터 탭 구현: 테이블/그래프 형태로 가시성 높임

4. **세션 모니터링 기능**
   - `monitoring_module.session.SessionManager` 사용
   - 실시간 조회 API (`/api/sessions?proxy=<id>&search=<term>`)
   - 세션 데이터 저장 옵션(임시 DB) 및 상세 조회 API 제공
   - 프론트엔드 세션 모니터 탭 구현: 검색 폼과 결과 테이블 표시

5. **공통 사항**
   - Flask-SocketIO를 이용한 실시간 알림(선택 사항)
   - 대량 장비를 고려한 페이지네이션 및 필터 기능 검토
   - 정책 조회 기능은 기존 모델 활용해 추후 추가 예정

## 결정 사항
- 모니터링 데이터는 100MB까지 저장하고 기간 제한은 없다.
- 실시간 갱신은 WebSocket을 사용한다.
- 보안 관련 요구 사항은 고려하지 않는다.
