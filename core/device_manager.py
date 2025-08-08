from typing import Dict, Any
from proxy_module.proxy_client import ProxyClient
from models import ProxyServer, db

class DeviceManager:
    def __init__(self):
        self.clients: Dict[int, ProxyClient] = {}

    def add_or_update(self, proxy: ProxyServer) -> None:
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

# 전역 인스턴스
device_manager = DeviceManager()