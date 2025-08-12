"""프록시 모니터링 시스템 메인 애플리케이션"""

from flask import Flask, send_from_directory, render_template, jsonify
import os

def create_app():
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)
    
    # 설정
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ppat.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 데이터베이스 초기화
    from models import db
    db.init_app(app)
    
    # 블루프린트 등록
    from api.proxy import proxy_bp
    from api.monitoring import monitoring_bp
    app.register_blueprint(proxy_bp, url_prefix='/api')
    app.register_blueprint(monitoring_bp, url_prefix='/api/monitoring')
    
    # 메인 라우트
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # 정적 파일 라우트 (CSS, JS 등)
    @app.route('/static/<path:filename>')
    def static_files(filename):
        return send_from_directory('static', filename)
    
    # 데이터베이스 테이블 생성
    with app.app_context():
        db.create_all()
        
        # 기본 그룹 생성
        from models import ProxyGroup, MonitoringConfig, ProxyServer, SessionRecord
        default_group = ProxyGroup.query.filter_by(name='기본그룹').first()
        if not default_group:
            default_group = ProxyGroup(
                name='기본그룹',
                description='기본 프록시 그룹'
            )
            db.session.add(default_group)
        
        # 기본 모니터링 설정 생성
        default_config = MonitoringConfig.query.filter_by(name='기본설정').first()
        if not default_config:
            default_config = MonitoringConfig(
                name='기본설정',
                description='기본 모니터링 설정',
                snmp_oids={
                    'CPU': '1.3.6.1.2.1.25.3.3.1.2.1',
                    'Memory': '1.3.6.1.2.1.25.2.2.1.1',
                    'CC': '1.3.6.1.2.1.25.4.2.1.2',
                    'CS': '1.3.6.1.2.1.25.4.2.1.3',
                    'HTTP': '1.3.6.1.2.1.25.4.2.1.2',
                    'HTTPS': '1.3.6.1.2.1.25.4.2.1.3',
                    'FTP': '1.3.6.1.2.1.25.4.2.1.4'
                },
                session_cmd="echo 'sample session data'",  # 테스트용 명령어
                cpu_threshold=80,
                memory_threshold=80,
                default_interval=30,
                is_active=True
            )
            db.session.add(default_config)
        
        db.session.commit()

        # 경량 스키마 마이그레이션: url_host 컬럼 추가 및 백필
        try:
            insp = db.inspect(db.engine)
            cols = [c['name'] for c in insp.get_columns('session_records')]
            if 'url_host' not in cols:
                db.session.execute(db.text('ALTER TABLE session_records ADD COLUMN url_host VARCHAR(255)'))
                db.session.commit()
            # 백필: policy -> url, 그리고 url_host 파생
            from urllib.parse import urlparse
            records = SessionRecord.query.all()
            changed = 0
            for r in records:
                src_url = r.url or r.policy
                host = None
                if src_url:
                    try:
                        parsed = urlparse(src_url if '://' in src_url else f'//{src_url}', allow_fragments=True)
                        host = parsed.hostname
                    except Exception:
                        host = None
                updated = False
                if (not r.url) and r.policy:
                    r.url = r.policy
                    updated = True
                if (not r.url_host) and (host):
                    r.url_host = host
                    updated = True
                if updated:
                    changed += 1
            if changed:
                db.session.commit()
        except Exception as e:
            # 마이그레이션 오류는 무시하고 진행 (로그만 남김)
            print(f"[WARN] schema migration skipped or failed: {e}")

    # 테스트 데이터 생성 엔드포인트
    @app.route('/api/test/generate_data', methods=['POST'])
    def generate_test_data():
        try:
            # 기존 데이터 삭제
            SessionRecord.query.delete()
            ProxyServer.query.delete()
            ProxyGroup.query.delete()
            db.session.commit()

            # 테스트 그룹 생성
            groups = [
                ProxyGroup(name='서울 센터', description='서울 지역 프록시 그룹'),
                ProxyGroup(name='부산 센터', description='부산 지역 프록시 그룹')
            ]
            for group in groups:
                db.session.add(group)
            db.session.commit()

            # 테스트 프록시 생성
            proxies = []
            for group in groups:
                # 메인 프록시
                main_proxy = ProxyServer(
                    name=f'{group.name} Main',
                    host='127.0.0.1',
                    ssh_port=22,
                    snmp_port=161,
                    username='test',
                    password='test123!@#',
                    description=f'{group.name} 메인 프록시',
                    is_active=True,
                    is_main=True,
                    group_id=group.id
                )
                proxies.append(main_proxy)

                # 서브 프록시들
                for i in range(2):
                    sub_proxy = ProxyServer(
                        name=f'{group.name} Sub {i+1}',
                        host='127.0.0.1',
                        ssh_port=22,
                        snmp_port=161,
                        username='test',
                        password='test123!@#',
                        description=f'{group.name} 서브 프록시 {i+1}',
                        is_active=True,
                        is_main=False,
                        group_id=group.id
                    )
                    proxies.append(sub_proxy)

            for proxy in proxies:
                db.session.add(proxy)
            db.session.commit()

            # 테스트 세션 데이터 생성
            from datetime import datetime, timedelta
            import random

            protocols = ['HTTP', 'HTTPS', 'FTP']
            categories = ['Allowed', 'Blocked', 'Pending']
            
            for proxy in proxies:
                for _ in range(50):  # 각 프록시당 50개의 세션
                    created_at = datetime.utcnow() - timedelta(
                        minutes=random.randint(0, 60)
                    )
                    session = SessionRecord(
                        proxy_id=proxy.id,
                        group_id=proxy.group_id,
                        client_ip=f'192.168.{random.randint(1, 255)}.{random.randint(1, 255)}',
                        server_ip=f'10.0.{random.randint(1, 255)}.{random.randint(1, 255)}',
                        protocol=random.choice(protocols),
                        user=f'user{random.randint(1, 100)}',
                        policy=f'policy_{random.randint(1, 10)}',
                        category=random.choice(categories),
                        cl_bytes_sent=random.randint(1000, 1000000),
                        cl_bytes_received=random.randint(1000, 1000000),
                        srv_bytes_sent=random.randint(1000, 1000000),
                        srv_bytes_received=random.randint(1000, 1000000),
                        age_seconds=random.randint(1, 3600),
                        created_at=created_at
                    )
                    db.session.add(session)

            db.session.commit()
            return jsonify({
                'success': True,
                'message': '테스트 데이터가 생성되었습니다.',
                'groups': len(groups),
                'proxies': len(proxies),
                'sessions': len(proxies) * 50
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    return app

if __name__ == '__main__':
    app = create_app()
    
    # 프록시 매니저 초기화 (앱 생성 후)
    with app.app_context():
        from backend import device_manager
        device_manager.reload()
    
    print(f"🚀 프록시 모니터링 시스템 시작")
    print(f"🌐 접속 주소: http://127.0.0.1:5007")
    app.run(debug=True, host='0.0.0.0', port=5007)
