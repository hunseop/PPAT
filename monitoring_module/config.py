"""모니터링 모듈 설정

SSH 연결 및 모니터링 관련 설정을 관리합니다.
"""

from typing import Optional, List
from dataclasses import dataclass

@dataclass
class ProxyConfig:
    """프록시 설정 클래스"""
    host: str
    username: str = 'root'
    password: str = '123456'
    port: int = 22
    is_main: bool = False
    cluster_name: Optional[str] = None

@dataclass
class MonitoringConfig:
    """모니터링 설정 클래스"""
    cpu_threshold: int = 10
    memory_threshold: int = 21
    default_delay: int = 5
    snmp_community: str = 'public'
    snmp_port: int = 161
    snmp_oids: dict = None
    session_cmd: str = None

    def __post_init__(self):
        if self.snmp_oids is None:
            self.snmp_oids = {
                'CPU': '1.3.6.1.2.1.25.3.3.1.2.1',
                'Memory': '1.3.6.1.2.1.25.2.2.1.1',
                'CC': '1.3.6.1.2.1.25.4.2.1.2',
                'CS': '1.3.6.1.2.1.25.4.2.1.3',
                'HTTP': '1.3.6.1.2.1.25.4.2.1.2',
                'HTTPS': '1.3.6.1.2.1.25.4.2.1.3',
                'FTP': '1.3.6.1.2.1.25.4.2.1.4',
            }
        if self.session_cmd is None:
            self.session_cmd = """/opt/mwg/bin/mwg-core -S connections | awk -F " \\| " '{print $2" | "%5" | "%6" | "%6" | "%7" | "%18" | "%10" | "%11" | "%15"}'"""

class Config:
    """설정 관리 클래스"""
    def __init__(
        self,
        proxies: List[ProxyConfig],
        monitoring: Optional[MonitoringConfig] = None
    ):
        self.proxies = proxies
        self.monitoring = monitoring or MonitoringConfig()
        
        # Main 프록시 검증
        main_proxies = [p for p in proxies if p.is_main]
        if not main_proxies:
            raise ValueError("메인 프록시가 지정되지 않았습니다.")
        if len(main_proxies) > 1:
            raise ValueError("메인 프록시는 하나만 지정할 수 있습니다.")
        
        # 클러스터 검증
        clusters = {}
        for proxy in proxies:
            if proxy.cluster_name:
                if proxy.cluster_name not in clusters:
                    clusters[proxy.cluster_name] = []
                clusters[proxy.cluster_name].append(proxy)
        
        self.clusters = clusters
    
    @property
    def main_proxy(self) -> ProxyConfig:
        """메인 프록시 설정 반환"""
        return next(p for p in self.proxies if p.is_main)
    
    def get_cluster_proxies(self, cluster_name: str) -> List[ProxyConfig]:
        """클러스터에 속한 프록시 목록 반환"""
        return self.clusters.get(cluster_name, [])
