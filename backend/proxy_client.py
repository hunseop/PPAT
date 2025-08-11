"""프록시 클라이언트 모듈 (platform)"""

import paramiko
import socket
import subprocess
import time
from typing import Dict, Any, Optional

class ProxyClient:
    """프록시 서버 연결 및 관리 클라이언트"""
    
    def __init__(self, host: str, port: int = 22, username: str = 'root', password: str = '123456'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ssh_client = None
        self.connected = False
    
    def connect(self) -> bool:
        """SSH 연결 시도"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            self.connected = True
            return True
            
        except Exception as e:
            print(f"SSH 연결 실패 ({self.host}:{self.port}): {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """SSH 연결 해제"""
        if self.ssh_client:
            self.ssh_client.close()
            self.connected = False
    
    def test_connection(self) -> Dict[str, Any]:
        """연결 테스트"""
        result = {
            'success': False,
            'message': '',
            'response_time': 0
        }
        
        start_time = time.time()
        
        try:
            # TCP 연결 테스트
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            tcp_result = sock.connect_ex((self.host, self.port))
            sock.close()
            
            response_time = round((time.time() - start_time) * 1000, 2)
            result['response_time'] = response_time
            
            if tcp_result == 0:
                result['success'] = True
                result['message'] = f'연결 성공 (응답시간: {response_time}ms)'
            else:
                result['message'] = f'연결 실패: 포트 {self.port}에 접근할 수 없습니다'
                
        except Exception as e:
            result['message'] = f'연결 테스트 오류: {str(e)}'
            result['response_time'] = round((time.time() - start_time) * 1000, 2)
            
        return result
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """원격 명령 실행"""
        if not self.connected:
            if not self.connect():
                return {'success': False, 'error': '연결되지 않음'}
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            return {
                'success': exit_code == 0,
                'output': output,
                'error': error,
                'exit_code': exit_code
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 조회"""
        commands = {
            'hostname': 'hostname',
            'uptime': 'uptime',
            'cpu_info': 'cat /proc/cpuinfo | grep "model name" | head -1',
            'memory_info': 'free -h',
            'disk_usage': 'df -h /',
            'network_interfaces': 'ip addr show'
        }
        
        system_info = {}
        
        for key, command in commands.items():
            result = self.execute_command(command)
            if result['success']:
                system_info[key] = result['output'].strip()
            else:
                system_info[key] = f"오류: {result['error']}"
        
        return system_info
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """리소스 사용률 조회"""
        try:
            # CPU 사용률
            cpu_cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
            cpu_result = self.execute_command(cpu_cmd)
            cpu_usage = float(cpu_result['output'].strip()) if cpu_result['success'] else 0
            
            # 메모리 사용률
            mem_cmd = "free | grep Mem | awk '{printf \"%.2f\", $3/$2 * 100.0}'"
            mem_result = self.execute_command(mem_cmd)
            memory_usage = float(mem_result['output'].strip()) if mem_result['success'] else 0
            
            # 디스크 사용률
            disk_cmd = "df / | grep -vE '^Filesystem' | awk '{print $5}' | cut -d'%' -f1"
            disk_result = self.execute_command(disk_cmd)
            disk_usage = float(disk_result['output'].strip()) if disk_result['success'] else 0
            
            return {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0,
                'timestamp': time.time(),
                'error': str(e)
            }
    
    def check_proxy_status(self) -> Dict[str, Any]:
        """프록시 서비스 상태 확인"""
        # 일반적인 프록시 서비스들 확인
        services = ['squid', 'nginx', 'apache2', 'httpd']
        
        status = {}
        
        for service in services:
            cmd = f"systemctl is-active {service}"
            result = self.execute_command(cmd)
            
            if result['success'] and 'active' in result['output']:
                status[service] = 'running'
            else:
                status[service] = 'stopped'
        
        # 네트워크 포트 확인
        port_cmd = "netstat -tlnp | grep :80"
        port_result = self.execute_command(port_cmd)
        
        status['port_80_open'] = bool(port_result['success'] and port_result['output'])
        
        return status
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()