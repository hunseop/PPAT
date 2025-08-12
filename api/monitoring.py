"""모니터링 API"""

from flask import Blueprint, jsonify, request
from models import ProxyServer, MonitoringConfig, db, SessionRecord, ProxyGroup
from backend import ProxyMonitor
import logging
from backend import monitoring_service

logger = logging.getLogger(__name__)

monitoring_bp = Blueprint('monitoring', __name__)

@monitoring_bp.route('/resources', methods=['GET'])
def get_resources():
    """모든 활성 프록시의 리소스 사용률 조회 (group_id 필터 지원)"""
    try:
        group_id = request.args.get('group_id', type=int)
        resources_data = monitoring_service.collect_resources(group_id)
        return jsonify({'success': True, 'data': resources_data, 'total_proxies': len(resources_data)})
        
    except Exception as e:
        logger.error(f"리소스 데이터 조회 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/resources/<int:proxy_id>', methods=['GET'])
def get_proxy_resources(proxy_id):
    """특정 프록시의 리소스 사용률 조회"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        
        if not proxy.is_active:
            return jsonify({'error': '비활성화된 프록시입니다.'}), 400
        
        if not proxy.username or not proxy.password:
            return jsonify({'error': 'SSH 사용자명 또는 비밀번호가 설정되지 않았습니다.'}), 400
        
        # ProxyMonitor 인스턴스 생성
        monitor = ProxyMonitor(
            host=proxy.host,
            username=proxy.username,
            password=proxy.password,
            ssh_port=proxy.ssh_port,
            snmp_port=proxy.snmp_port,
            snmp_community=proxy.snmp_community
        )
        
        # 리소스 데이터 수집
        resource_data = monitor.get_resource_data()
        
        result = {
            'proxy_id': proxy.id,
            'proxy_name': proxy.name,
            'host': proxy.host,
            'group_name': proxy.group.name if proxy.group else None,
            'is_main': proxy.is_main,
            'resource_data': resource_data
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"프록시 {proxy_id} 리소스 수집 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/test/<int:proxy_id>', methods=['POST'])
def test_proxy_connection(proxy_id):
    """프록시 연결 테스트"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        
        if not proxy.username or not proxy.password:
            return jsonify({
                'success': False, 
                'message': 'SSH 사용자명 또는 비밀번호가 설정되지 않았습니다.'
            }), 400
        
        # ProxyMonitor로 연결 테스트
        monitor = ProxyMonitor(
            host=proxy.host,
            username=proxy.username,
            password=proxy.password,
            ssh_port=proxy.ssh_port,
            snmp_port=proxy.snmp_port,
            snmp_community=proxy.snmp_community
        )
        
        connection_result = monitor.test_connection()
        
        if connection_result:
            # 연결 성공 시 프록시를 활성화
            proxy.is_active = True
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'{proxy.host}에 연결되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'{proxy.host} 연결에 실패했습니다.'
            })
            
    except Exception as e:
        logger.error(f"프록시 {proxy_id} 연결 테스트 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'연결 테스트 중 오류: {str(e)}'
        }), 500

