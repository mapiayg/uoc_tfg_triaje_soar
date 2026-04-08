"""
tests/test_severity.py
Tests unitarios del clasificador de severidad.

Verifica que las reglas deterministas del clasificador son correctas:
- VPN Down siempre CRITICAL
- CPU: >=90% CRITICAL, >=70% WARNING, <70% INFO
- MEM: >=95% CRITICAL, >=80% WARNING, <80% INFO
- Tipo de alerta desconocido → INFO
- Tipo de recurso desconocido → WARNING
"""

import pytest
from src.severity import classify, Severity


# ---------------------------------------------------------------------------
# Helpers de alerta
# ---------------------------------------------------------------------------

def _vpn_alert():
    return {
        'alert_type': 'vpn_down',
        'device_ip': '10.10.1.1',
        'incident_id': 'INC-TEST-SEV-001',
    }


def _cpu_alert(threshold: float):
    return {
        'alert_type': 'resource_saturation',
        'resource_type': 'cpu',
        'threshold_value': threshold,
        'incident_id': 'INC-TEST-SEV-002',
    }


def _mem_alert(threshold: float):
    return {
        'alert_type': 'resource_saturation',
        'resource_type': 'mem',
        'threshold_value': threshold,
        'incident_id': 'INC-TEST-SEV-003',
    }


# ---------------------------------------------------------------------------
# Tests VPN
# ---------------------------------------------------------------------------

def test_vpn_always_critical():
    """Caída de VPN siempre debe ser CRITICAL independientemente del diagnóstico."""
    sev = classify('vpn_down', _vpn_alert(), {})
    assert sev == Severity.CRITICAL


def test_severity_is_string():
    """Severity hereda de str — el valor debe comparar directamente con 'critical'."""
    sev = classify('vpn_down', _vpn_alert(), {})
    assert sev == 'critical'


# ---------------------------------------------------------------------------
# Tests CPU
# ---------------------------------------------------------------------------

def test_cpu_critical_at_90():
    sev = classify('resource_saturation', _cpu_alert(90), {})
    assert sev == Severity.CRITICAL


def test_cpu_warning_at_75():
    sev = classify('resource_saturation', _cpu_alert(75), {})
    assert sev == Severity.WARNING


def test_cpu_info_at_50():
    sev = classify('resource_saturation', _cpu_alert(50), {})
    assert sev == Severity.INFO


# ---------------------------------------------------------------------------
# Tests Memoria
# ---------------------------------------------------------------------------

def test_mem_critical_at_95():
    sev = classify('resource_saturation', _mem_alert(95), {})
    assert sev == Severity.CRITICAL


def test_mem_warning_at_85():
    sev = classify('resource_saturation', _mem_alert(85), {})
    assert sev == Severity.WARNING


def test_mem_info_at_60():
    sev = classify('resource_saturation', _mem_alert(60), {})
    assert sev == Severity.INFO


# ---------------------------------------------------------------------------
# Tests tipos desconocidos
# ---------------------------------------------------------------------------

def test_unknown_alert_type():
    """Tipo de alerta no soportado devuelve INFO."""
    alert = {'alert_type': 'tipo_desconocido', 'incident_id': 'INC-X'}
    sev = classify('tipo_desconocido', alert, {})
    assert sev == Severity.INFO


def test_unknown_resource_type():
    """Tipo de recurso no clasificado devuelve WARNING."""
    alert = {
        'alert_type': 'resource_saturation',
        'resource_type': 'disco',
        'threshold_value': 80,
        'incident_id': 'INC-X',
    }
    sev = classify('resource_saturation', alert, {})
    assert sev == Severity.WARNING