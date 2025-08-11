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
    snmp_version = db.Column(db.String(10), default='v2c')  # SNMP 버전
    snmp_community = db.Column(db.String(100), default='public')  # 커뮤니티 스트링
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
            'snmp_version': self.snmp_version,
            'snmp_community': self.snmp_community,
            'username': self.username,
            'description': self.description,
            'is_active': self.is_active,
            'is_main': self.is_main,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MonitoringConfig(db.Model):
    """모니터링 설정 모델"""
    __tablename__ = 'monitoring_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    
    # SNMP 설정
    snmp_oids = db.Column(db.JSON)  # JSON 형태로 OID 저장
    
    # 세션 명령어
    session_cmd = db.Column(db.Text)
    
    # 임계값 설정
    cpu_threshold = db.Column(db.Integer, default=80)
    memory_threshold = db.Column(db.Integer, default=80)
    
    # 모니터링 주기 설정
    default_interval = db.Column(db.Integer, default=30)  # 초
    
    # 활성화 여부
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'snmp_oids': self.snmp_oids,
            'session_cmd': self.session_cmd,
            'cpu_threshold': self.cpu_threshold,
            'memory_threshold': self.memory_threshold,
            'default_interval': self.default_interval,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SessionRecord(db.Model):
    """세션 임시 저장 레코드"""
    __tablename__ = 'session_records'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('proxy_groups.id'), nullable=True)
    proxy_id = db.Column(db.Integer, db.ForeignKey('proxy_servers.id'), nullable=True)

    # 표준화된 주요 필드 (검색 대상)
    client_ip = db.Column(db.String(128), index=True)
    server_ip = db.Column(db.String(128), index=True)
    protocol = db.Column(db.String(32), index=True)
    user = db.Column(db.String(128), index=True)
    policy = db.Column(db.Text)  # URL 맵핑
    category = db.Column(db.String(256))  # Status 맵핑

    # 파싱된 전체 컬럼 (가능한 한 모두 보존)
    transaction = db.Column(db.String(64))
    creation_time = db.Column(db.DateTime)
    cust_id = db.Column(db.String(128))
    user_name = db.Column(db.String(128))
    client_side_mwg_ip = db.Column(db.String(128))
    server_side_mwg_ip = db.Column(db.String(128))
    cl_bytes_received = db.Column(db.BigInteger)
    cl_bytes_sent = db.Column(db.BigInteger)
    srv_bytes_received = db.Column(db.BigInteger)
    srv_bytes_sent = db.Column(db.BigInteger)
    trxn_index = db.Column(db.Integer)
    age_seconds = db.Column(db.Integer)
    in_use = db.Column(db.String(32))  # MWG는 Y/N 등 문자열일 수 있음
    url = db.Column(db.Text)

    extra = db.Column(db.JSON)  # 원본 컬럼 전체를 JSON으로 보관

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'proxy_id': self.proxy_id,
            'client_ip': self.client_ip,
            'server_ip': self.server_ip,
            'protocol': self.protocol,
            'user': self.user,
            'policy': self.policy,
            'category': self.category,
            'transaction': self.transaction,
            'creation_time': self.creation_time.isoformat() if self.creation_time else None,
            'cust_id': self.cust_id,
            'user_name': self.user_name,
            'client_side_mwg_ip': self.client_side_mwg_ip,
            'server_side_mwg_ip': self.server_side_mwg_ip,
            'cl_bytes_received': self.cl_bytes_received,
            'cl_bytes_sent': self.cl_bytes_sent,
            'srv_bytes_received': self.srv_bytes_received,
            'srv_bytes_sent': self.srv_bytes_sent,
            'trxn_index': self.trxn_index,
            'age_seconds': self.age_seconds,
            'in_use': self.in_use,
            'url': self.url,
            'extra': self.extra,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }