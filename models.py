"""데이터베이스 모델 정의"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ProxyGroup(db.Model):
    """프록시 그룹 모델"""
    __tablename__ = 'proxy_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    proxies = db.relationship('ProxyServer', backref='group', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'proxy_count': len(self.proxies)
        }

class ProxyServer(db.Model):
    """프록시 서버 모델"""
    __tablename__ = 'proxy_servers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    ssh_port = db.Column(db.Integer, default=22)
    username = db.Column(db.String(100), default='root')
    password = db.Column(db.String(255), default='123456')  # 실제 환경에서는 암호화 필요
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 외래키
    group_id = db.Column(db.Integer, db.ForeignKey('proxy_groups.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'ssh_port': self.ssh_port,
            'username': self.username,
            'is_active': self.is_active,
            'description': self.description,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }