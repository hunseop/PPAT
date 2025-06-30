from flask import Flask
import os
from .extensions import db, socketio


def create_app(config_object=None):
    app = Flask(__name__)
    # 기본 설정
    app.config.setdefault('SECRET_KEY', 'secret')
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///instance/ppat.db')
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    if config_object:
        app.config.from_object(config_object)

    # 인스턴스 디렉터리 생성
    instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)

    db.init_app(app)
    socketio.init_app(app)

    from .proxy import bp as proxy_bp
    from .monitoring import bp as monitoring_bp
    app.register_blueprint(proxy_bp, url_prefix='/api/proxy')
    app.register_blueprint(monitoring_bp, url_prefix='/api/monitoring')

    return app
