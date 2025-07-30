"""모니터링 API"""

from flask import Blueprint, jsonify, request
from models import ProxyServer, db
from monitoring_module import ResourceMonitor
import logging

logger = logging.getLogger(__name__)

monitoring_bp = Blueprint('monitoring', __name__)

@monitoring_bp.route('/resources', methods=['GET'])
def get_resources():
    """모든 활성 프록시의 리소스 사용률 조회"""
    try:
        # 활성화된 프록시 서버들 조회
        active_proxies = ProxyServer.query.filter_by(is_active=True).all()
        
        if not active_proxies:
            return jsonify({'message': '활성화된 프록시 서버가 없습니다.', 'data': []}), 200
        
        resources_data = []
        
        for proxy in active_proxies:
            try:
                # ResourceMonitor 인스턴스 생성
                monitor = ResourceMonitor(
                    host=proxy.host,
                    username=proxy.username,
                    password=proxy.password
                )
                
                # 리소스 데이터 수집
                resource_data = monitor.get_resource_data()
                
                # 프록시 정보와 함께 반환
                proxy_resource = {
                    'proxy_id': proxy.id,
                    'proxy_name': proxy.name,
                    'host': proxy.host,
                    'group_name': proxy.group.name if proxy.group else None,
                    'is_main': proxy.is_main,
                    'resource_data': resource_data
                }
                
                resources_data.append(proxy_resource)
                
            except Exception as e:
                logger.error(f"프록시 {proxy.name} 리소스 수집 실패: {e}")
                # 에러 상태로라도 포함
                error_data = {
                    'proxy_id': proxy.id,
                    'proxy_name': proxy.name,
                    'host': proxy.host,
                    'group_name': proxy.group.name if proxy.group else None,
                    'is_main': proxy.is_main,
                    'resource_data': {
                        'date': '',
                        'time': '',
                        'device': proxy.host,
                        'cpu': 'error',
                        'memory': 'error',
                        'uc': 'error',
                        'cc': 'error',
                        'cs': 'error',
                        'http': 'error',
                        'https': 'error',
                        'ftp': 'error'
                    }
                }
                resources_data.append(error_data)
        
        return jsonify({
            'success': True,
            'data': resources_data,
            'total_proxies': len(resources_data)
        })
        
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
        
        # ResourceMonitor 인스턴스 생성
        monitor = ResourceMonitor(
            host=proxy.host,
            username=proxy.username,
            password=proxy.password
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

@monitoring_bp.route('/summary', methods=['GET'])
def get_monitoring_summary():
    """모니터링 요약 정보 조회"""
    try:
        # 전체 프록시 수
        total_proxies = ProxyServer.query.count()
        
        # 활성 프록시 수
        active_proxies = ProxyServer.query.filter_by(is_active=True).count()
        
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