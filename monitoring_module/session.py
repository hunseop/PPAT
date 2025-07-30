import pandas as pd
from .clients.ssh import SSHClient
from .config import Config
from .utils import split_line

class SessionManager:
    def __init__(self, host, username=None, password=None):
        self.host = host
        self.username = username
        self.password = password

    def get_session(self) -> pd.DataFrame:
        """프록시 서버의 세션 정보를 가져옴"""
        with SSHClient(self.host, self.username, self.password) as ssh:
            stdin, stdout, stderr = ssh.execute_command(Config.SESSION_CMD)
            lines = stdout.readlines()

            try:
                if not lines:  # 결과가 없는 경우
                    return pd.DataFrame()
                    
                lines.pop(-1)  # 마지막 빈 줄 제거
                header = split_line(lines[1])
                data = [split_line(line) for line in lines[2:]]
                session = pd.DataFrame(data, columns=header)
                
                # 컬럼명 매핑
                column_mapping = {
                    header[0]: 'Creation Time',
                    header[1]: 'User Name',
                    header[2]: 'Client IP',
                    header[3]: 'Proxy IP',
                    header[4]: 'URL',
                    header[5]: 'CL Bytes Received',
                    header[6]: 'CL Bytes Sent',
                    header[7]: 'Age(seconds)'
                }
                session = session.rename(columns=column_mapping)
            except Exception as e:
                print(f"세션 데이터 처리 중 오류 발생: {e}")
                session = pd.DataFrame()

            return session

    def search_session(self, search_term: str = None, session: pd.DataFrame = None) -> pd.DataFrame:
        """세션 데이터 검색
        
        Args:
            search_term (str): 검색어
            session (pd.DataFrame, optional): 검색할 세션 데이터. None인 경우 새로 조회
        
        Returns:
            pd.DataFrame: 검색된 세션 데이터
        """
        if session is None:
            session = self.get_session()
            
        if session.empty or not search_term:
            return session

        # 모든 컬럼에서 검색어 찾기
        mask = pd.DataFrame(False, index=session.index, columns=[0])
        for column in session.columns:
            mask = mask | session[column].str.contains(str(search_term), case=False, na=False)
        
        return session[mask] 
