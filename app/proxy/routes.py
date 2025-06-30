from flask import request, jsonify
from . import bp
from ppat_db.proxy_db import ProxyGroup, ProxyServer
from ppat_db.database import db


@bp.route('/groups', methods=['GET', 'POST'])
def groups():
    if request.method == 'GET':
        groups = ProxyGroup.query.all()
        return jsonify([
            {
                'id': g.id,
                'name': g.name,
                'description': g.description,
                'proxy_count': len(g.proxies),
            }
            for g in groups
        ])
    data = request.get_json() or {}
    group = ProxyGroup(name=data.get('name'), description=data.get('description', ''))
    db.session.add(group)
    db.session.commit()
    return jsonify({'id': group.id, 'name': group.name, 'description': group.description}), 201


@bp.route('/groups/<int:group_id>', methods=['GET', 'PUT', 'DELETE'])
def group_detail(group_id):
    group = ProxyGroup.query.get_or_404(group_id)
    if request.method == 'GET':
        return jsonify({'id': group.id, 'name': group.name, 'description': group.description})
    if request.method == 'PUT':
        data = request.get_json() or {}
        group.name = data.get('name', group.name)
        group.description = data.get('description', group.description)
        db.session.commit()
        return jsonify({'id': group.id, 'name': group.name, 'description': group.description})
    db.session.delete(group)
    db.session.commit()
    return '', 204


@bp.route('/servers', methods=['GET', 'POST'])
def servers():
    if request.method == 'GET':
        query = ProxyServer.query
        group = request.args.get('group', type=int)
        if group:
            query = query.filter_by(group_id=group)
        is_main = request.args.get('is_main')
        if is_main is not None:
            query = query.filter_by(is_main=is_main.lower() == 'true')
        servers = query.all()
        return jsonify([
            {
                'id': s.id,
                'name': s.name,
                'ip_address': s.ip_address,
                'port': s.port,
                'enabled': s.enabled,
                'is_main': s.is_main,
                'group_id': s.group_id,
            }
            for s in servers
        ])
    data = request.get_json() or {}
    server = ProxyServer(
        name=data.get('name'),
        ip_address=data.get('ip_address'),
        port=data.get('port'),
        description=data.get('description'),
        is_main=data.get('is_main', False),
        enabled=data.get('enabled', True),
        group_id=data.get('group_id'),
    )
    db.session.add(server)
    db.session.commit()
    return jsonify({'id': server.id}), 201


@bp.route('/servers/<int:server_id>', methods=['PUT', 'DELETE'])
def server_detail(server_id):
    server = ProxyServer.query.get_or_404(server_id)
    if request.method == 'PUT':
        data = request.get_json() or {}
        server.name = data.get('name', server.name)
        server.ip_address = data.get('ip_address', server.ip_address)
        server.port = data.get('port', server.port)
        server.description = data.get('description', server.description)
        server.is_main = data.get('is_main', server.is_main)
        server.enabled = data.get('enabled', server.enabled)
        server.group_id = data.get('group_id', server.group_id)
        db.session.commit()
        return jsonify({'id': server.id})
    db.session.delete(server)
    db.session.commit()
    return '', 204
