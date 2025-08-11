from typing import Dict, Any, List

from .proxy_client import ProxyClient
from .monitoring import ProxyMonitor


class DeviceManager:
    def __init__(self):
        self.clients: Dict[int, ProxyClient] = {}

    def add_or_update(self, proxy) -> None:
        client = ProxyClient(
            host=proxy.host,
            port=proxy.ssh_port,
            username=proxy.username,
            password=proxy.password
        )
        self.clients[proxy.id] = client

    def remove(self, proxy_id: int) -> None:
        client = self.clients.pop(proxy_id, None)
        if client:
            client.disconnect()

    def reload(self) -> int:
        for client in self.clients.values():
            client.disconnect()
        self.clients.clear()
        from models import ProxyServer  # local import
        proxies = ProxyServer.query.all()
        for proxy in proxies:
            self.add_or_update(proxy)
        return len(proxies)

    def test_connection(self, proxy_id: int) -> Dict[str, Any]:
        client = self.clients.get(proxy_id)
        if not client:
            return {'success': False, 'message': '프록시 클라이언트가 없습니다.'}
        return client.test_connection()

    def execute_command(self, proxy_id: int, command: str) -> Dict[str, Any]:
        client = self.clients.get(proxy_id)
        if not client:
            return {'success': False, 'error': '프록시 클라이언트가 없습니다.'}
        return client.execute_command(command)

    def get_system_info(self, proxy_id: int) -> Dict[str, Any]:
        client = self.clients.get(proxy_id)
        if not client:
            return {'error': '프록시 클라이언트가 없습니다.'}
        info = client.get_system_info()
        client.disconnect()
        return info

    def get_resource_usage(self, proxy_id: int) -> Dict[str, Any]:
        client = self.clients.get(proxy_id)
        if not client:
            return {'error': '프록시 클라이언트가 없습니다.'}
        usage = client.get_resource_usage()
        client.disconnect()
        return usage

    def check_services(self, proxy_id: int) -> Dict[str, Any]:
        client = self.clients.get(proxy_id)
        if not client:
            return {'error': '프록시 클라이언트가 없습니다.'}
        status = client.check_proxy_status()
        client.disconnect()
        return status


class MonitoringService:
    def __init__(self):
        pass

    def get_active_config(self):
        from models import MonitoringConfig  # local import
        return MonitoringConfig.query.filter_by(is_active=True).first()

    def update_active_config(self, data: Dict[str, Any]):
        from models import db  # local import
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
        from models import ProxyServer  # local import
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
        from models import ProxyServer, SessionRecord, db  # local import
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
        from models import SessionRecord, db  # local import
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
device_manager = DeviceManager()
monitoring_service = MonitoringService()