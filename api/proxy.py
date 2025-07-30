"""프록시 서버 관리 API"""

from flask import Blueprint, request, jsonify
from models import db, ProxyServer, ProxyGroup
from proxy_module.proxy_manager import proxy_manager
from datetime import datetime

proxy_bp = Blueprint('proxy', __name__)

@proxy_bp.route('/proxies', methods=['GET'])
def get_proxies():
    """프록시 서버 목록 조회"""
    try:
        proxies = ProxyServer.query.all()
        return jsonify([proxy.to_dict() for proxy in proxies])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies', methods=['POST'])
def create_proxy():
    """프록시 서버 추가"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        if not data.get('name') or not data.get('host'):
            return jsonify({'error': '이름과 호스트는 필수 항목입니다.'}), 400
        
        # 기본 그룹이 없으면 생성
        default_group = ProxyGroup.query.filter_by(name='기본그룹').first()
        if not default_group:
            default_group = ProxyGroup(name='기본그룹', description='기본 프록시 그룹')
            db.session.add(default_group)
            db.session.commit()
        
        # 새 프록시 서버 생성
        proxy = ProxyServer(
            name=data['name'],
            host=data['host'],
            ssh_port=data.get('ssh_port', 22),
            username=data.get('username', 'root'),
            password=data.get('password', '123456'),
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
            group_id=default_group.id
        )
        
        db.session.add(proxy)
        db.session.commit()
        
        # 프록시 매니저에 추가
        proxy_manager.add_proxy(proxy)
        
        return jsonify(proxy.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>', methods=['PUT'])
def update_proxy(proxy_id):
    """프록시 서버 수정"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        data = request.get_json()
        
        # 필수 필드 검증
        if not data.get('name') or not data.get('host'):
            return jsonify({'error': '이름과 호스트는 필수 항목입니다.'}), 400
        
        # 업데이트
        proxy.name = data['name']
        proxy.host = data['host']
        proxy.ssh_port = data.get('ssh_port', 22)
        proxy.username = data.get('username', 'root')
        if data.get('password'):  # 비밀번호가 제공된 경우만 업데이트
            proxy.password = data['password']
        proxy.description = data.get('description', '')
        proxy.is_active = data.get('is_active', True)
        proxy.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # 프록시 매니저에서 제거 후 다시 추가 (정보 업데이트)
        proxy_manager.remove_proxy(proxy_id)
        proxy_manager.add_proxy(proxy)
        
        return jsonify(proxy.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>', methods=['DELETE'])
def delete_proxy(proxy_id):
    """프록시 서버 삭제"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        
        # 프록시 매니저에서 제거
        proxy_manager.remove_proxy(proxy_id)
        
        db.session.delete(proxy)
        db.session.commit()
        
        return jsonify({'message': '프록시 서버가 삭제되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>/test', methods=['POST'])
def test_proxy_connection(proxy_id):
    """프록시 서버 연결 테스트"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        
        # 프록시 매니저를 통한 연결 테스트
        result = proxy_manager.test_proxy_connection(proxy_id)
        
        if not result or 'success' not in result:
            # 매니저에 프록시가 없는 경우 직접 추가 후 테스트
            proxy_manager.add_proxy(proxy)
            result = proxy_manager.test_proxy_connection(proxy_id)
        
        # 상태 업데이트
        proxy.is_active = result.get('success', False)
        proxy.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(result)
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'연결 테스트 중 오류가 발생했습니다: {str(e)}'
        }), 500

@proxy_bp.route('/proxies/<int:proxy_id>/info', methods=['GET'])
def get_proxy_system_info(proxy_id):
    """프록시 서버 시스템 정보 조회"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        
        # 매니저에 프록시가 없으면 추가
        if proxy_id not in proxy_manager.clients:
            proxy_manager.add_proxy(proxy)
        
        info = proxy_manager.get_proxy_system_info(proxy_id)
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>/resources', methods=['GET'])
def get_proxy_resources(proxy_id):
    """프록시 서버 리소스 사용률 조회"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        
        # 매니저에 프록시가 없으면 추가
        if proxy_id not in proxy_manager.clients:
            proxy_manager.add_proxy(proxy)
        
        resources = proxy_manager.get_proxy_resource_usage(proxy_id)
        return jsonify(resources)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>/services', methods=['GET'])
def get_proxy_services(proxy_id):
    """프록시 서버 서비스 상태 조회"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        
        # 매니저에 프록시가 없으면 추가
        if proxy_id not in proxy_manager.clients:
            proxy_manager.add_proxy(proxy)
        
        services = proxy_manager.check_proxy_services(proxy_id)
        return jsonify(services)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>/command', methods=['POST'])
def execute_command(proxy_id):
    """프록시 서버에서 명령 실행"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
        data = request.get_json()
        
        if not data or not data.get('command'):
            return jsonify({'error': '명령어가 필요합니다.'}), 400
        
        # 매니저에 프록시가 없으면 추가
        if proxy_id not in proxy_manager.clients:
            proxy_manager.add_proxy(proxy)
        
        result = proxy_manager.execute_command_on_proxy(proxy_id, data['command'])
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/monitoring/start', methods=['POST'])
def start_monitoring():
    """모니터링 시작"""
    try:
        # 프록시 목록 다시 로드
        proxy_manager.reload_proxies()
        
        # 모니터링 시작
        proxy_manager.start_monitoring()
        
        return jsonify({'message': '모니터링이 시작되었습니다.'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """모니터링 중지"""
    try:
        proxy_manager.stop_monitoring()
        return jsonify({'message': '모니터링이 중지되었습니다.'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/monitoring/status', methods=['GET'])
def get_monitoring_status():
    """모니터링 상태 조회"""
    try:
        status = proxy_manager.get_monitoring_status()
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500