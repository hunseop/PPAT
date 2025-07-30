from pysnmp.hlapi import *
from .clients.ssh import SSHClient
from .config import Config
from .utils import get_current_timestamp, validate_resource_data, logger, split_line

class ResourceMonitor:
    def __init__(self, host, username=None, password=None):
        self.host = host
        self.username = username
        self.password = password

    def get_memory_and_uniq_clients(self) -> tuple:
        """메모리 사용률과 고유 클라이언트 수를 한번에 조회"""
        memory_cmd = '''awk '/MemTotal/ {total=$2} /MemAvailable/ {available=$2} END {printf "%.0f", 100 - (available / total * 100)}' /proc/meminfo'''
        try:
            with SSHClient(self.host, self.username, self.password) as ssh:
                # 메모리 데이터 조회
                stdin, stdout, stderr = ssh.execute_command(memory_cmd)
                memory_value = stdout.readlines()
                memory = -1 if not memory_value else int(memory_value[0])

                # 세션 데이터 조회
                stdin, stdout, stderr = ssh.execute_command(Config.SESSION_CMD)
                lines = stdout.readlines()
                
                # 고유 클라이언트 수 계산
                unique_clients = 0
                try:
                    if lines:
                        lines.pop(-1)  # 마지막 빈 줄 제거
                        header = split_line(lines[1])
                        data = [split_line(line) for line in lines[2:]]
                        client_ips = [row[2].split(':')[0] for row in data]  # Client IP 컬럼
                        unique_clients = len(set(client_ips))
                except Exception as e:
                    logger.error(f"고유 클라이언트 수 계산 중 오류: {e}")
                
                return memory, unique_clients

        except Exception as e:
            logger.error(f"메모리와 세션 데이터 조회 중 오류: {e}")
            return -1, 0

    def get_snmp_data(self) -> dict:
        """SNMP를 통해 시스템 데이터를 수집"""
        result = {}
        try:
            # OID 객체 생성 - 단순화
            odis = [ObjectType(ObjectIdentity(oid)) for oid in Config.SNMP_OIDS.values()]

            # SNMP 요청
            errorIndication, errorStatus, errorIndex, varBinds = next(
                getCmd(SnmpEngine(),
                      CommunityData(Config.SNMP_COMMUNITY, mpModel=1),  # SNMPv2c 명시적 지정
                      UdpTransportTarget((self.host, Config.SNMP_PORT)),
                      ContextData(),
                      *odis)
            )
            
            if errorIndication:
                logger.error(f"SNMP 에러: {errorIndication}")
                return {metric.lower(): -1 for metric in Config.SNMP_OIDS.keys()}
            elif errorStatus:
                logger.error(f"SNMP 에러 상태: {errorStatus}, 인덱스: {errorIndex}")
                return {metric.lower(): -1 for metric in Config.SNMP_OIDS.keys()}
            
            # 결과 처리
            if not varBinds:
                logger.error("SNMP 응답이 비어있습니다")
                return {metric.lower(): -1 for metric in Config.SNMP_OIDS.keys()}

            for varBind in varBinds:
                try:
                    oid, value = varBind
                    oid_str = str(oid)
                    # OID에 해당하는 메트릭 찾기
                    metric = next((desc for desc, cfg_oid in Config.SNMP_OIDS.items() 
                                if str(cfg_oid) in oid_str), None)
                    
                    if metric:
                        try:
                            value = int(value)
                            if metric in ['CPU', 'Memory'] and not (0 <= value <= 100):
                                logger.warning(f"잘못된 {metric} 값: {value}")
                                value = -1
                            result[metric.lower()] = value
                        except (ValueError, TypeError) as e:
                            logger.error(f"SNMP 값 변환 에러 ({metric}): {value}, 에러: {e}")
                            result[metric.lower()] = -1
                    else:
                        logger.warning(f"알 수 없는 OID 응답: {oid_str}")
                except Exception as e:
                    logger.error(f"SNMP 응답 처리 중 에러: {e}")
                    continue
            
            # 누락된 메트릭에 대한 처리
            for metric in Config.SNMP_OIDS.keys():
                if metric.lower() not in result:
                    result[metric.lower()] = -1
            
            return result
            
        except Exception as e:
            logger.error(f"SNMP 데이터 수집 중 에러: {e}")
            return {metric.lower(): -1 for metric in Config.SNMP_OIDS.keys()}

    def get_resource_data(self) -> dict:
        """시스템 리소스 데이터를 수집하여 반환"""
        try:
            timestamp = get_current_timestamp()
            
            # 메모리와 고유 클라이언트 수를 한번에 조회
            memory, unique_clients = self.get_memory_and_uniq_clients()

            # SNMP 데이터 수집
            snmp_data = self.get_snmp_data()
            if not snmp_data:  # SNMP 데이터 수집 실패 시 기본값 설정
                snmp_data = {
                    'cpu': -1,
                    'cc': -1,
                    'cs': -1,
                    'http': -1,
                    'https': -1,
                    'ftp': -1
                }

            # 결과 데이터 생성
            result = {
                'date': timestamp['date'],
                'time': timestamp['time'],
                'device': self.host,
                'cpu': str(snmp_data['cpu']),
                'memory': str(memory),
                'uc': str(unique_clients),
                'cc': str(snmp_data['cc']),
                'cs': str(snmp_data['cs']),
                'http': str(snmp_data['http']),
                'https': str(snmp_data['https']),
                'ftp': str(snmp_data['ftp'])
            }

            # 데이터 검증 및 임계값 확인
            if validate_resource_data(result):
                try:
                    cpu_value = float(result['cpu'])
                    mem_value = float(result['memory'])
                    
                    if cpu_value >= Config.CPU_THRESHOLD:
                        logger.warning(f"CPU 사용률 임계값 초과: {cpu_value}%")
                    if mem_value >= Config.MEMORY_THRESHOLD:
                        logger.warning(f"메모리 사용률 임계값 초과: {mem_value}%")
                except ValueError:
                    pass  # 에러 상태인 경우 무시
            
            return result
            
        except Exception as e:
            logger.error(f"리소스 데이터 수집 중 오류 발생: {e}")
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
                'ftp': 'error'
            } 
