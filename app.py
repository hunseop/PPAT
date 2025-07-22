"""프록시 모니터링 & 정책 관리 시스템 메인 애플리케이션"""

from flask import Flask, render_template
from flask_socketio import SocketIO
import os

socketio = SocketIO()

def create_app():
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)
    
    # 설정
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ppat.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # models.py에서 db 가져오기
    from models import db
    
    # 확장 초기화
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # 블루프린트 등록
    from api.proxy import proxy_bp
    from api.monitoring import monitoring_bp
    
    app.register_blueprint(proxy_bp, url_prefix='/api')
    app.register_blueprint(monitoring_bp, url_prefix='/api')
    
    # 메인 라우트
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    # 모델 임포트 (테이블 생성을 위해)
    from models import ProxyGroup, ProxyServer, ResourceStat, SessionInfo
    
    # 데이터베이스 테이블 생성
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)