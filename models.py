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
            'proxy_count': len(self.proxies),
            'main_proxy_count': len([p for p in self.proxies if p.is_main])
        }

class ProxyServer(db.Model):
    """프록시 서버 모델"""
    __tablename__ = 'proxy_servers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    ssh_port = db.Column(db.Integer, default=22)
    snmp_port = db.Column(db.Integer, default=161)
    username = db.Column(db.String(100), default='root')
    password = db.Column(db.String(255), default='123456')  # 실제 환경에서는 암호화 필요
    is_main = db.Column(db.Boolean, default=False)
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
            'snmp_port': self.snmp_port,
            'username': self.username,
            'is_main': self.is_main,
            'is_active': self.is_active,
            'description': self.description,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ResourceStat(db.Model):
    """리소스 통계 모델"""
    __tablename__ = 'resource_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    proxy_id = db.Column(db.Integer, db.ForeignKey('proxy_servers.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    cpu_usage = db.Column(db.Float)
    memory_usage = db.Column(db.Float)
    disk_usage = db.Column(db.Float)
    network_in = db.Column(db.Float)
    network_out = db.Column(db.Float)
    session_count = db.Column(db.Integer)
    status = db.Column(db.String(20), default='online')  # online, offline, error
    
    # 관계
    proxy = db.relationship('ProxyServer', backref='resource_stats')
    
    def to_dict(self):
        return {
            'id': self.id,
            'proxy_id': self.proxy_id,
            'proxy_name': self.proxy.name if self.proxy else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'network_in': self.network_in,
            'network_out': self.network_out,
            'session_count': self.session_count,
            'status': self.status
        }

class SessionInfo(db.Model):
    """세션 정보 모델"""
    __tablename__ = 'session_info'
    
    id = db.Column(db.Integer, primary_key=True)
    proxy_id = db.Column(db.Integer, db.ForeignKey('proxy_servers.id'), nullable=False)
    client_ip = db.Column(db.String(45))  # IPv6 지원
    username = db.Column(db.String(255))
    url = db.Column(db.Text)
    protocol = db.Column(db.String(10))
    status = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 관계
    proxy = db.relationship('ProxyServer', backref='sessions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'proxy_id': self.proxy_id,
            'proxy_name': self.proxy.name if self.proxy else None,
            'client_ip': self.client_ip,
            'username': self.username,
            'url': self.url,
            'protocol': self.protocol,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }