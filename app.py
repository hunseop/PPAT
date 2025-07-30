"""프록시 모니터링 시스템 메인 애플리케이션"""

from flask import Flask
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
    
    # API 블루프린트 등록
    from api.proxy import proxy_bp
    app.register_blueprint(proxy_bp, url_prefix='/api')
    
    # 메인 라우트
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    # 데이터베이스 테이블 생성
    with app.app_context():
        db.create_all()
        
        # 기본 그룹 생성
        from models import ProxyGroup
        if not ProxyGroup.query.filter_by(name='기본그룹').first():
            default_group = ProxyGroup(name='기본그룹', description='기본 프록시 그룹')
            db.session.add(default_group)
            db.session.commit()
    
    return app

if __name__ == '__main__':
    app = create_app()
    print(f"🚀 프록시 모니터링 시스템 시작")
    print(f"🌐 접속 주소: http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)