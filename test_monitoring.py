#!/usr/bin/env python3
"""
모니터링 모듈 CLI 테스트 도구

사용법:
    python test_monitoring.py --help
    python test_monitoring.py test-proxy --host 192.168.1.10
    python test_monitoring.py test-monitoring --host 192.168.1.10
    python test_monitoring.py compare --host 192.168.1.10
"""

import argparse
import sys
import json
import time
from datetime import datetime

def test_proxy_module(host, username='root', password='123456', port=22):
    """proxy_module 테스트"""
    print(f"\n🔧 === PROXY_MODULE 테스트 ===")
    print(f"대상: {host}:{port} (사용자: {username})")
    
    try:
        from proxy_module.proxy_client import ProxyClient
        
        print("✅ ProxyClient 생성 중...")
        client = ProxyClient(host=host, port=port, username=username, password=password)
        
        print("🔗 SSH 연결 테스트...")
        if client.test_connection():
            print("✅ SSH 연결 성공!")
            
            print("📊 시스템 상태 조회...")
            status = client.get_status()
            print(f"Status: {json.dumps(status, indent=2, ensure_ascii=False)}")
            
            print("💾 리소스 정보 조회...")
            resources = client.get_resources()
            print(f"Resources: {json.dumps(resources, indent=2, ensure_ascii=False)}")
            
        else:
            print("❌ SSH 연결 실패!")
            
    except Exception as e:
        print(f"❌ proxy_module 테스트 실패: {e}")
    
    print(f"🔧 === PROXY_MODULE 테스트 완료 ===\n")

def test_monitoring_module(host, username='root', password='123456', snmp_port=161, snmp_community='public'):
    """monitoring_module 테스트"""
    print(f"\n📊 === MONITORING_MODULE 테스트 ===")
    print(f"대상: {host} (SSH: {username}, SNMP: {snmp_port}/{snmp_community})")
    
    try:
        # Flask app context 설정
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from app import create_app
        from monitoring_module import ResourceMonitor
        
        app = create_app()
        with app.app_context():
            print("✅ ResourceMonitor 생성 중...")
            monitor = ResourceMonitor(
                host=host, 
                username=username, 
                password=password,
                snmp_port=snmp_port,
                snmp_community=snmp_community
            )
            
            print("🔗 SSH 연결 테스트...")
            try:
                memory, unique_clients = monitor.get_memory_and_uniq_clients()
                print(f"✅ SSH 연결 성공! 메모리: {memory}%, 고유 클라이언트: {unique_clients}")
            except Exception as e:
                print(f"❌ SSH 연결 실패: {e}")
            
            print("📡 SNMP 데이터 수집...")
            try:
                snmp_data = monitor.get_snmp_data()
                print(f"SNMP 데이터: {json.dumps(snmp_data, indent=2, ensure_ascii=False)}")
            except Exception as e:
                print(f"❌ SNMP 수집 실패: {e}")
            
            print("📈 전체 리소스 데이터 수집...")
            try:
                resource_data = monitor.get_resource_data()
                print(f"리소스 데이터: {json.dumps(resource_data, indent=2, ensure_ascii=False)}")
            except Exception as e:
                print(f"❌ 리소스 수집 실패: {e}")
            
    except Exception as e:
        print(f"❌ monitoring_module 테스트 실패: {e}")
    
    print(f"📊 === MONITORING_MODULE 테스트 완료 ===\n")

