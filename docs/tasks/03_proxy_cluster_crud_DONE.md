# 프록시 클러스터 관리 기능

프록시는 그룹(Cluster) 단위로 관리한다. 각 그룹은 여러 프록시 장비를 포함하며 한 개의 메인 장비를 가진다.

## 데이터베이스
- `ProxyGroup` 테이블: 그룹 이름과 설명
- `ProxyServer` 테이블: 장비 세부 정보, 그룹 ID, 메인 여부, 모니터링 접속 정보

## API 설계
1. `GET /api/groups` : 그룹 목록 조회
2. `POST /api/groups` : 새 그룹 생성
3. `PUT /api/groups/<id>` : 그룹 수정
4. `DELETE /api/groups/<id>` : 그룹 삭제
5. `GET /api/servers` : 프록시 목록 조회 (필터: group, is_main)
6. `POST /api/servers` : 프록시 추가
7. `PUT /api/servers/<id>` : 프록시 수정
8. `DELETE /api/servers/<id>` : 프록시 삭제

프런트엔드에서는 Vue 기반의 테이블과 폼을 제공해 CRUD를 수행한다.
