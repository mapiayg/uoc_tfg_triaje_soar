"""
tests/conftest.py
Verificación de conectividad con la VM antes de ejecutar tests de integración.
"""

import os
import socket
import pytest
from dotenv import load_dotenv

load_dotenv()

FORTI_HOST = os.getenv("FORTI_HOST", "192.168.75.2")


def _vm_is_reachable():
    """Comprueba si la VM responde en el puerto 443."""
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((FORTI_HOST, 443))
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


requires_vm = pytest.mark.skipif(
    not _vm_is_reachable(),
    reason=f"FortiOS VM no accesible en {FORTI_HOST}:443 — arranca la VM para ejecutar tests de integración"
)