def compare_modules(host, username='root', password='123456', port=22, snmp_port=161, snmp_community='public'):
    """두 모듈 비교 테스트"""
    print(f"\n🔍 === 모듈 비교 테스트 ===")
    print(f"대상: {host}")
    
    # proxy_module 테스트
    proxy_results = {}
    try:
        from proxy_module.proxy_client import ProxyClient
        client = ProxyClient(host=host, port=port, username=username, password=password)
        
        if client.test_connection():
            proxy_results['connection'] = True
            proxy_results['status'] = client.get_status()
            proxy_results['resources'] = client.get_resources()
        else:
            proxy_results['connection'] = False
    except Exception as e:
        proxy_results['error'] = str(e)
    
    # monitoring_module 테스트
    monitoring_results = {}
    try:
        # Flask app context 설정
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from app import create_app
        from monitoring_module import ResourceMonitor
        
        app = create_app()
        with app.app_context():
            monitor = ResourceMonitor(host=host, username=username, password=password, 
                                    snmp_port=snmp_port, snmp_community=snmp_community)
            
            monitoring_results['resource_data'] = monitor.get_resource_data()
            monitoring_results['snmp_data'] = monitor.get_snmp_data()
            
            memory, unique_clients = monitor.get_memory_and_uniq_clients()
            monitoring_results['memory'] = memory
            monitoring_results['unique_clients'] = unique_clients
        
    except Exception as e:
        monitoring_results['error'] = str(e)
    
    # 결과 출력
    print("\n📋 === 비교 결과 ===")
    print(f"🔧 proxy_module 결과:")
    print(json.dumps(proxy_results, indent=2, ensure_ascii=False))
    
    print(f"\n📊 monitoring_module 결과:")
    print(json.dumps(monitoring_results, indent=2, ensure_ascii=False))
    
    print(f"\n🔍 === 모듈 비교 완료 ===\n")

def test_database_config():
    """데이터베이스 모니터링 설정 테스트"""
    print(f"\n🗄️  === 데이터베이스 설정 테스트 ===")
    
    try:
        # Flask 앱 컨텍스트 필요
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from app import create_app
        from models import MonitoringConfig
        
        app = create_app()
        with app.app_context():
            print("✅ Flask 앱 컨텍스트 생성 성공")
            
            # 모니터링 설정 조회
            configs = MonitoringConfig.query.all()
            print(f"📝 저장된 모니터링 설정 수: {len(configs)}")
            
            for config in configs:
                print(f"\n📋 설정 ID {config.id}: {config.name}")
                print(f"   - 설명: {config.description}")
                print(f"   - SNMP OIDs: {list(config.snmp_oids.keys()) if config.snmp_oids else 'None'}")
                print(f"   - CPU 임계값: {config.cpu_threshold}%")
                print(f"   - 메모리 임계값: {config.memory_threshold}%")
                print(f"   - 기본 주기: {config.default_interval}초")
                print(f"   - 활성 상태: {config.is_active}")
            
            # 활성 설정으로 ResourceMonitor 테스트
            active_config = MonitoringConfig.query.filter_by(is_active=True).first()
            if active_config:
                print(f"\n🔧 활성 설정으로 ResourceMonitor 테스트...")
                from monitoring_module import ResourceMonitor
                
                # 더미 호스트로 설정 테스트
                monitor = ResourceMonitor('127.0.0.1')
                config_from_db = monitor.get_monitoring_config()
                
                print(f"✅ 데이터베이스에서 설정 조회 성공!")
                print(f"   - 설정명: {config_from_db.name if hasattr(config_from_db, 'name') else '기본설정'}")
                print(f"   - SNMP OIDs: {list(config_from_db.snmp_oids.keys())}")
                print(f"   - 세션 명령어 길이: {len(config_from_db.session_cmd)}자")
                
    except Exception as e:
        print(f"❌ 데이터베이스 설정 테스트 실패: {e}")
    
    print(f"🗄️  === 데이터베이스 설정 테스트 완료 ===\n")

