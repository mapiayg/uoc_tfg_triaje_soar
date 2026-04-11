"""
tests/test_router.py
Tests de integración del pipeline completo contra la API real de FortiOS.

Verifica el pipeline completo:
  alerta VPN → router → VPNDiagnostic (API real) → severity → output → ticket JSON

Requiere la VM en 192.168.75.2 y el fichero .env configurado con FORTI_TOKEN.
"""

import json
import pytest
from dotenv import load_dotenv

from src.router import route_alert
from tests.conftest import requires_vm

load_dotenv()

pytestmark = requires_vm


# ---------------------------------------------------------------------------
# Fixture: una sola llamada al pipeline para todos los tests
# ---------------------------------------------------------------------------

_cached_ticket = None
_cached_output_dir = None


@pytest.fixture
def tmp_output(tmp_path, monkeypatch):
    """Redirige OUTPUT_DIR a un directorio temporal."""
    monkeypatch.setenv('OUTPUT_DIR', str(tmp_path))
    return tmp_path


@pytest.fixture
def ticket(tmp_output):
    """Ticket generado por el pipeline completo — cacheado para evitar rate limit."""
    global _cached_ticket, _cached_output_dir
    if _cached_ticket is None:
        _cached_ticket = route_alert({
            'incident_id': 'INC-TEST-ROUTER-001',
            'alert_type': 'vpn_down',
            'device_ip': '192.168.75.2',
            'device_hostname': 'FORTI-LAB',
            'customer_id': 'LAB',
            'timestamp': '2026-04-07T10:00:00Z',
            'vpn_tunnel_name': 'VPN-SEDE-CENTRAL-MADRID',
        })
        _cached_output_dir = tmp_output
    return _cached_ticket


@pytest.fixture
def output_dir(ticket):
    return _cached_output_dir


# ---------------------------------------------------------------------------
# Tests del ticket
# ---------------------------------------------------------------------------

def test_ticket_structure(ticket):
    required = {'incident_id', 'severity', 'alert_type', 'device',
                 'diagnostic_summary', 'recommended_action', 'timestamp'}
    assert required.issubset(ticket.keys())


def test_vpn_severity_is_critical(ticket):
    assert ticket['severity'] == 'critical'


def test_incident_id_propagated(ticket):
    assert ticket['incident_id'] == 'INC-TEST-ROUTER-001'


def test_device_info(ticket):
    assert ticket['device']['hostname'] == 'FORTI-LAB'
    assert ticket['device']['ip'] == '192.168.75.2'


# ---------------------------------------------------------------------------
# Tests de ficheros generados
# ---------------------------------------------------------------------------

def test_json_file_created(output_dir):
    assert (output_dir / "INC-TEST-ROUTER-001.json").exists()


def test_txt_file_created(output_dir):
    assert (output_dir / "INC-TEST-ROUTER-001.txt").exists()


# ---------------------------------------------------------------------------
# Tests del pipeline de saturación (caso de uso 2)
# ---------------------------------------------------------------------------

_cached_resource_ticket = None


@pytest.fixture
def resource_ticket(tmp_output):
    """Ticket de saturación generado por el pipeline completo."""
    global _cached_resource_ticket
    if _cached_resource_ticket is None:
        _cached_resource_ticket = route_alert({
            'incident_id': 'INC-TEST-ROUTER-RES',
            'alert_type': 'resource_saturation',
            'device_ip': '192.168.75.2',
            'device_hostname': 'FORTI-LAB',
            'customer_id': 'LAB',
            'timestamp': '2026-04-07T10:00:00Z',
            'resource_type': 'cpu',
            'threshold_value': 95,
        })
    return _cached_resource_ticket


def test_resource_ticket_structure(resource_ticket):
    required = {'incident_id', 'severity', 'alert_type', 'device',
                 'diagnostic_summary', 'recommended_action', 'timestamp'}
    assert required.issubset(resource_ticket.keys())


def test_resource_severity_is_critical(resource_ticket):
    assert resource_ticket['severity'] == 'critical'


def test_resource_alert_type(resource_ticket):
    assert resource_ticket['alert_type'] == 'resource_saturation'


# ---------------------------------------------------------------------------
# Test de error
# ---------------------------------------------------------------------------

def test_unsupported_alert_type_raises(tmp_output):
    alert = {
        'incident_id': 'INC-TEST-ERR',
        'alert_type': 'tipo_no_soportado',
        'device_ip': '10.0.0.1',
        'device_hostname': 'FW-TEST',
        'customer_id': 'TEST',
        'timestamp': '2026-04-07T10:00:00Z',
    }
    with pytest.raises(ValueError, match='alert_type no soportado'):
        route_alert(alert)
