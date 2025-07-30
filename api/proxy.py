"""프록시 서버 관리 API"""

from flask import Blueprint, request, jsonify
from models import db, ProxyServer, ProxyGroup
import subprocess
import socket
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
        
        return jsonify(proxy.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@proxy_bp.route('/proxies/<int:proxy_id>', methods=['DELETE'])
def delete_proxy(proxy_id):
    """프록시 서버 삭제"""
    try:
        proxy = ProxyServer.query.get_or_404(proxy_id)
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
        
        # SSH 연결 테스트
        success = test_ssh_connection(proxy.host, proxy.ssh_port)
        
        # 상태 업데이트
        proxy.is_active = success
        proxy.updated_at = datetime.utcnow()
        db.session.commit()
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{proxy.host}:{proxy.ssh_port}에 성공적으로 연결되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'{proxy.host}:{proxy.ssh_port}에 연결할 수 없습니다.'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'연결 테스트 중 오류가 발생했습니다: {str(e)}'
        }), 500

def test_ssh_connection(host, port):
    """SSH 연결 테스트"""
    try:
        # 간단한 TCP 연결 테스트 (실제 SSH 인증은 하지 않음)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5초 타임아웃
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False