def interactive_test():
    """대화형 테스트 모드"""
    print("\n🎮 === 대화형 테스트 모드 ===")
    
    while True:
        print("\n선택하세요:")
        print("1. proxy_module 테스트")
        print("2. monitoring_module 테스트") 
        print("3. 모듈 비교 테스트")
        print("4. 데이터베이스 설정 테스트")
        print("5. 종료")
        
        choice = input("선택 (1-5): ").strip()
        
        if choice == '5':
            print("👋 테스트 종료!")
            break
        elif choice == '4':
            test_database_config()
            continue
        elif choice in ['1', '2', '3']:
            host = input("호스트 IP (기본값: 127.0.0.1): ").strip() or '127.0.0.1'
            username = input("SSH 사용자명 (기본값: root): ").strip() or 'root'
            password = input("SSH 비밀번호 (기본값: 123456): ").strip() or '123456'
            
            if choice == '1':
                port = input("SSH 포트 (기본값: 22): ").strip() or '22'
                test_proxy_module(host, username, password, int(port))
            elif choice == '2':
                snmp_port = input("SNMP 포트 (기본값: 161): ").strip() or '161'
                snmp_community = input("SNMP 커뮤니티 (기본값: public): ").strip() or 'public'
                test_monitoring_module(host, username, password, int(snmp_port), snmp_community)
            elif choice == '3':
                port = input("SSH 포트 (기본값: 22): ").strip() or '22'
                snmp_port = input("SNMP 포트 (기본값: 161): ").strip() or '161'
                snmp_community = input("SNMP 커뮤니티 (기본값: public): ").strip() or 'public'
                compare_modules(host, username, password, int(port), int(snmp_port), snmp_community)
        else:
            print("❌ 잘못된 선택입니다.")

def main():
    parser = argparse.ArgumentParser(description='모니터링 모듈 CLI 테스트 도구')
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # proxy_module 테스트
    proxy_parser = subparsers.add_parser('test-proxy', help='proxy_module 테스트')
    proxy_parser.add_argument('--host', required=True, help='대상 호스트 IP')
    proxy_parser.add_argument('--username', default='root', help='SSH 사용자명 (기본값: root)')
    proxy_parser.add_argument('--password', default='123456', help='SSH 비밀번호 (기본값: 123456)')
    proxy_parser.add_argument('--port', type=int, default=22, help='SSH 포트 (기본값: 22)')
    
    # monitoring_module 테스트
    monitoring_parser = subparsers.add_parser('test-monitoring', help='monitoring_module 테스트')
    monitoring_parser.add_argument('--host', required=True, help='대상 호스트 IP')
    monitoring_parser.add_argument('--username', default='root', help='SSH 사용자명 (기본값: root)')
    monitoring_parser.add_argument('--password', default='123456', help='SSH 비밀번호 (기본값: 123456)')
    monitoring_parser.add_argument('--snmp-port', type=int, default=161, help='SNMP 포트 (기본값: 161)')
    monitoring_parser.add_argument('--snmp-community', default='public', help='SNMP 커뮤니티 (기본값: public)')
    
    # 모듈 비교 테스트
    compare_parser = subparsers.add_parser('compare', help='두 모듈 비교 테스트')
    compare_parser.add_argument('--host', required=True, help='대상 호스트 IP')
    compare_parser.add_argument('--username', default='root', help='SSH 사용자명 (기본값: root)')
    compare_parser.add_argument('--password', default='123456', help='SSH 비밀번호 (기본값: 123456)')
    compare_parser.add_argument('--port', type=int, default=22, help='SSH 포트 (기본값: 22)')
    compare_parser.add_argument('--snmp-port', type=int, default=161, help='SNMP 포트 (기본값: 161)')
    compare_parser.add_argument('--snmp-community', default='public', help='SNMP 커뮤니티 (기본값: public)')
    
    # 데이터베이스 설정 테스트
    subparsers.add_parser('test-db', help='데이터베이스 모니터링 설정 테스트')
    
    # 대화형 모드
    subparsers.add_parser('interactive', help='대화형 테스트 모드')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print(f"🚀 모니터링 모듈 테스트 시작 - {datetime.now()}")
    
    if args.command == 'test-proxy':
        test_proxy_module(args.host, args.username, args.password, args.port)
    elif args.command == 'test-monitoring':
        test_monitoring_module(args.host, args.username, args.password, args.snmp_port, args.snmp_community)
    elif args.command == 'compare':
        compare_modules(args.host, args.username, args.password, args.port, args.snmp_port, args.snmp_community)
    elif args.command == 'test-db':
        test_database_config()
    elif args.command == 'interactive':
        interactive_test()
    
    print(f"✅ 테스트 완료 - {datetime.now()}")

if __name__ == '__main__':
    main()