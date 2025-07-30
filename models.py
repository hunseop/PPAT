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
    
    # 관계 설정
    servers = db.relationship('ProxyServer', backref='group', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        # 메인 서버 찾기
        main_server = None
        for server in self.servers:
            if server.is_main:
                main_server = server.name
                break
        
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'proxy_count': len(self.servers),
            'main_server': main_server,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ProxyServer(db.Model):
    """프록시 서버 모델"""
    __tablename__ = 'proxy_servers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    host = db.Column(db.String(45), nullable=False)  # IPv4/IPv6 지원
    ssh_port = db.Column(db.Integer, default=22)
    snmp_port = db.Column(db.Integer, default=161)
    username = db.Column(db.String(50), default='root')
    password = db.Column(db.String(255))  # 암호화 저장 권장
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=False)
    is_main = db.Column(db.Boolean, default=False)  # 메인 클러스터 여부
    group_id = db.Column(db.Integer, db.ForeignKey('proxy_groups.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'ssh_port': self.ssh_port,
            'snmp_port': self.snmp_port,
            'username': self.username,
            'description': self.description,
            'is_active': self.is_active,
            'is_main': self.is_main,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }