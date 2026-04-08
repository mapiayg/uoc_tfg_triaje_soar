# src/severity.py
# Clasificador de severidad con reglas deterministas.
# VPN Down siempre es CRITICAL (pérdida de conectividad entre sedes).
# Saturación de recursos depende del umbral superado y el tipo de recurso.
from enum import Enum


class Severity(str, Enum):
    CRITICAL = 'critical'
    WARNING = 'warning'
    INFO = 'info'


def classify_vpn(alert: dict, diagnostic: dict) -> Severity:
    """Caída de túnel VPN — siempre CRITICAL (pérdida de conectividad)."""
    return Severity.CRITICAL


def classify_resource(alert: dict, diagnostic: dict) -> Severity:
    """Saturación de recursos — depende del tipo de recurso y el umbral."""
    threshold = float(alert.get('threshold_value', 0))
    resource_type = alert.get('resource_type', 'cpu')

    if resource_type == 'cpu':
        if threshold >= 90:
            return Severity.CRITICAL
        elif threshold >= 70:
            return Severity.WARNING
        return Severity.INFO

    if resource_type == 'mem':
        if threshold >= 95:
            return Severity.CRITICAL
        elif threshold >= 80:
            return Severity.WARNING
        return Severity.INFO

    return Severity.WARNING  # Recurso no clasificado → WARNING por defecto


CLASSIFIERS = {
    'vpn_down': classify_vpn,
    'resource_saturation': classify_resource,
}


def classify(alert_type: str, alert: dict, diagnostic: dict) -> Severity:
    """Punto de entrada: devuelve la severidad para el tipo de alerta dado."""
    classifier = CLASSIFIERS.get(alert_type)
    if not classifier:
        return Severity.INFO
    return classifier(alert, diagnostic)