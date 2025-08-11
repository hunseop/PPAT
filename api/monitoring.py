"""모니터링 API"""

from flask import Blueprint, jsonify, request
from models import ProxyServer, MonitoringConfig, db, SessionRecord, ProxyGroup
from unified import ProxyMonitor
import logging
from unified import monitoring_service

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
        active_proxies = ProxyServer.query.filter_by(is_active=True).all()
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
                    'sessions': info.get('sessions', [])
                })
            except Exception as e:
                logger.error(f"세션 조회 실패 ({proxy.name}): {e}")
        return jsonify({'success': True, 'data': results})
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
            'sessions': info.get('sessions', [])
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

@monitoring_bp.route('/sessions/search', methods=['GET'])
def search_sessions():
    """임시저장된 세션 검색. 파라미터: group_id, q(키워드)"""
    try:
        group_id = request.args.get('group_id', type=int)
        keyword = request.args.get('q', type=str)
        records = monitoring_service.search_sessions(group_id, keyword, limit=1000)
        return jsonify({'success': True, 'data': records})
    except Exception as e:
        logger.error(f"세션 검색 실패: {e}")
        return jsonify({'error': str(e)}), 500