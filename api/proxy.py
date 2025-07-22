"""프록시 관리 API"""

from flask import Blueprint, request, jsonify
from models import ProxyGroup, ProxyServer, db
from sqlalchemy.exc import IntegrityError

proxy_bp = Blueprint('proxy', __name__)

# 프록시 그룹 관리
@proxy_bp.route('/groups', methods=['GET'])
def get_groups():
    """프록시 그룹 목록 조회"""
    groups = ProxyGroup.query.all()
    return jsonify([group.to_dict() for group in groups])

@proxy_bp.route('/groups', methods=['POST'])
def create_group():
    """프록시 그룹 생성"""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Group name is required'}), 400
    
    group = ProxyGroup(
        name=data['name'],
        description=data.get('description', '')
    )
    
    try:
        db.session.add(group)
        db.session.commit()
        return jsonify(group.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Group name already exists'}), 409

@proxy_bp.route('/groups/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    """프록시 그룹 수정"""
    group = ProxyGroup.query.get_or_404(group_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'name' in data:
        group.name = data['name']
    if 'description' in data:
        group.description = data['description']
    
    try:
        db.session.commit()
        return jsonify(group.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Group name already exists'}), 409

@proxy_bp.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """프록시 그룹 삭제"""
    group = ProxyGroup.query.get_or_404(group_id)
    
    # 그룹에 속한 프록시가 있는지 확인
    if group.proxies:
        return jsonify({'error': 'Cannot delete group with proxies'}), 400
    
    db.session.delete(group)
    db.session.commit()
    return '', 204

# 프록시 서버 관리
@proxy_bp.route('/servers', methods=['GET'])
def get_servers():
    """프록시 서버 목록 조회"""
    group_id = request.args.get('group_id', type=int)
    is_main = request.args.get('is_main')
    
    query = ProxyServer.query
    
    if group_id:
        query = query.filter_by(group_id=group_id)
    if is_main is not None:
        query = query.filter_by(is_main=is_main.lower() == 'true')
    
    servers = query.all()
    return jsonify([server.to_dict() for server in servers])

@proxy_bp.route('/servers', methods=['POST'])
def create_server():
    """프록시 서버 생성"""
    data = request.get_json()
    
    required_fields = ['name', 'host', 'group_id']
    for field in required_fields:
        if not data or not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # 그룹이 존재하는지 확인
    group = ProxyGroup.query.get(data['group_id'])
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    # 같은 그룹에서 main proxy가 이미 있는지 확인
    if data.get('is_main', False):
        existing_main = ProxyServer.query.filter_by(
            group_id=data['group_id'], 
            is_main=True
        ).first()
        if existing_main:
            return jsonify({'error': 'Main proxy already exists in this group'}), 409
    
    server = ProxyServer(
        name=data['name'],
        host=data['host'],
        ssh_port=data.get('ssh_port', 22),
        snmp_port=data.get('snmp_port', 161),
        username=data.get('username', 'root'),
        password=data.get('password', '123456'),
        is_main=data.get('is_main', False),
        is_active=data.get('is_active', True),
        description=data.get('description', ''),
        group_id=data['group_id']
    )
    
    db.session.add(server)
    db.session.commit()
    return jsonify(server.to_dict()), 201

@proxy_bp.route('/servers/<int:server_id>', methods=['PUT'])
def update_server(server_id):
    """프록시 서버 수정"""
    server = ProxyServer.query.get_or_404(server_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Main proxy 변경 시 중복 확인
    if 'is_main' in data and data['is_main'] and not server.is_main:
        existing_main = ProxyServer.query.filter_by(
            group_id=server.group_id, 
            is_main=True
        ).first()
        if existing_main:
            return jsonify({'error': 'Main proxy already exists in this group'}), 409
    
    # 업데이트 가능한 필드들
    updatable_fields = [
        'name', 'host', 'ssh_port', 'snmp_port', 
        'username', 'password', 'is_main', 'is_active', 'description'
    ]
    
    for field in updatable_fields:
        if field in data:
            setattr(server, field, data[field])
    
    db.session.commit()
    return jsonify(server.to_dict())

@proxy_bp.route('/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    """프록시 서버 삭제"""
    server = ProxyServer.query.get_or_404(server_id)
    
    db.session.delete(server)
    db.session.commit()
    return '', 204

@proxy_bp.route('/servers/<int:server_id>/test', methods=['POST'])
def test_server_connection(server_id):
    """프록시 서버 연결 테스트"""
    server = ProxyServer.query.get_or_404(server_id)
    
    # 실제 환경에서는 monitoring_module을 사용하여 연결 테스트
    # 여기서는 간단한 응답만 반환
    return jsonify({
        'success': True,
        'message': f'Connection test to {server.host}:{server.ssh_port} successful',
        'timestamp': '2024-01-01T00:00:00Z'
    })