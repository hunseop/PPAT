"""프록시 관리 API"""

from flask import Blueprint, request, jsonify
from models import db, ProxyGroup, ProxyServer
from proxy_module.proxy_manager import proxy_manager

proxy_bp = Blueprint('proxy', __name__)

# ==================== 프록시 그룹 관리 ====================

@proxy_bp.route('/groups', methods=['GET'])
def get_groups():
    """모든 프록시 그룹 조회"""
    try:
        groups = ProxyGroup.query.all()
        return jsonify([group.to_dict() for group in groups])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/groups', methods=['POST'])
def create_group():
    """새 프록시 그룹 생성"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        if not data.get('name'):
            return jsonify({'error': '그룹 이름은 필수입니다.'}), 400
        
        # 중복 이름 검사
        if ProxyGroup.query.filter_by(name=data['name']).first():
            return jsonify({'error': '이미 존재하는 그룹 이름입니다.'}), 400
        
        group = ProxyGroup(
            name=data['name'],
            description=data.get('description', '')
        )
        
        db.session.add(group)
        db.session.commit()
        
        return jsonify(group.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    """프록시 그룹 수정"""
    try:
        group = ProxyGroup.query.get_or_404(group_id)
        data = request.get_json()
        
        # 이름 중복 검사 (자기 자신 제외)
        if data.get('name') and data['name'] != group.name:
            if ProxyGroup.query.filter_by(name=data['name']).first():
                return jsonify({'error': '이미 존재하는 그룹 이름입니다.'}), 400
        
        if data.get('name'):
            group.name = data['name']
        if 'description' in data:
            group.description = data['description']
        
        db.session.commit()
        return jsonify(group.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """프록시 그룹 삭제"""
    try:
        group = ProxyGroup.query.get_or_404(group_id)
        
        # 기본 그룹은 삭제 불가
        if group.name == '기본그룹':
            return jsonify({'error': '기본 그룹은 삭제할 수 없습니다.'}), 400
        
        # 해당 그룹에 속한 프록시가 있는지 확인
        proxy_count = ProxyServer.query.filter_by(group_id=group_id).count()
        if proxy_count > 0:
            return jsonify({'error': f'그룹에 {proxy_count}개의 프록시가 있어 삭제할 수 없습니다.'}), 400
        
        db.session.delete(group)
        db.session.commit()
        
        return jsonify({'message': '그룹이 삭제되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== 프록시 서버 관리 ====================

@proxy_bp.route('/proxies', methods=['GET'])
def get_proxies():
    """모든 프록시 서버 조회"""
    try:
        proxies = ProxyServer.query.all()
        return jsonify([proxy.to_dict() for proxy in proxies])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies', methods=['POST'])
def create_proxy():
    """새 프록시 서버 생성"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        if not data.get('name') or not data.get('host'):
            return jsonify({'error': '이름과 호스트는 필수입니다.'}), 400
        
        # 그룹 ID 검증
        group_id = data.get('group_id')
        if group_id:
            if not ProxyGroup.query.get(group_id):
                return jsonify({'error': '존재하지 않는 그룹입니다.'}), 400
        else:
            # 기본 그룹 사용
            default_group = ProxyGroup.query.filter_by(name='기본그룹').first()
            if not default_group:
                return jsonify({'error': '기본 그룹을 찾을 수 없습니다.'}), 500
            group_id = default_group.id
        
        proxy = ProxyServer(
            name=data['name'],
            host=data['host'],
            ssh_port=data.get('ssh_port', 22),
            username=data.get('username', 'root'),
            password=data.get('password', '123456'),
            description=data.get('description', ''),
            group_id=group_id,
            is_active=False  # 최초 등록 시 오프라인 상태
        )
        
        db.session.add(proxy)
        db.session.commit()
        
        # 프록시 매니저에 추가
        proxy_manager.add_proxy(proxy.id, proxy.host, proxy.ssh_port, proxy.username, proxy.password)
        
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
        
        # 그룹 ID 검증
        if data.get('group_id'):
            if not ProxyGroup.query.get(data['group_id']):
                return jsonify({'error': '존재하지 않는 그룹입니다.'}), 400
            proxy.group_id = data['group_id']
        
        if data.get('name'):
            proxy.name = data['name']
        if data.get('host'):
            proxy.host = data['host']
        if data.get('ssh_port'):
            proxy.ssh_port = data['ssh_port']
        if data.get('username'):
            proxy.username = data['username']
        if data.get('password'):
            proxy.password = data['password']
        if 'description' in data:
            proxy.description = data['description']
        if 'is_active' in data:
            proxy.is_active = data['is_active']
        
        db.session.commit()
        
        # 프록시 매니저 업데이트
        proxy_manager.remove_proxy(proxy_id)
        proxy_manager.add_proxy(proxy_id, proxy.host, proxy.ssh_port, proxy.username, proxy.password)
        
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
        
        return jsonify({'message': '프록시가 삭제되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>/test', methods=['POST'])
def test_proxy_connection(proxy_id):
    """프록시 연결 테스트"""
    try:
        result = proxy_manager.test_proxy_connection(proxy_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== 프록시 모니터링 ====================

@proxy_bp.route('/proxies/<int:proxy_id>/info', methods=['GET'])
def get_proxy_info(proxy_id):
    """프록시 시스템 정보 조회"""
    try:
        info = proxy_manager.get_proxy_system_info(proxy_id)
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>/resources', methods=['GET'])
def get_proxy_resources(proxy_id):
    """프록시 리소스 사용량 조회"""
    try:
        resources = proxy_manager.get_proxy_resource_usage(proxy_id)
        return jsonify(resources)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>/services', methods=['GET'])
def get_proxy_services(proxy_id):
    """프록시 서비스 상태 조회"""
    try:
        services = proxy_manager.check_proxy_services(proxy_id)
        return jsonify(services)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>/command', methods=['POST'])
def execute_proxy_command(proxy_id):
    """프록시에서 명령어 실행"""
    try:
        data = request.get_json()
        command = data.get('command')
        
        if not command:
            return jsonify({'error': '명령어가 필요합니다.'}), 400
        
        result = proxy_manager.execute_command_on_proxy(proxy_id, command)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== 모니터링 제어 ====================

@proxy_bp.route('/monitoring/start', methods=['POST'])
def start_monitoring():
    """자동 모니터링 시작"""
    try:
        proxy_manager.start_monitoring()
        return jsonify({'message': '모니터링이 시작되었습니다.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """자동 모니터링 중지"""
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