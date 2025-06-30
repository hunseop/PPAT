# 프로젝트 구조 설계

새로운 Flask 애플리케이션은 `app/` 디렉터리에 모듈별 블루프린트 구조로 나눈다.

## 기본 구조
```
app/
├── __init__.py
├── models/            # SQLAlchemy 모델 정의
├── proxy/             # 프록시 클러스터 관리 블루프린트
├── monitoring/        # 모니터링 관련 블루프린트
└── extensions.py      # 확장 모듈 초기화
```

## 초기 설정 작업
1. `Flask`와 `Flask-SocketIO` 초기화 코드를 `__init__.py`에서 수행.
2. 데이터베이스 세션 및 마이그레이션 도구 설정.
3. 설정 파일(`config.py` 혹은 `config.yaml`)을 읽어 환경별 옵션을 관리.
4. `create_app()` 팩토리 함수 작성 후 애플리케이션 실행 스크립트를 별도 파일로 분리.
