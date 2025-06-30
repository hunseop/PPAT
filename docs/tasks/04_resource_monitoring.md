# 리소스 모니터링 기능

모든 프록시 장비의 CPU, 메모리 등 자원 정보를 주기적으로 수집한다.

## 저장 정책
- 수집 데이터는 최대 100MB까지 저장한다. 초과 시 오래된 항목부터 순차 삭제한다.
- 데이터 보존 기간은 별도로 제한하지 않는다.

## 기능 요구사항
1. `ResourceMonitor` 클래스를 활용해 각 프록시의 자원을 조회.
2. 백그라운드 스케줄러로 주기 실행. 주기는 API를 통해 변경 가능.
3. 시작/중지 API
   - `POST /api/monitoring/start`
   - `POST /api/monitoring/stop`
4. 주기 설정 API
   - `POST /api/monitoring/interval`
5. 조회 API
   - `GET /api/monitoring/resources?group=<id>&proxy=<id>`
6. 수집된 데이터는 `ResourceStat` 테이블에 저장하고 WebSocket을 통해 실시간 전송한다.

프론트엔드 리소스 탭에서는 테이블과 그래프를 제공하여 많은 장비도 한눈에 볼 수 있도록 한다.
