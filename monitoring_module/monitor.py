"""통합 프록시 모니터링 클래스

프록시 서버의 연결 테스트, 상태 확인, 리소스 모니터링을 통합 제공합니다.
"""

import paramiko
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from .utils import get_current_timestamp, validate_resource_data, logger, split_line

# SNMP import with error handling
try:
    from pysnmp.hlapi import *
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False
    logger.warning("SNMP 라이브러리를 사용할 수 없습니다. SNMP 모니터링이 비활성화됩니다.")

class ProxyMonitor:
    """통합 프록시 모니터링 클래스
    
    프록시 서버의 연결 테스트, 상태 확인, 리소스 모니터링을 통합 제공합니다.
    """
    
    def __init__(self, host: str, username: str = None, password: str = None, 
                 ssh_port: int = 22, snmp_port: int = 161, snmp_community: str = 'public'):
        """
        Args:
            host: 프록시 서버 호스트
            username: SSH 사용자명 (기본값 없음)
            password: SSH 비밀번호 (기본값 없음)
            ssh_port: SSH 포트
            snmp_port: SNMP 포트
            snmp_community: SNMP 커뮤니티
        """
        self.host = host
        self.username = username
        self.password = password
        self.ssh_port = ssh_port
        self.snmp_port = snmp_port
        self.snmp_community = snmp_community
        self._ssh_client = None
        
        # 연결 재시도 설정
        self.max_retries = 3
        self.retry_delay = 5
    
    def get_monitoring_config(self):
        """데이터베이스에서 모니터링 설정을 가져옴 (DB 전용)"""
        try:
            from flask import current_app
            if current_app:
                from models import MonitoringConfig
                config = MonitoringConfig.query.filter_by(is_active=True).first()
                return config
            return None
        except Exception as e:
            logger.error(f"모니터링 설정 조회 실패: {e}")
            return None
    
    def _get_default_config(self):
        """더 이상 사용하지 않음: 하드코딩 기본값 제거"""
        return None
    
    def _create_ssh_connection(self):
        """SSH 연결 생성"""
        if not self.username or not self.password:
            raise ValueError("SSH 사용자명과 비밀번호가 필요합니다.")
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                if self._ssh_client:
                    self._ssh_client.close()
                
                self._ssh_client = paramiko.SSHClient()
                self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._ssh_client.connect(
                    self.host,
                    username=self.username,
                    password=self.password,
                    port=self.ssh_port,
                    timeout=30
                )
                logger.info(f"SSH 연결 성공: {self.host}")
                return self._ssh_client
                
            except Exception as e:
                last_exception = e
                logger.warning(f"SSH 연결 실패 ({attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        logger.error(f"SSH 연결 최대 재시도 횟수 초과: {last_exception}")
        raise ConnectionError(f"SSH 연결 실패: {last_exception}")
    
    def _execute_ssh_command(self, command: str) -> Tuple[List[str], str]:
        """SSH 명령어 실행"""
        try:
            ssh = self._create_ssh_connection()
            stdin, stdout, stderr = ssh.exec_command(command)
            
            # 결과 읽기
            output_lines = stdout.readlines()
            error_output = stderr.read().decode('utf-8')
            
            if error_output:
                logger.warning(f"SSH 명령어 실행 시 경고: {error_output}")
            
            return output_lines, error_output
            
        except Exception as e:
            logger.error(f"SSH 명령어 실행 실패: {e}")
            raise
        finally:
            if self._ssh_client:
                self._ssh_client.close()
                self._ssh_client = None
    
    def test_connection(self) -> bool:
        """프록시 서버 연결 테스트"""
        try:
            self._create_ssh_connection()
            return True
        except Exception as e:
            logger.error(f"연결 테스트 실패: {e}")
            return False
        finally:
            if self._ssh_client:
                self._ssh_client.close()
                self._ssh_client = None
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 기본 상태 정보 조회"""
        try:
            # 시스템 업타임 조회
            uptime_lines, _ = self._execute_ssh_command("uptime")
            uptime = uptime_lines[0].strip() if uptime_lines else "Unknown"
            
            # 시스템 로드 조회
            load_lines, _ = self._execute_ssh_command("cat /proc/loadavg")
            load_avg = load_lines[0].split()[:3] if load_lines else ["0", "0", "0"]
            
            # 디스크 사용량 조회
            disk_lines, _ = self._execute_ssh_command("df -h / | tail -1")
            disk_info = disk_lines[0].split() if disk_lines else []
            disk_usage = disk_info[4] if len(disk_info) > 4 else "0%"
            
            return {
                'status': 'online',
                'uptime': uptime,
                'load_avg': {
                    '1min': load_avg[0],
                    '5min': load_avg[1], 
                    '15min': load_avg[2]
                },
                'disk_usage': disk_usage,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"시스템 상태 조회 실패: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_memory_usage(self) -> int:
        """메모리 사용률 조회"""
        try:
            memory_cmd = '''awk '/MemTotal/ {total=$2} /MemAvailable/ {available=$2} END {printf "%.0f", 100 - (available / total * 100)}' /proc/meminfo'''
            memory_lines, _ = self._execute_ssh_command(memory_cmd)
            
            if memory_lines and memory_lines[0].strip():
                return int(memory_lines[0].strip())
            return -1
            
        except Exception as e:
            logger.error(f"메모리 사용률 조회 실패: {e}")
            return -1
    
    def get_session_info(self) -> Dict[str, Any]:
        """세션 정보 조회"""
        try:
            config = self.get_monitoring_config()
            if not config or not config.session_cmd:
                logger.warning("session_cmd 미설정: 세션 조회를 건너뜁니다.")
                return {'unique_clients': 0, 'total_sessions': 0, 'sessions': []}
            session_lines, _ = self._execute_ssh_command(config.session_cmd)
            
            if not session_lines:
                return {'unique_clients': 0, 'total_sessions': 0, 'sessions': []}
            
            # 마지막 빈 줄 제거
            if session_lines and session_lines[-1].strip() == '':
                session_lines.pop()
            
            if len(session_lines) < 2:
                return {'unique_clients': 0, 'total_sessions': 0, 'sessions': []}
            
            # 헤더와 데이터 분리
            header = split_line(session_lines[1])
            data_lines = session_lines[2:]
            
            sessions = []
            client_ips = set()
            
            for line in data_lines:
                try:
                    data = split_line(line)
                    if len(data) >= len(header):
                        session = {}
                        for i, column in enumerate(header):
                            session[column] = data[i] if i < len(data) else ''
                        sessions.append(session)
                        
                        # Client IP 추출
                        client_ip = session.get('Client IP', '')
                        if client_ip and ':' in client_ip:
                            ip = client_ip.split(':')[0]
                            client_ips.add(ip)
                            
                except Exception as e:
                    logger.error(f"세션 데이터 파싱 오류: {e}")
                    continue
            
            return {
                'unique_clients': len(client_ips),
                'total_sessions': len(sessions),
                'sessions': sessions
            }
            
        except Exception as e:
            logger.error(f"세션 정보 조회 실패: {e}")
            return {'unique_clients': 0, 'total_sessions': 0, 'sessions': []}
    
    def get_snmp_data(self) -> Dict[str, int]:
        """SNMP 데이터 수집"""
        if not SNMP_AVAILABLE:
            logger.warning("SNMP 라이브러리가 없어 SNMP 데이터를 수집할 수 없습니다.")
            return self._get_empty_snmp_data()
        
        try:
            config = self.get_monitoring_config()
            snmp_oids = (config.snmp_oids if config and config.snmp_oids else {})
            if not snmp_oids:
                logger.warning("SNMP OIDs 미설정: SNMP 수집을 건너뜁니다.")
                return self._get_empty_snmp_data()
            
            # OID 객체 생성
            oids = [ObjectType(ObjectIdentity(oid)) for oid in snmp_oids.values()]
            
            # SNMP 요청
            errorIndication, errorStatus, errorIndex, varBinds = next(
                getCmd(SnmpEngine(),
                      CommunityData(self.snmp_community, mpModel=1),
                      UdpTransportTarget((self.host, self.snmp_port)),
                      ContextData(),
                      *oids)
            )
            
            if errorIndication:
                logger.error(f"SNMP 에러: {errorIndication}")
                return self._get_empty_snmp_data()
            elif errorStatus:
                logger.error(f"SNMP 에러 상태: {errorStatus}")
                return self._get_empty_snmp_data()
            
            # 결과 처리
            result = {}
            for varBind in varBinds:
                try:
                    oid, value = varBind
                    oid_str = str(oid)
                    
                    # OID에 해당하는 메트릭 찾기
                    metric = next((desc for desc, cfg_oid in snmp_oids.items() 
                                if str(cfg_oid) in oid_str), None)
                    
                    if metric:
                        try:
                            int_value = int(value)
                            if metric in ['CPU', 'Memory'] and not (0 <= int_value <= 100):
                                logger.warning(f"잘못된 {metric} 값: {int_value}")
                                int_value = -1
                            result[metric.lower()] = int_value
                        except (ValueError, TypeError):
                            result[metric.lower()] = -1
                            
                except Exception as e:
                    logger.error(f"SNMP 응답 처리 중 에러: {e}")
                    continue
            
            # 누락된 메트릭 처리
            for metric in snmp_oids.keys():
                if metric.lower() not in result:
                    result[metric.lower()] = -1
            
            return result
            
        except Exception as e:
            logger.error(f"SNMP 데이터 수집 실패: {e}")
            return self._get_empty_snmp_data()
    
    def _get_empty_snmp_data(self) -> Dict[str, int]:
        """빈 SNMP 데이터 반환"""
        return {
            'cpu': -1,
            'memory': -1,
            'cc': -1,
            'cs': -1,
            'http': -1,
            'https': -1,
            'ftp': -1
        }
    
    def get_resource_data(self) -> Dict[str, Any]:
        """통합 리소스 데이터 수집"""
        try:
            timestamp = get_current_timestamp()
            
            # 메모리 사용률 조회
            memory_usage = self.get_memory_usage()
            
            # 세션 정보 조회
            session_info = self.get_session_info()
            
            # SNMP 데이터 수집
            snmp_data = self.get_snmp_data()
            
            # 결과 데이터 생성
            result = {
                'date': timestamp['date'],
                'time': timestamp['time'],
                'device': self.host,
                'cpu': str(snmp_data.get('cpu', -1)),
                'memory': str(memory_usage),
                'uc': str(session_info['unique_clients']),
                'cc': str(snmp_data.get('cc', -1)),
                'cs': str(snmp_data.get('cs', -1)),
                'http': str(snmp_data.get('http', -1)),
                'https': str(snmp_data.get('https', -1)),
                'ftp': str(snmp_data.get('ftp', -1)),
                'total_sessions': session_info['total_sessions']
            }
            
            # 데이터 검증 및 임계값 확인
            if validate_resource_data(result):
                try:
                    config = self.get_monitoring_config()
                    if config:
                        cpu_value = float(result['cpu']) if result['cpu'] != 'error' else -1
                        mem_value = float(result['memory']) if result['memory'] != 'error' else -1
                        if cpu_value >= (config.cpu_threshold or 80):
                            logger.warning(f"CPU 사용률 임계값 초과: {cpu_value}%")
                        if mem_value >= (config.memory_threshold or 80):
                            logger.warning(f"메모리 사용률 임계값 초과: {mem_value}%")
                except (ValueError, AttributeError):
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"리소스 데이터 수집 중 오류: {e}")
            timestamp = get_current_timestamp()
            return {
                'date': timestamp['date'],
                'time': timestamp['time'],
                'device': self.host,
                'cpu': 'error',
                'memory': 'error',
                'uc': 'error',
                'cc': 'error',
                'cs': 'error',
                'http': 'error',
                'https': 'error',
                'ftp': 'error',
                'total_sessions': 0
            }
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """포괄적인 프록시 상태 정보"""
        try:
            system_status = self.get_system_status()
            resource_data = self.get_resource_data()
            
            return {
                'connection': self.test_connection(),
                'system': system_status,
                'resources': resource_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"포괄적 상태 조회 실패: {e}")
            return {
                'connection': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        if self._ssh_client:
            try:
                self._ssh_client.close()
            except Exception as e:
                logger.error(f"SSH 연결 종료 중 오류: {e}")
            finally:
                self._ssh_client = None