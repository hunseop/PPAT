from flask import request, jsonify
from threading import Thread, Event
from time import sleep
from . import bp
from ppat_db.proxy_db import ProxyServer, ResourceStat, SessionInfo
from ppat_db.database import db
from monitoring_module.resource import ResourceMonitor
from monitoring_module.session import SessionManager
from app.extensions import socketio
import os

monitor_interval = 60
monitor_thread = None
stop_event = Event()


def _limit_db_size():
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'instance', 'ppat.db')
    if os.path.exists(db_path) and os.path.getsize(db_path) > 100 * 1024 * 1024:
        while os.path.getsize(db_path) > 100 * 1024 * 1024:
            oldest = ResourceStat.query.order_by(ResourceStat.id.asc()).first()
            if not oldest:
                break
            db.session.delete(oldest)
            db.session.commit()


def _collect_loop():
    while not stop_event.is_set():
        servers = ProxyServer.query.filter_by(enabled=True).all()
        for server in servers:
            mon = ResourceMonitor(server.ip_address, server.ssh_username, server.ssh_password)
            data = mon.get_resource_data()
            stat = ResourceStat(
                proxy_id=server.id,
                cpu=float(data.get('cpu', -1)),
                memory=float(data.get('memory', -1)),
                unique_clients=int(data.get('uc', 0)),
                cc=int(data.get('cc', 0)),
                cs=int(data.get('cs', 0)),
                http=int(data.get('http', 0)),
                https=int(data.get('https', 0)),
                ftp=int(data.get('ftp', 0)),
            )
            db.session.add(stat)
            db.session.commit()
            socketio.emit('resource_update', {'server_id': server.id, **data})
            _limit_db_size()
        stop_event.wait(monitor_interval)


@bp.route('/start', methods=['POST'])
def start_monitoring():
    global monitor_thread
    if monitor_thread and monitor_thread.is_alive():
        return jsonify({'status': 'running'})
    stop_event.clear()
    monitor_thread = Thread(target=_collect_loop, daemon=True)
    monitor_thread.start()
    return jsonify({'status': 'started'})


@bp.route('/stop', methods=['POST'])
def stop_monitoring():
    stop_event.set()
    return jsonify({'status': 'stopped'})


@bp.route('/interval', methods=['POST'])
def set_interval():
    global monitor_interval
    data = request.get_json() or {}
    interval = data.get('interval', monitor_interval)
    try:
        monitor_interval = max(1, int(interval))
    except (ValueError, TypeError):
        pass
    return jsonify({'interval': monitor_interval})


@bp.route('/resources', methods=['GET'])
def get_resources():
    group_id = request.args.get('group', type=int)
    proxy_id = request.args.get('proxy', type=int)
    query = ResourceStat.query
    if proxy_id:
        query = query.filter_by(proxy_id=proxy_id)
    elif group_id:
        query = query.join(ProxyServer).filter(ProxyServer.group_id == group_id)
    stats = query.order_by(ResourceStat.timestamp.desc()).limit(100).all()
    return jsonify([
        {
            'id': s.id,
            'proxy_id': s.proxy_id,
            'timestamp': s.timestamp.isoformat(),
            'cpu': s.cpu,
            'memory': s.memory,
            'unique_clients': s.unique_clients,
            'cc': s.cc,
            'cs': s.cs,
            'http': s.http,
            'https': s.https,
            'ftp': s.ftp,
        }
        for s in stats
    ])


@bp.route('/sessions', methods=['GET'])
def sessions():
    proxy_id = request.args.get('proxy', type=int)
    search = request.args.get('search')
    if not proxy_id:
        server = ProxyServer.query.first()
    else:
        server = ProxyServer.query.get_or_404(proxy_id)
    if not server:
        return jsonify([])
    manager = SessionManager(server.ip_address, server.ssh_username, server.ssh_password)
    df = manager.get_session()
    if search:
        df = manager.search_session(search, df)
    records = df.to_dict(orient='records')
    for row in records:
        rec = SessionInfo(proxy_id=server.id, data=row)
        db.session.add(rec)
    db.session.commit()
    socketio.emit('session_update', records)
    return jsonify(records)


@bp.route('/sessions/<int:session_id>', methods=['GET'])
def session_detail(session_id):
    info = SessionInfo.query.get_or_404(session_id)
    return jsonify({'id': info.id, 'proxy_id': info.proxy_id, 'timestamp': info.timestamp.isoformat(), 'data': info.data})

