"""프록시 서버 관리 데이터베이스 모델"""

from .database import db
from datetime import datetime

class ProxyGroup(db.Model):
    """프록시 서버 그룹"""
    __tablename__ = "proxy_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(500))
    
    # 관계 설정
    proxies = db.relationship("ProxyServer", back_populates="group")

class ProxyServer(db.Model):
    """프록시 서버"""
    __tablename__ = "proxy_servers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    ip_address = db.Column(db.String(100))
    port = db.Column(db.Integer)
    description = db.Column(db.String(500))
    is_main = db.Column(db.Boolean, default=False)  # Main Appliance 여부
    enabled = db.Column(db.Boolean, default=True)
    group_id = db.Column(db.Integer, db.ForeignKey("proxy_groups.id"))
    
    # SSH 접속 정보
    ssh_username = db.Column(db.String(100))
    ssh_password = db.Column(db.String(100))  # 실제 구현시 암호화 필요
    ssh_port = db.Column(db.Integer, default=22)
    
    # SNMP 정보
    snmp_version = db.Column(db.String(10))
    snmp_community = db.Column(db.String(100))
    snmp_port = db.Column(db.Integer, default=161)
    
    # 메타데이터
    proxy_metadata = db.Column(db.JSON)
    
    # 관계 설정
    group = db.relationship("ProxyGroup", back_populates="proxies")

    # 업데이트 관련 필드 추가
    last_update = db.Column(db.DateTime, default=None)
    update_status = db.Column(db.String(20), default='pending')  # pending, updating, success, error

    def __repr__(self):
        return f'<ProxyServer {self.name}>'


class ResourceStat(db.Model):
    """프록시 리소스 수집 데이터"""
    __tablename__ = 'resource_stats'

    id = db.Column(db.Integer, primary_key=True)
    proxy_id = db.Column(db.Integer, db.ForeignKey('proxy_servers.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    cpu = db.Column(db.Float)
    memory = db.Column(db.Float)
    unique_clients = db.Column(db.Integer)
    cc = db.Column(db.Integer)
    cs = db.Column(db.Integer)
    http = db.Column(db.Integer)
    https = db.Column(db.Integer)
    ftp = db.Column(db.Integer)

    proxy = db.relationship('ProxyServer')


class SessionInfo(db.Model):
    """세션 모니터링 데이터"""
    __tablename__ = 'session_info'

    id = db.Column(db.Integer, primary_key=True)
    proxy_id = db.Column(db.Integer, db.ForeignKey('proxy_servers.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.JSON)

    proxy = db.relationship('ProxyServer')
