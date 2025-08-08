"""프록시 매니저 모듈"""

import threading
import time
from typing import List, Dict, Any
from .proxy_client import ProxyClient

class ProxyManager:
    """프록시 서버 통합 관리자"""
    
    def __init__(self):
        self.clients = {}  # proxy_id: ProxyClient
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_interval = 30  # 30초 간격
    
    def add_proxy(self, proxy_server) -> bool:
        """프록시 서버 추가"""
        try:
            client = ProxyClient(
                host=proxy_server.host,
                port=proxy_server.ssh_port,
                username=proxy_server.username,
                password=proxy_server.password
            )
            
            self.clients[proxy_server.id] = client
            return True
            
        except Exception as e:
            print(f"프록시 추가 실패 ({proxy_server.host}): {e}")
            return False
    
    def remove_proxy(self, proxy_id: int):
        """프록시 서버 제거"""
        if proxy_id in self.clients:
            self.clients[proxy_id].disconnect()
            del self.clients[proxy_id]
    
    def test_proxy_connection(self, proxy_id: int) -> Dict[str, Any]:
        """특정 프록시 연결 테스트"""
        if proxy_id not in self.clients:
            return {'success': False, 'message': '프록시 클라이언트가 없습니다.'}
        
        return self.clients[proxy_id].test_connection()
    
    def test_all_connections(self) -> Dict[int, Dict[str, Any]]:
        """모든 프록시 연결 테스트"""
        results = {}
        
        for proxy_id, client in self.clients.items():
            results[proxy_id] = client.test_connection()
        
        return results
    
    def get_proxy_system_info(self, proxy_id: int) -> Dict[str, Any]:
        """특정 프록시 시스템 정보 조회"""
        if proxy_id not in self.clients:
            return {'error': '프록시 클라이언트가 없습니다.'}
        
        return self.clients[proxy_id].get_system_info()
    
    def get_proxy_resource_usage(self, proxy_id: int) -> Dict[str, Any]:
        """특정 프록시 리소스 사용률 조회"""
        if proxy_id not in self.clients:
            return {'error': '프록시 클라이언트가 없습니다.'}
        
        return self.clients[proxy_id].get_resource_usage()
    
    def get_all_resource_usage(self) -> Dict[int, Dict[str, Any]]:
        """모든 프록시 리소스 사용률 조회"""
        results = {}
        
        for proxy_id, client in self.clients.items():
            results[proxy_id] = client.get_resource_usage()
        
        return results
    
    def check_proxy_services(self, proxy_id: int) -> Dict[str, Any]:
        """특정 프록시 서비스 상태 확인"""
        if proxy_id not in self.clients:
            return {'error': '프록시 클라이언트가 없습니다.'}
        
        return self.clients[proxy_id].check_proxy_status()
    
    def execute_command_on_proxy(self, proxy_id: int, command: str) -> Dict[str, Any]:
        """특정 프록시에서 명령 실행"""
        if proxy_id not in self.clients:
            return {'success': False, 'error': '프록시 클라이언트가 없습니다.'}
        
        return self.clients[proxy_id].execute_command(command)
    
    def execute_command_on_all(self, command: str) -> Dict[int, Dict[str, Any]]:
        """모든 프록시에서 명령 실행"""
        results = {}
        
        for proxy_id, client in self.clients.items():
            results[proxy_id] = client.execute_command(command)
        
        return results
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        print("프록시 모니터링 시작됨")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        print("프록시 모니터링 중지됨")
    
    def set_monitoring_interval(self, interval: int):
        """모니터링 간격 설정 (초)"""
        self.monitoring_interval = max(10, interval)  # 최소 10초
    
    def _monitoring_loop(self):
        """모니터링 루프"""
        while self.monitoring_active:
            try:
                self._update_proxy_status()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                print(f"모니터링 오류: {e}")
                time.sleep(5)  # 오류 발생 시 5초 대기
    
    def _update_proxy_status(self):
        """프록시 상태 업데이트"""
        # 순환 임포트 방지를 위해 함수 내부에서 임포트
        from models import ProxyServer, db
        
        for proxy_id, client in self.clients.items():
            try:
                # 연결 테스트
                connection_result = client.test_connection()
                
                # 데이터베이스에서 프록시 서버 조회
                proxy_server = ProxyServer.query.get(proxy_id)
                if proxy_server:
                    # 상태 업데이트
                    proxy_server.is_active = connection_result['success']
                    db.session.commit()
                    
                    if connection_result['success']:
                        print(f"프록시 {proxy_server.name} ({proxy_server.host}) - 온라인")
                    else:
                        print(f"프록시 {proxy_server.name} ({proxy_server.host}) - 오프라인")
                        
            except Exception as e:
                print(f"프록시 {proxy_id} 상태 업데이트 오류: {e}")
    
    def reload_proxies(self):
        """데이터베이스에서 프록시 목록 다시 로드"""
        # 순환 임포트 방지를 위해 함수 내부에서 임포트
        from models import ProxyServer
        
        # 기존 클라이언트들 정리
        for client in self.clients.values():
            client.disconnect()
        self.clients.clear()
        
        # 데이터베이스에서 프록시 서버들 로드
        proxy_servers = ProxyServer.query.all()
        
        for proxy_server in proxy_servers:
            self.add_proxy(proxy_server)
        
        print(f"{len(proxy_servers)}개의 프록시 서버가 로드되었습니다.")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """모니터링 상태 조회"""
        return {
            'active': self.monitoring_active,
            'interval': self.monitoring_interval,
            'proxy_count': len(self.clients),
            'connected_proxies': len([
                client for client in self.clients.values() 
                if client.connected
            ])
        }

# 전역 프록시 매니저 인스턴스
proxy_manager = ProxyManager()