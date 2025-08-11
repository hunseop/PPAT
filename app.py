"""프록시 모니터링 시스템 메인 애플리케이션"""

from flask import Flask, send_from_directory, render_template
import os

def create_app():
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)
    
    # 설정
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///proxy_monitoring.db')
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
        from models import ProxyGroup, MonitoringConfig
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
                session_cmd="/opt/mwg/bin/mwg-core -S connections | sed -E 's/\\s*\\|\\s*/ | /g'",
                cpu_threshold=80,
                memory_threshold=80,
                default_interval=30,
                is_active=True
            )
            db.session.add(default_config)
        
        db.session.commit()
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # 프록시 매니저 초기화 (앱 생성 후)
    with app.app_context():
        from unified import device_manager
        device_manager.reload()
    
    print(f"🚀 프록시 모니터링 시스템 시작")
    print(f"🌐 접속 주소: http://127.0.0.1:5007")
    app.run(debug=True, host='0.0.0.0', port=5007)