@monitoring_bp.route('/status/<int:proxy_id>', methods=['GET'])
def get_proxy_comprehensive_status(proxy_id):
    """프록시의 포괄적인 상태 정보"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        
        if not proxy.username or not proxy.password:
            return jsonify({'error': 'SSH 사용자명 또는 비밀번호가 설정되지 않았습니다.'}), 400
        
        # ProxyMonitor 인스턴스 생성
        monitor = ProxyMonitor(
            host=proxy.host,
            username=proxy.username,
            password=proxy.password,
            ssh_port=proxy.ssh_port,
            snmp_port=proxy.snmp_port,
            snmp_community=proxy.snmp_community
        )
        
        # 포괄적 상태 정보 수집
        status_data = monitor.get_comprehensive_status()
        
        result = {
            'proxy_id': proxy.id,
            'proxy_name': proxy.name,
            'host': proxy.host,
            'group_name': proxy.group.name if proxy.group else None,
            'is_main': proxy.is_main,
            'status': status_data
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"프록시 {proxy_id} 포괄적 상태 조회 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/summary', methods=['GET'])
def get_monitoring_summary():
    """모니터링 요약 정보 조회"""
    try:
        # 전체 프록시 수
        total_proxies = ProxyServer.query.count()
        
        # 활성 프록시 수
        active_proxies = ProxyServer.query.filter_by(is_active=True).count()
        
        # 사용자명/비밀번호가 설정된 프록시 수
        configured_proxies = ProxyServer.query.filter(
            ProxyServer.username.isnot(None),
            ProxyServer.password.isnot(None)
        ).count()
        
        # 그룹별 통계
        from sqlalchemy import func
        group_stats = db.session.query(
            ProxyServer.group_id,
            func.count(ProxyServer.id).label('total'),
            func.sum(ProxyServer.is_active).label('active')
        ).group_by(ProxyServer.group_id).all()
        
        return jsonify({
            'total_proxies': total_proxies,
            'active_proxies': active_proxies,
            'offline_proxies': total_proxies - active_proxies,
            'configured_proxies': configured_proxies,
            'group_stats': [
                {
                    'group_id': stat.group_id,
                    'total': stat.total,
                    'active': stat.active or 0,
                    'offline': stat.total - (stat.active or 0)
                }
                for stat in group_stats
            ]
        })
        
    except Exception as e:
        logger.error(f"모니터링 요약 조회 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/config', methods=['GET'])
def get_monitoring_config():
    """활성 모니터링 설정 조회"""
    try:
        config = monitoring_service.get_active_config()
        if not config:
            return jsonify({'error': '활성화된 모니터링 설정이 없습니다.'}), 404
        return jsonify(config.to_dict())
    except Exception as e:
        logger.error(f"모니터링 설정 조회 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/config', methods=['PUT'])
def update_monitoring_config():
    """활성 모니터링 설정 수정 (SNMP OIDs, session_cmd, 임계치 등)"""
    try:
        data = request.get_json() or {}
        config = monitoring_service.update_active_config(data)
        return jsonify({'success': True, 'config': config.to_dict()})
    except Exception as e:
        logger.error(f"모니터링 설정 수정 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """활성 프록시들에 대한 세션 목록/요약 조회"""
    try:
        group_id = request.args.get('group_id', type=int)
        persist = request.args.get('persist', default='0') == '1'
        query = ProxyServer.query.filter_by(is_active=True)
        if group_id:
            query = query.filter(ProxyServer.group_id == group_id)
        active_proxies = query.all()

        # 선택적으로 그룹 전체를 DB에 저장 (조회 시 자동 저장 옵션)
        saved = 0
        if group_id and persist:
            saved = monitoring_service.collect_sessions_by_group(group_id, persist=True)

        results = []
        for proxy in active_proxies:
            try:
                if not proxy.username or not proxy.password:
                    continue
                monitor = ProxyMonitor(
                    host=proxy.host,
                    username=proxy.username,
                    password=proxy.password,
                    ssh_port=proxy.ssh_port,
                    snmp_port=proxy.snmp_port,
                    snmp_community=proxy.snmp_community
                )
                info = monitor.get_session_info()
                results.append({
                    'proxy_id': proxy.id,
                    'proxy_name': proxy.name,
                    'host': proxy.host,
                    'group_name': proxy.group.name if proxy.group else None,
                    'is_main': proxy.is_main,
                    'unique_clients': info.get('unique_clients', 0),
                    'total_sessions': info.get('total_sessions', 0),
                    'headers': info.get('headers') or [],
                    'sessions': info.get('sessions', [])
                })
            except Exception as e:
                logger.error(f"세션 조회 실패 ({proxy.name}): {e}")
        return jsonify({'success': True, 'data': results, 'saved': saved})
    except Exception as e:
        logger.error(f"세션 목록 조회 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/sessions/<int:proxy_id>', methods=['GET'])
def get_sessions_by_proxy(proxy_id):
    """특정 프록시 세션 조회"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        if not proxy.is_active:
            return jsonify({'error': '비활성 프록시입니다.'}), 400
        if not proxy.username or not proxy.password:
            return jsonify({'error': 'SSH 자격 증명이 없습니다.'}), 400

        # 옵션: 조회 시 저장
        persist = request.args.get('persist', default='0') == '1'
        saved = 0
        if persist:
            saved = monitoring_service.collect_sessions_by_proxy(proxy_id, replace=True)

        monitor = ProxyMonitor(
            host=proxy.host,
            username=proxy.username,
            password=proxy.password,
            ssh_port=proxy.ssh_port,
            snmp_port=proxy.snmp_port,
            snmp_community=proxy.snmp_community
        )
        info = monitor.get_session_info()
        return jsonify({
            'proxy_id': proxy.id,
            'proxy_name': proxy.name,
            'host': proxy.host,
            'group_name': proxy.group.name if proxy.group else None,
            'is_main': proxy.is_main,
            'unique_clients': info.get('unique_clients', 0),
            'total_sessions': info.get('total_sessions', 0),
            'headers': info.get('headers') or [],
            'sessions': info.get('sessions', []),
            'saved': saved
        })
    except Exception as e:
        logger.error(f"특정 프록시 세션 조회 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/sessions/group/<int:group_id>', methods=['GET'])
def collect_sessions_by_group(group_id):
    """그룹 단위 세션 수집 및 임시저장. ?persist=1 시 기존 그룹 데이터 삭제 후 저장"""
    try:
        persist = request.args.get('persist', default='1') == '1'
        saved = monitoring_service.collect_sessions_by_group(group_id, persist=persist)
        return jsonify({'success': True, 'group_id': group_id, 'saved': saved})
    except Exception as e:
        logger.error(f"그룹 세션 수집 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/sessions/datatables', methods=['GET'])
def get_sessions_datatables():
    """DataTables 서버 사이드 처리 API"""
    try:
        # DataTables 파라미터 파싱
        draw = request.args.get('draw', type=int)
        start = request.args.get('start', type=int, default=0)
        length = request.args.get('length', type=int, default=10)
        search_value = request.args.get('search[value]', type=str)
        
        # 정렬 파라미터
        order_column = request.args.get('order[0][column]', type=int)
        order_dir = request.args.get('order[0][dir]', type=str)
        
        # 컬럼 매핑 (0: id [hidden], 1: proxy_id, 2: client_ip, 3: server_ip, 4: user, 5: url_host, 6: category,
        #           7: cl_bytes_sent, 8: cl_bytes_received, 9: age_seconds, 10: created_at)
        columns = ['id', 'proxy_id', 'client_ip', 'server_ip', 'user', 'url_host', 
                  'category', 'cl_bytes_sent', 'cl_bytes_received', 'age_seconds', 'created_at']
        
        # 필터 파라미터
        group_id = request.args.get('group_id', type=int)
        proxy_id = request.args.get('proxy_id', type=int)
        
        # 쿼리 구성
        query = SessionRecord.query
        
        # 그룹/프록시 필터
        if group_id:
            query = query.filter(SessionRecord.group_id == group_id)
        if proxy_id:
            query = query.filter(SessionRecord.proxy_id == proxy_id)
            
        # 검색어 적용
        if search_value:
            search_filter = []
            for column in ['client_ip', 'server_ip', 'user', 'url', 'url_host', 'category']:
                search_filter.append(getattr(SessionRecord, column).ilike(f'%{search_value}%'))
            query = query.filter(db.or_(*search_filter))
            
        # 전체 레코드 수
        total_records = query.count()
        filtered_records = total_records
        
        # 정렬
        if order_column is not None and order_dir:
            column = columns[order_column]
            if order_dir == 'desc':
                query = query.order_by(db.desc(getattr(SessionRecord, column)))
            else:
                query = query.order_by(getattr(SessionRecord, column))
        else:
            query = query.order_by(db.desc(SessionRecord.created_at))
        
        # 페이징
        query = query.offset(start).limit(length)
        
        # 결과 포맷팅
        data = []
        for record in query.all():
            data.append([
                record.id,
                record.proxy_id,
                record.client_ip,
                record.server_ip,
                record.user,
                record.url_host,
                record.category,
                record.cl_bytes_sent,
                record.cl_bytes_received,
                record.age_seconds,
                record.created_at.isoformat() if record.created_at else None
            ])
        
        return jsonify({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': filtered_records,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"DataTables 데이터 조회 실패: {e}")
        return jsonify({
            'draw': request.args.get('draw', type=int),
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': str(e)
        }), 500

@monitoring_bp.route('/sessions/detail/<int:session_id>', methods=['GET'])
def get_session_detail(session_id: int):
    """세션 상세 조회 (모든 필드)"""
    try:
        record = SessionRecord.query.get_or_404(session_id)
        return jsonify({'success': True, 'data': record.to_dict()})
    except Exception as e:
        logger.error(f"세션 상세 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@monitoring_bp.route('/sessions/search', methods=['GET'])
def search_sessions():
    """임시저장된 세션 검색. 파라미터: group_id, proxy_id, q(키워드), protocol, status, client_ip, server_ip, user, url, page, page_size"""
    try:
        group_id = request.args.get('group_id', type=int)
        proxy_id = request.args.get('proxy_id', type=int)
        keyword = request.args.get('q', type=str)
        protocol = request.args.get('protocol', type=str)
        status = request.args.get('status', type=str)
        client_ip = request.args.get('client_ip', type=str)
        server_ip = request.args.get('server_ip', type=str)
        user = request.args.get('user', type=str)
        url_contains = request.args.get('url', type=str)
        page = request.args.get('page', default=1, type=int)
        page_size = request.args.get('page_size', default=100, type=int)

        items, total = monitoring_service.search_sessions_paginated(
            group_id=group_id,
            proxy_id=proxy_id,
            keyword=keyword,
            protocol=protocol,
            status=status,
            client_ip=client_ip,
            server_ip=server_ip,
            user=user,
            url_contains=url_contains,
            page=page,
            page_size=page_size
        )
        return jsonify({'success': True, 'data': items, 'total': total, 'page': page, 'page_size': page_size})
    except Exception as e:
        logger.error(f"세션 검색 실패: {e}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/sessions/export', methods=['GET'])
def export_sessions_csv():
    """필터를 적용한 임시저장 세션 CSV 다운로드"""
    try:
        import csv
        from io import StringIO
        from flask import Response
        group_id = request.args.get('group_id', type=int)
        proxy_id = request.args.get('proxy_id', type=int)
        keyword = request.args.get('q', type=str)
        protocol = request.args.get('protocol', type=str)
        status = request.args.get('status', type=str)
        client_ip = request.args.get('client_ip', type=str)
        server_ip = request.args.get('server_ip', type=str)
        user = request.args.get('user', type=str)
        url_contains = request.args.get('url', type=str)
        # 전체 내보내기: 페이지 제한 없이
        items, total = monitoring_service.search_sessions_paginated(
            group_id=group_id,
            proxy_id=proxy_id,
            keyword=keyword,
            protocol=protocol,
            status=status,
            client_ip=client_ip,
            server_ip=server_ip,
            user=user,
            url_contains=url_contains,
            page=1,
            page_size=1000000
        )
        # 컬럼 헤더
        fieldnames = ['proxy_id','client_ip','server_ip','user','url_host','url','category','created_at','creation_time']
        # CSV 생성
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for r in items:
            writer.writerow({k: r.get(k, '') for k in fieldnames})
        csv_content = buffer.getvalue()
        buffer.close()
        return Response(csv_content, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=sessions.csv'})
    except Exception as e:
        logger.error(f"CSV 내보내기 실패: {e}")
        return jsonify({'error': str(e)}), 500