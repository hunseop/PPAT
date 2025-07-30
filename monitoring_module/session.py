"""세션 모니터링 모듈"""

import logging
from typing import List, Dict, Any
from .client.ssh import SSHClient
from .config import Config
from .utils import split_line, logger

class SessionManager:
    """세션 모니터링을 위한 클래스"""
    
    def __init__(self, host: str, username: str = None, password: str = None):
        """
        Args:
            host (str): 호스트 주소
            username (str): SSH 사용자명
            password (str): SSH 비밀번호
        """
        self.host = host
        self.username = username
        self.password = password
        
    def get_session_data(self) -> List[Dict[str, Any]]:
        """세션 데이터를 조회하여 반환"""
        try:
            with SSHClient(self.host, self.username, self.password) as ssh:
                # 세션 데이터 조회
                stdin, stdout, stderr = ssh.execute_command(Config.SESSION_CMD)
                lines = stdout.readlines()
                
                if not lines:
                    logger.warning("세션 데이터가 비어있습니다.")
                    return []
                
                # 마지막 빈 줄 제거
                if lines and lines[-1].strip() == '':
                    lines.pop()
                
                # 헤더와 데이터 분리
                if len(lines) < 2:
                    logger.warning("세션 데이터 형식이 올바르지 않습니다.")
                    return []
                
                header = split_line(lines[1])
                data_lines = lines[2:]
                
                sessions = []
                for line in data_lines:
                    try:
                        data = split_line(line)
                        if len(data) >= len(header):
                            session = {}
                            for i, column in enumerate(header):
                                session[column] = data[i] if i < len(data) else ''
                            sessions.append(session)
                    except Exception as e:
                        logger.error(f"세션 데이터 파싱 오류: {e}")
                        continue
                
                return sessions
                
        except Exception as e:
            logger.error(f"세션 데이터 조회 중 오류: {e}")
            return []
    
    def get_unique_clients(self) -> int:
        """고유 클라이언트 수를 반환"""
        try:
            sessions = self.get_session_data()
            if not sessions:
                return 0
            
            # Client IP 컬럼에서 고유 IP 추출
            client_ips = set()
            for session in sessions:
                client_ip = session.get('Client IP', '')
                if client_ip and ':' in client_ip:
                    ip = client_ip.split(':')[0]
                    client_ips.add(ip)
            
            return len(client_ips)
            
        except Exception as e:
            logger.error(f"고유 클라이언트 수 계산 중 오류: {e}")
            return 0
    
    def get_session_count(self) -> int:
        """총 세션 수를 반환"""
        try:
            sessions = self.get_session_data()
            return len(sessions)
        except Exception as e:
            logger.error(f"세션 수 계산 중 오류: {e}")
            return 0 
