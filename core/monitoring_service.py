from typing import Dict, Any, List
from flask import current_app
from models import ProxyServer, MonitoringConfig, SessionRecord, ProxyGroup, db
from monitoring_module import ProxyMonitor

class MonitoringService:
    def __init__(self):
        pass

    def get_active_config(self) -> MonitoringConfig | None:
        return MonitoringConfig.query.filter_by(is_active=True).first()

    def update_active_config(self, data: Dict[str, Any]) -> MonitoringConfig:
        config = self.get_active_config()
        if not config:
            raise ValueError('활성화된 모니터링 설정이 없습니다.')
        if 'snmp_oids' in data and isinstance(data['snmp_oids'], dict):
            config.snmp_oids = data['snmp_oids']
        if 'session_cmd' in data and isinstance(data['session_cmd'], str):
            config.session_cmd = data['session_cmd']
        if 'cpu_threshold' in data:
            config.cpu_threshold = int(data['cpu_threshold'])
        if 'memory_threshold' in data:
            config.memory_threshold = int(data['memory_threshold'])
        if 'default_interval' in data:
            config.default_interval = int(data['default_interval'])
        db.session.commit()
        return config

    def collect_resources(self, group_id: int | None = None) -> List[Dict[str, Any]]:
        query = ProxyServer.query.filter_by(is_active=True)
        if group_id:
            query = query.filter(ProxyServer.group_id == group_id)
        results = []
        for proxy in query.all():
            monitor = ProxyMonitor(
                host=proxy.host,
                username=proxy.username,
                password=proxy.password,
                ssh_port=proxy.ssh_port,
                snmp_port=proxy.snmp_port,
                snmp_community=proxy.snmp_community
            )
            data = monitor.get_resource_data()
            results.append({
                'proxy_id': proxy.id,
                'proxy_name': proxy.name,
                'host': proxy.host,
                'group_name': proxy.group.name if proxy.group else None,
                'is_main': proxy.is_main,
                'resource_data': data
            })
        return results

    def collect_sessions_by_group(self, group_id: int, persist: bool = True) -> int:
        if persist:
            SessionRecord.query.filter_by(group_id=group_id).delete()
            db.session.commit()
        proxies = ProxyServer.query.filter_by(group_id=group_id, is_active=True).all()
        saved = 0
        for proxy in proxies:
            monitor = ProxyMonitor(
                host=proxy.host,
                username=proxy.username,
                password=proxy.password,
                ssh_port=proxy.ssh_port,
                snmp_port=proxy.snmp_port,
                snmp_community=proxy.snmp_community
            )
            info = monitor.get_session_info()
            for s in info.get('sessions', []):
                rec = SessionRecord(
                    group_id=group_id,
                    proxy_id=proxy.id,
                    client_ip=s.get('Client IP') or (s.get('ClientIP') or ''),
                    server_ip=s.get('Server IP') or (s.get('ServerIP') or ''),
                    protocol=s.get('Protocol') or '',
                    user=s.get('User Name') or s.get('User') or '',
                    policy=s.get('URL') or '',
                    category=s.get('Age(seconds) Status') or s.get('Status') or '',
                    extra=s
                )
                db.session.add(rec)
                saved += 1
            db.session.commit()
        return saved

    def search_sessions(self, group_id: int | None, keyword: str | None, limit: int = 1000) -> List[Dict[str, Any]]:
        query = SessionRecord.query
        if group_id:
            query = query.filter(SessionRecord.group_id == group_id)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                db.or_(
                    SessionRecord.client_ip.ilike(like),
                    SessionRecord.server_ip.ilike(like),
                    SessionRecord.user.ilike(like),
                    SessionRecord.policy.ilike(like),
                    SessionRecord.protocol.ilike(like),
                    SessionRecord.category.ilike(like)
                )
            )
        return [r.to_dict() for r in query.order_by(SessionRecord.created_at.desc()).limit(limit).all()]

# 전역 인스턴스
monitoring_service = MonitoringService()