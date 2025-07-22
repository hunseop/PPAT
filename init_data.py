"""초기 샘플 데이터 생성 스크립트"""

from app import create_app
from models import db
from models import ProxyGroup, ProxyServer, ResourceStat, SessionInfo
from datetime import datetime, timedelta
import random

def create_sample_data():
    """샘플 데이터 생성"""
    
    # 기존 데이터 삭제
    ResourceStat.query.delete()
    SessionInfo.query.delete()
    ProxyServer.query.delete()
    ProxyGroup.query.delete()
    
    # 프록시 그룹 생성
    groups = [
        ProxyGroup(name="Production-Proxy", description="운영 프록시 그룹"),
        ProxyGroup(name="Development-Proxy", description="개발 프록시 그룹"),
        ProxyGroup(name="Testing-Proxy", description="테스트 프록시 그룹")
    ]
    
    for group in groups:
        db.session.add(group)
    
    db.session.commit()
    
    # 프록시 서버 생성
    servers = [
        # Production 그룹
        ProxyServer(
            name="PROD-MAIN-01",
            host="192.168.1.10",
            group_id=groups[0].id,
            is_main=True,
            description="운영 메인 프록시 서버"
        ),
        ProxyServer(
            name="PROD-CLUSTER-01",
            host="192.168.1.11",
            group_id=groups[0].id,
            is_main=False,
            description="운영 클러스터 프록시 서버 1"
        ),
        ProxyServer(
            name="PROD-CLUSTER-02",
            host="192.168.1.12",
            group_id=groups[0].id,
            is_main=False,
            description="운영 클러스터 프록시 서버 2"
        ),
        
        # Development 그룹
        ProxyServer(
            name="DEV-MAIN-01",
            host="192.168.2.10",
            group_id=groups[1].id,
            is_main=True,
            description="개발 메인 프록시 서버"
        ),
        ProxyServer(
            name="DEV-CLUSTER-01",
            host="192.168.2.11",
            group_id=groups[1].id,
            is_main=False,
            description="개발 클러스터 프록시 서버"
        ),
        
        # Testing 그룹
        ProxyServer(
            name="TEST-MAIN-01",
            host="192.168.3.10",
            group_id=groups[2].id,
            is_main=True,
            description="테스트 메인 프록시 서버"
        )
    ]
    
    for server in servers:
        db.session.add(server)
    
    db.session.commit()
    
    # 최근 리소스 통계 생성 (최근 1시간)
    now = datetime.utcnow()
    
    for server in servers:
        for i in range(60):  # 60개의 데이터 포인트 (1분마다)
            timestamp = now - timedelta(minutes=i)
            
            stat = ResourceStat(
                proxy_id=server.id,
                timestamp=timestamp,
                cpu_usage=round(random.uniform(10, 90), 2),
                memory_usage=round(random.uniform(20, 80), 2),
                disk_usage=round(random.uniform(30, 70), 2),
                network_in=round(random.uniform(100, 1000), 2),
                network_out=round(random.uniform(50, 500), 2),
                session_count=random.randint(10, 100),
                status=random.choice(['online', 'online', 'online', 'warning'])
            )
            db.session.add(stat)
    
    # 샘플 세션 데이터 생성
    sample_ips = ['192.168.100.1', '192.168.100.2', '192.168.100.3', '10.0.0.1', '10.0.0.2']
    sample_users = ['user1', 'user2', 'admin', 'test_user', 'developer']
    sample_urls = [
        'https://www.google.com',
        'https://www.naver.com',
        'https://www.github.com',
        'https://stackoverflow.com',
        'https://www.youtube.com'
    ]
    
    for _ in range(50):  # 50개의 세션 데이터
        session = SessionInfo(
            proxy_id=random.choice(servers).id,
            client_ip=random.choice(sample_ips),
            username=random.choice(sample_users),
            url=random.choice(sample_urls),
            protocol=random.choice(['HTTP', 'HTTPS']),
            status=random.choice(['active', 'closed', 'blocked']),
            timestamp=now - timedelta(minutes=random.randint(0, 60))
        )
        db.session.add(session)
    
    db.session.commit()
    print("샘플 데이터가 성공적으로 생성되었습니다!")
    print(f"- 프록시 그룹: {len(groups)}개")
    print(f"- 프록시 서버: {len(servers)}개")
    print(f"- 리소스 통계: {len(servers) * 60}개")
    print(f"- 세션 데이터: 50개")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        create_sample_data()