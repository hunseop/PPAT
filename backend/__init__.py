"""Unified platform module combining core, monitoring_module, and proxy_module."""

from .proxy_client import ProxyClient
from .proxy_manager import ProxyManager, proxy_manager
from .monitoring import ProxyMonitor
from .services import DeviceManager, device_manager, MonitoringService, monitoring_service
from . import utils

__all__ = [
    'ProxyClient',
    'ProxyManager',
    'proxy_manager',
    'ProxyMonitor',
    'DeviceManager',
    'device_manager',
    'MonitoringService',
    'monitoring_service',
    'utils',
]