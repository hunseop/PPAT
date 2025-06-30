# 세션 모니터링 기능

프록시 세션 현황을 실시간으로 조회하고 검색할 수 있게 한다.

## 기능 요구사항
1. `SessionManager` 클래스로 세션 데이터를 수집하여 임시 DB에 저장한다.
2. 검색 API
   - `GET /api/sessions?proxy=<id>&search=<term>`
3. 상세 조회 API
   - `GET /api/sessions/<session_id>`
4. 세션 정보는 WebSocket으로 실시간 전송하며 페이지네이션을 지원한다.

보안 요건은 고려하지 않으므로 개인정보 마스킹 작업은 생략한다.
