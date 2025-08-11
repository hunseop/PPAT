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

            def pick(session: dict, keys: list[str]) -> str:
                # 후보 키들 중 첫번째로 값이 존재하는 것을 선택 (대소문자/공백 차이 보정)
                if not session:
                    return ''
                # 키 정규화 맵
                normalized = {}
                for k, v in session.items():
                    normalized[''.join(k.lower().split())] = v
                for key in keys:
                    nk = ''.join(key.lower().split())
                    if nk in normalized and normalized[nk] not in (None, ''):
                        return str(normalized[nk])
                return ''

            def to_int(v: str) -> int | None:
                try:
                    return int(v)
                except Exception:
                    return None

            def to_bigint(v: str) -> int | None:
                try:
                    return int(v)
                except Exception:
                    return None

            def to_dt(v: str):
                from datetime import datetime
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S']:
                    try:
                        return datetime.strptime(v, fmt)
                    except Exception:
                        continue
                return None

            def strip_port(ip: str) -> str:
                if not ip:
                    return ''
                return ip.split(':')[0]

            for s in info.get('sessions', []):
                client_ip = strip_port(pick(s, ['Client IP', 'ClientIP', 'Client Address', 'Client']))
                server_ip = strip_port(pick(s, ['Server IP', 'ServerIP', 'Server Address', 'Server']))
                protocol = pick(s, ['Protocol', 'Proto'])
                user = pick(s, ['User Name', 'User', 'Username', 'UserName'])
                url = pick(s, ['URL', 'Uri', 'Request URL'])
                status = pick(s, ['Status', 'Age(seconds) Status', 'In use'])

                rec = SessionRecord(
                    group_id=group_id,
                    proxy_id=proxy.id,
                    client_ip=client_ip,
                    server_ip=server_ip,
                    protocol=protocol,
                    user=user,
                    policy=url,
                    category=status,
                    transaction=pick(s, ['Transaction']),
                    creation_time=to_dt(pick(s, ['Creation Time'])),
                    cust_id=pick(s, ['Cust ID']),
                    user_name=pick(s, ['User Name', 'User']),
                    client_side_mwg_ip=pick(s, ['Client Side MWG IP']),
                    server_side_mwg_ip=pick(s, ['Server Side MWG IP']),
                    cl_bytes_received=to_bigint(pick(s, ['CL Bytes Received'])),
                    cl_bytes_sent=to_bigint(pick(s, ['CL Bytes Sent'])),
                    srv_bytes_received=to_bigint(pick(s, ['SRV Bytes Received'])),
                    srv_bytes_sent=to_bigint(pick(s, ['SRV Bytes Sent'])),
                    trxn_index=to_int(pick(s, ['Trxn Index'])),
                    age_seconds=to_int(pick(s, ['Age(seconds)'])),
                    in_use=pick(s, ['In use']),
                    url=pick(s, ['URL']),
                    extra=s
                )
                db.session.add(rec)
                saved += 1
            db.session.commit()
        return saved

    def collect_sessions_by_proxy(self, proxy_id: int, replace: bool = True) -> int:
        from models import ProxyServer, SessionRecord, db  # local import
        proxy = ProxyServer.query.get(proxy_id)
        if not proxy or not proxy.is_active:
            return 0
        if replace:
            SessionRecord.query.filter_by(proxy_id=proxy_id).delete()
            db.session.commit()
        monitor = ProxyMonitor(
            host=proxy.host,
            username=proxy.username,
            password=proxy.password,
            ssh_port=proxy.ssh_port,
            snmp_port=proxy.snmp_port,
            snmp_community=proxy.snmp_community
        )
        info = monitor.get_session_info()

        # 재사용: 그룹 저장 로직과 동일한 매핑
        def pick(session: dict, keys: list[str]) -> str:
            if not session:
                return ''
            normalized = {''.join(k.lower().split()): v for k, v in session.items()}
            for key in keys:
                nk = ''.join(key.lower().split())
                if nk in normalized and normalized[nk] not in (None, ''):
                    return str(normalized[nk])
            return ''

        def to_int(v: str) -> int | None:
            try:
                return int(v)
            except Exception:
                return None

        def to_bigint(v: str) -> int | None:
            try:
                return int(v)
            except Exception:
                return None

        def to_dt(v: str):
            from datetime import datetime
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S']:
                try:
                    return datetime.strptime(v, fmt)
                except Exception:
                    continue
            return None

        def strip_port(ip: str) -> str:
            if not ip:
                return ''
            return ip.split(':')[0]

        saved = 0
        from models import SessionRecord
        for s in info.get('sessions', []):
            client_ip = strip_port(pick(s, ['Client IP', 'ClientIP', 'Client Address', 'Client']))
            server_ip = strip_port(pick(s, ['Server IP', 'ServerIP', 'Server Address', 'Server']))
            protocol = pick(s, ['Protocol', 'Proto'])
            user = pick(s, ['User Name', 'User', 'Username', 'UserName'])
            url = pick(s, ['URL', 'Uri', 'Request URL'])
            status = pick(s, ['Status', 'Age(seconds) Status', 'In use'])
            rec = SessionRecord(
                group_id=proxy.group_id,
                proxy_id=proxy.id,
                client_ip=client_ip,
                server_ip=server_ip,
                protocol=protocol,
                user=user,
                policy=url,
                category=status,
                transaction=pick(s, ['Transaction']),
                creation_time=to_dt(pick(s, ['Creation Time'])),
                cust_id=pick(s, ['Cust ID']),
                user_name=pick(s, ['User Name', 'User']),
                client_side_mwg_ip=pick(s, ['Client Side MWG IP']),
                server_side_mwg_ip=pick(s, ['Server Side MWG IP']),
                cl_bytes_received=to_bigint(pick(s, ['CL Bytes Received'])),
                cl_bytes_sent=to_bigint(pick(s, ['CL Bytes Sent'])),
                srv_bytes_received=to_bigint(pick(s, ['SRV Bytes Received'])),
                srv_bytes_sent=to_bigint(pick(s, ['SRV Bytes Sent'])),
                trxn_index=to_int(pick(s, ['Trxn Index'])),
                age_seconds=to_int(pick(s, ['Age(seconds)'])),
                in_use=pick(s, ['In use']),
                url=pick(s, ['URL']),
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

    def search_sessions_paginated(self,
                                 group_id: int | None,
                                 proxy_id: int | None,
                                 keyword: str | None,
                                 protocol: str | None,
                                 status: str | None,
                                 client_ip: str | None,
                                 server_ip: str | None,
                                 user: str | None,
                                 url_contains: str | None,
                                 page: int = 1,
                                 page_size: int = 100) -> tuple[list[dict], int]:
        """필터 및 페이지네이션 지원 세션 검색 (임시저장 DB 기준)
        Returns: (items, total)
        """
        from models import SessionRecord, db  # local import
        query = SessionRecord.query
        if group_id:
            query = query.filter(SessionRecord.group_id == group_id)
        if proxy_id:
            query = query.filter(SessionRecord.proxy_id == proxy_id)
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
        if protocol:
            query = query.filter(SessionRecord.protocol.ilike(protocol))
        if status:
            query = query.filter(SessionRecord.category.ilike(f"%{status}%"))
        if client_ip:
            query = query.filter(SessionRecord.client_ip.ilike(f"%{client_ip}%"))
        if server_ip:
            query = query.filter(SessionRecord.server_ip.ilike(f"%{server_ip}%"))
        if user:
            query = query.filter(SessionRecord.user.ilike(f"%{user}%"))
        if url_contains:
            query = query.filter(SessionRecord.policy.ilike(f"%{url_contains}%"))

        total = query.count()
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 100
        items = (
            query.order_by(SessionRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [r.to_dict() for r in items], total


# 전역 인스턴스
device_manager = DeviceManager()
monitoring_service = MonitoringService()