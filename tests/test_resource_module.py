"""
tests/test_resource_module.py
Tests del módulo de diagnóstico de saturación contra la API real de FortiOS.

Requiere la VM en 192.168.75.2 y el fichero .env configurado con FORTI_TOKEN.
"""

import pytest
from dotenv import load_dotenv

from src.diagnostics.resources import ResourceDiagnostic
from tests.conftest import requires_vm

load_dotenv()

pytestmark = requires_vm


@pytest.fixture(scope="module")
def resource_alert():
    return {
        "incident_id": "INC-20260412-RES001",
        "alert_type": "resource_saturation",
        "device_ip": "192.168.75.2",
        "device_hostname": "FORTI-LAB",
        "customer_id": "LAB",
        "timestamp": "2026-04-12T10:00:00Z",
        "resource_type": "cpu",
        "threshold_value": 95,
    }


@pytest.fixture(scope="module")
def resource_result(resource_alert):
    """Resultado de un diagnóstico de saturación real contra la VM."""
    diag = ResourceDiagnostic()
    return diag.run(resource_alert)


def test_result_structure(resource_result):
    """El resultado contiene todos los campos requeridos."""
    required_keys = {
        "diagnostic_type",
        "resource_type",
        "threshold_value",
        "diagnostic_summary",
        "raw_data",
        "processing_time_ms",
        "errors",
    }
    assert required_keys.issubset(resource_result.keys())


def test_diagnostic_type(resource_result):
    assert resource_result["diagnostic_type"] == "resource_saturation"


def test_resource_type_in_result(resource_result, resource_alert):
    assert resource_result["resource_type"] == resource_alert["resource_type"]


def test_diagnostic_summary_not_empty(resource_result):
    assert isinstance(resource_result["diagnostic_summary"], str)
    assert len(resource_result["diagnostic_summary"]) > 0


def test_processing_time_captured(resource_result):
    assert isinstance(resource_result["processing_time_ms"], int)
    assert resource_result["processing_time_ms"] >= 0


def test_diagnostic_completes(resource_result):
    """El diagnóstico se completa sin lanzar excepción."""
    assert resource_result["processing_time_ms"] >= 0
    assert isinstance(resource_result["errors"], list)


def test_raw_data_keys_present(resource_result):
    """raw_data contiene las claves esperadas."""
    assert "resource_usage" in resource_result["raw_data"]
    assert "session_count" in resource_result["raw_data"]
    assert "interfaces" in resource_result["raw_data"]
