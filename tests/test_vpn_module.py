"""
tests/test_vpn_module.py
Tests del módulo de diagnóstico VPN contra la API real de FortiOS.

Requiere la VM en 192.168.75.2 y el fichero .env configurado con FORTI_TOKEN.
"""

import pytest
from dotenv import load_dotenv

from src.diagnostics.vpn import VPNDiagnostic
from tests.conftest import requires_vm

load_dotenv()

pytestmark = requires_vm


# ---------------------------------------------------------------------------
# Fixture: alerta VPN estándar
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def vpn_alert():
    return {
        "incident_id": "INC-20260330-VPN001",
        "alert_type": "vpn_down",
        "device_ip": "192.168.75.2",
        "device_hostname": "FORTI-LAB",
        "customer_id": "LAB",
        "timestamp": "2026-03-30T10:00:00Z",
        "vpn_tunnel_name": "VPN-SEDE-CENTRAL-MADRID",
    }


@pytest.fixture(scope="module")
def vpn_result(vpn_alert):
    """Resultado de un diagnóstico VPN real contra la VM — se ejecuta una sola vez."""
    diag = VPNDiagnostic()
    return diag.run(vpn_alert)


# ---------------------------------------------------------------------------
# Tests del resultado
# ---------------------------------------------------------------------------

def test_result_structure(vpn_result):
    """El resultado contiene todos los campos requeridos."""
    required_keys = {
        "diagnostic_type",
        "tunnel_name",
        "diagnostic_summary",
        "raw_data",
        "processing_time_ms",
        "errors",
    }
    assert required_keys.issubset(vpn_result.keys())


def test_diagnostic_type(vpn_result):
    assert vpn_result["diagnostic_type"] == "vpn_down"


def test_tunnel_name_in_result(vpn_result, vpn_alert):
    assert vpn_result["tunnel_name"] == vpn_alert["vpn_tunnel_name"]


def test_diagnostic_summary_not_empty(vpn_result):
    assert isinstance(vpn_result["diagnostic_summary"], str)
    assert len(vpn_result["diagnostic_summary"]) > 0


def test_processing_time_captured(vpn_result):
    assert isinstance(vpn_result["processing_time_ms"], int)
    assert vpn_result["processing_time_ms"] >= 0


def test_diagnostic_completes(vpn_result):
    """El diagnóstico se completa sin lanzar excepción, incluso si la API
    devuelve errores (403, datos vacíos). El módulo captura los errores
    y genera un resultado válido igualmente."""
    assert vpn_result["processing_time_ms"] >= 0
    assert isinstance(vpn_result["errors"], list)


def test_raw_data_keys_present(vpn_result):
    """raw_data contiene las claves esperadas (pueden ser None si la API
    no responde o el lab no tiene túneles VPN configurados)."""
    assert "ipsec_tunnels" in vpn_result["raw_data"]
    assert "interfaces" in vpn_result["raw_data"]