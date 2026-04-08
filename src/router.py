# src/router.py
# Dispatcher principal: selecciona el módulo de diagnóstico según el tipo de alerta,
# calcula la severidad y genera el ticket de salida.
# Sustituye el stub de semana 3.
from src.diagnostics.vpn import VPNDiagnostic
from src.diagnostics.resources import ResourceDiagnostic
from src.severity import classify
from src.output import generate_output
from src.logger_config import get_logger

logger = get_logger(__name__)

DIAGNOSTIC_MODULES = {
    'vpn_down': VPNDiagnostic,
    'resource_saturation': ResourceDiagnostic,
}


def route_alert(alert: dict) -> dict:
    """
    Selecciona el módulo de diagnóstico, ejecuta el playbook,
    clasifica la severidad y genera el ticket de salida.
    """
    alert_type = alert['alert_type']
    iid = alert['incident_id']

    DiagClass = DIAGNOSTIC_MODULES.get(alert_type)
    if not DiagClass:
        logger.error(
            f'Tipo de alerta no soportado: {alert_type}',
            extra={'incident_id': iid},
        )
        raise ValueError(f'alert_type no soportado: {alert_type}')

    diag = DiagClass()
    diagnostic_result = diag.run(alert)
    severity = classify(alert_type, alert, diagnostic_result)
    ticket = generate_output(alert, diagnostic_result, severity)

    logger.info(
        f'Ticket generado. Severidad: {severity}',
        extra={'incident_id': iid},
    )
    return ticket