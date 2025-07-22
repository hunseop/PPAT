"""모니터링 API"""

from flask import Blueprint, request, jsonify
from flask_socketio import emit
from models import ProxyServer, ResourceStat, SessionInfo, db
from datetime import datetime, timedelta
import threading
import time
import random

monitoring_bp = Blueprint('monitoring', __name__)

# 모니터링 상태 관리
monitoring_status = {
    'active': False,
    'interval': 5,  # 초
    'thread': None
}

def generate_mock_data(proxy_id):
    """테스트용 모의 데이터 생성"""
    return {
        'cpu_usage': round(random.uniform(10, 90), 2),
        'memory_usage': round(random.uniform(20, 80), 2),
        'disk_usage': round(random.uniform(30, 70), 2),
        'network_in': round(random.uniform(100, 1000), 2),
        'network_out': round(random.uniform(50, 500), 2),
        'session_count': random.randint(10, 100),
        'status': random.choice(['online', 'online', 'online', 'warning'])
    }

def monitoring_worker():
    """백그라운드 모니터링 작업"""
    from app import socketio
    
    while monitoring_status['active']:
        try:
            # 모든 활성 프록시에 대해 데이터 수집
            active_proxies = ProxyServer.query.filter_by(is_active=True).all()
            
            for proxy in active_proxies:
                # 실제 환경에서는 monitoring_module을 사용
                mock_data = generate_mock_data(proxy.id)
                
                # 데이터베이스에 저장
                stat = ResourceStat(
                    proxy_id=proxy.id,
                    cpu_usage=mock_data['cpu_usage'],
                    memory_usage=mock_data['memory_usage'],
                    disk_usage=mock_data['disk_usage'],
                    network_in=mock_data['network_in'],
                    network_out=mock_data['network_out'],
                    session_count=mock_data['session_count'],
                    status=mock_data['status']
                )
                db.session.add(stat)
                
                # 실시간 데이터 전송
                socketio.emit('resource_update', {
                    'proxy_id': proxy.id,
                    'proxy_name': proxy.name,
                    'data': mock_data,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            db.session.commit()
            
        except Exception as e:
            print(f"Monitoring error: {e}")
            db.session.rollback()
        
        time.sleep(monitoring_status['interval'])

@monitoring_bp.route('/monitoring/start', methods=['POST'])
def start_monitoring():
    """모니터링 시작"""
    if monitoring_status['active']:
        return jsonify({'error': 'Monitoring already active'}), 400
    
    monitoring_status['active'] = True
    monitoring_status['thread'] = threading.Thread(target=monitoring_worker, daemon=True)
    monitoring_status['thread'].start()
    
    return jsonify({'message': 'Monitoring started', 'interval': monitoring_status['interval']})

@monitoring_bp.route('/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """모니터링 중지"""
    if not monitoring_status['active']:
        return jsonify({'error': 'Monitoring not active'}), 400
    
    monitoring_status['active'] = False
    
    return jsonify({'message': 'Monitoring stopped'})

@monitoring_bp.route('/monitoring/status', methods=['GET'])
def get_monitoring_status():
    """모니터링 상태 조회"""
    return jsonify({
        'active': monitoring_status['active'],
        'interval': monitoring_status['interval']
    })

@monitoring_bp.route('/monitoring/interval', methods=['PUT'])
def set_monitoring_interval():
    """모니터링 간격 설정"""
    data = request.get_json()
    interval = data.get('interval', 5)
    
    if interval < 1 or interval > 60:
        return jsonify({'error': 'Interval must be between 1 and 60 seconds'}), 400
    
    monitoring_status['interval'] = interval
    return jsonify({'message': 'Interval updated', 'interval': interval})

@monitoring_bp.route('/monitoring/resources', methods=['GET'])
def get_resources():
    """리소스 사용률 조회"""
    group_id = request.args.get('group_id', type=int)
    proxy_id = request.args.get('proxy_id', type=int)
    hours = request.args.get('hours', default=1, type=int)
    
    # 시간 범위 설정
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    # 쿼리 구성
    query = ResourceStat.query.filter(
        ResourceStat.timestamp >= start_time,
        ResourceStat.timestamp <= end_time
    )
    
    if proxy_id:
        query = query.filter_by(proxy_id=proxy_id)
    elif group_id:
        # 그룹에 속한 프록시들의 데이터
        proxy_ids = [p.id for p in ProxyServer.query.filter_by(group_id=group_id).all()]
        query = query.filter(ResourceStat.proxy_id.in_(proxy_ids))
    
    # 최신 순으로 정렬
    stats = query.order_by(ResourceStat.timestamp.desc()).limit(1000).all()
    
    return jsonify([stat.to_dict() for stat in stats])

@monitoring_bp.route('/monitoring/resources/latest', methods=['GET'])
def get_latest_resources():
    """최신 리소스 사용률 조회"""
    group_id = request.args.get('group_id', type=int)
    
    # 서브쿼리로 각 프록시의 최신 데이터 타임스탬프 조회
    latest_subquery = db.session.query(
        ResourceStat.proxy_id,
        db.func.max(ResourceStat.timestamp).label('latest_time')
    ).group_by(ResourceStat.proxy_id).subquery()
    
    # 최신 데이터 조회
    query = db.session.query(ResourceStat).join(
        latest_subquery,
        db.and_(
            ResourceStat.proxy_id == latest_subquery.c.proxy_id,
            ResourceStat.timestamp == latest_subquery.c.latest_time
        )
    )
    
    if group_id:
        # 그룹에 속한 프록시들만 필터링
        proxy_ids = [p.id for p in ProxyServer.query.filter_by(group_id=group_id).all()]
        query = query.filter(ResourceStat.proxy_id.in_(proxy_ids))
    
    stats = query.all()
    return jsonify([stat.to_dict() for stat in stats])

@monitoring_bp.route('/monitoring/sessions', methods=['GET'])
def get_sessions():
    """세션 정보 조회"""
    proxy_id = request.args.get('proxy_id', type=int)
    search = request.args.get('search', '')
    limit = request.args.get('limit', default=100, type=int)
    
    query = SessionInfo.query
    
    if proxy_id:
        query = query.filter_by(proxy_id=proxy_id)
    
    if search:
        # IP, 사용자명, URL에서 검색
        search_filter = db.or_(
            SessionInfo.client_ip.contains(search),
            SessionInfo.username.contains(search),
            SessionInfo.url.contains(search)
        )
        query = query.filter(search_filter)
    
    sessions = query.order_by(SessionInfo.timestamp.desc()).limit(limit).all()
    return jsonify([session.to_dict() for session in sessions])

@monitoring_bp.route('/monitoring/sessions/stats', methods=['GET'])
def get_session_stats():
    """세션 통계 조회"""
    # IP별 세션 수
    ip_stats = db.session.query(
        SessionInfo.client_ip,
        db.func.count(SessionInfo.id).label('count')
    ).group_by(SessionInfo.client_ip).order_by(db.desc('count')).limit(10).all()
    
    # 프록시별 세션 수
    proxy_stats = db.session.query(
        ProxyServer.name,
        db.func.count(SessionInfo.id).label('count')
    ).join(SessionInfo).group_by(ProxyServer.name).order_by(db.desc('count')).all()
    
    # URL별 세션 수 (도메인만 추출)
    url_stats = db.session.query(
        SessionInfo.url,
        db.func.count(SessionInfo.id).label('count')
    ).group_by(SessionInfo.url).order_by(db.desc('count')).limit(10).all()
    
    return jsonify({
        'by_ip': [{'ip': ip, 'count': count} for ip, count in ip_stats],
        'by_proxy': [{'proxy': name, 'count': count} for name, count in proxy_stats],
        'by_url': [{'url': url, 'count': count} for url, count in url_stats]
    })

@monitoring_bp.route('/monitoring/thresholds', methods=['GET'])
def get_thresholds():
    """임계값 조회"""
    # 기본 임계값 반환 (실제로는 설정에서 관리)
    return jsonify({
        'cpu': 80.0,
        'memory': 85.0,
        'disk': 90.0,
        'network_in': 1000.0,
        'network_out': 1000.0
    })

@monitoring_bp.route('/monitoring/thresholds', methods=['PUT'])
def set_thresholds():
    """임계값 설정"""
    data = request.get_json()
    
    # 실제로는 데이터베이스나 설정 파일에 저장
    # 여기서는 간단한 응답만 반환
    return jsonify({
        'message': 'Thresholds updated',
        'thresholds': data
    })