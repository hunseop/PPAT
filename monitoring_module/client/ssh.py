"""모니터링을 위한 SSH 클라이언트

시스템 리소스 모니터링을 위한 SSH 연결을 관리합니다.
재시도 로직과 컨텍스트 매니저를 지원합니다.
"""

import paramiko
import time
import logging
from ..config import Config, ProxyConfig
from ..utils import logger

class SSHClient:
    """모니터링을 위한 SSH 클라이언트
    
    시스템 리소스 모니터링을 위한 SSH 연결을 관리합니다.
    재시도 로직과 컨텍스트 매니저를 지원합니다.
    """
    
    def __init__(self, proxy_config: ProxyConfig, max_retries=3, retry_delay=5):
        """
        Args:
            proxy_config (ProxyConfig): 프록시 설정
            max_retries (int): 최대 재시도 횟수
            retry_delay (int): 재시도 간격 (초)
        """
        self.proxy_config = proxy_config
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = None
        
        # paramiko 로깅 비활성화
        logging.getLogger('paramiko').setLevel(logging.CRITICAL)

    def connect(self):
        """SSH 연결 수행 (재시도 로직 포함)"""
        if self._client is not None:
            return self._client

        retries = 0
        last_exception = None

        while retries < self.max_retries:
            try:
                self._client = paramiko.SSHClient()
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._client.connect(
                    self.proxy_config.host,
                    username=self.proxy_config.username,
                    password=self.proxy_config.password,
                    port=self.proxy_config.port,
                    timeout=30  # 연결 타임아웃 30초
                )
                logger.info(f"SSH 연결 성공: {self.proxy_config.host}")
                return self._client
            except Exception as e:
                last_exception = e
                retries += 1
                if retries < self.max_retries:
                    logger.warning(f"SSH 연결 실패 ({retries}/{self.max_retries}): {e}")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"SSH 연결 최대 재시도 횟수 초과: {e}")

        raise ConnectionError(f"SSH 연결 실패: {last_exception}")

    def execute_command(self, command, timeout=60):
        """명령어 실행 (타임아웃 처리 포함)
        
        Args:
            command (str): 실행할 SSH 명령어
            timeout (int): 명령어 실행 타임아웃 (초)
            
        Returns:
            tuple: (stdin, stdout, stderr) 파일 객체
            
        Raises:
            ConnectionError: SSH 연결 실패시
            Exception: 명령어 실행 실패시
        """
        client = self.connect()
        try:
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            return stdin, stdout, stderr
        except Exception as e:
            logger.error(f"명령어 실행 실패: {e}")
            raise

    def close(self):
        """SSH 연결 종료"""
        if self._client:
            try:
                self._client.close()
                logger.info(f"SSH 연결 종료: {self.proxy_config.host}")
            except Exception as e:
                logger.error(f"SSH 연결 종료 중 오류: {e}")
            finally:
                self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 
