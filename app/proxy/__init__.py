from flask import Blueprint

bp = Blueprint('proxy', __name__)

from . import routes  # noqa
