# src/output.py
# Generador de salida dual: ticket JSON + texto plano legible.
# El JSON sigue la estructura del Anexo B (compatible ServiceNow).
# Los ficheros se guardan en OUTPUT_DIR (por defecto ./output/).
import json
import os
from datetime import datetime, timezone

from src.logger_config import get_logger
from src.severity import Severity

logger = get_logger(__name__)
OUTPUT_DIR = os.getenv('OUTPUT_DIR', './output')

RECOMMENDED_ACTIONS = {
    'vpn_down': (
        'Verificar conectividad con peer remoto. '
        'Revisar logs IKE en ambos extremos. '
        'Contactar a cliente para confirmar incidencia y coordinar restablecimiento del túnel.'
    ),
    'resource_saturation': (
        'Monitorizar tendencia de consumo. '
        'Identificar procesos o tráfico anómalo. '
        'Si CPU >95% sostenido, evaluar reinicio de proceso o escalado.'
    ),
}


def generate_output(alert: dict, diagnostic: dict, severity: Severity) -> dict:
    """
    Genera ticket JSON y fichero de texto plano en OUTPUT_DIR.
    Devuelve el diccionario del ticket.
    """
    output_dir = os.getenv('OUTPUT_DIR', OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    iid = alert['incident_id']

    ticket = {
        'incident_id': iid,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'alert_type': alert['alert_type'],
        'severity': severity.value,
        'device': {
            'hostname': alert['device_hostname'],
            'ip': alert['device_ip'],
            'customer_id': alert['customer_id'],
        },
        'diagnostic_summary': diagnostic.get('diagnostic_summary', ''),
        'raw_data': diagnostic.get('raw_data', {}),
        'recommended_action': RECOMMENDED_ACTIONS.get(alert['alert_type'], ''),
        'processing_time_ms': diagnostic.get('processing_time_ms', 0),
        'errors': diagnostic.get('errors', []),
        'log_ref': 'logs/soar.log',
    }

    json_path = os.path.join(output_dir, f'{iid}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(ticket, f, indent=2, ensure_ascii=False)

    txt_path = os.path.join(output_dir, f'{iid}.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(_format_plain_text(ticket))

    logger.info(f'Salida generada: {json_path}', extra={'incident_id': iid})
    return ticket


def _format_plain_text(ticket: dict) -> str:
    lines = [
        '=' * 60,
        'TICKET DE INCIDENCIA SOAR',
        '=' * 60,
        f"ID:          {ticket['incident_id']}",
        f"Fecha:       {ticket['timestamp']}",
        f"Tipo:        {ticket['alert_type'].upper()}",
        f"Severidad:   {ticket['severity'].upper()}",
        f"Dispositivo: {ticket['device']['hostname']} ({ticket['device']['ip']})",
        f"Cliente:     {ticket['device']['customer_id']}",
        '-' * 60,
        'DIAGNÓSTICO:',
        ticket['diagnostic_summary'],
        '-' * 60,
        'ACCIÓN RECOMENDADA:',
        ticket['recommended_action'],
        '-' * 60,
        f"Tiempo de procesado: {ticket['processing_time_ms']} ms",
        f"Log: {ticket['log_ref']}",
    ]
    if ticket['errors']:
        lines.append('-' * 60)
        lines.append('ERRORES DURANTE DIAGNÓSTICO:')
        for err in ticket['errors']:
            lines.append(f'  - {err}')
    lines.append('=' * 60)
    return '\n'.join(lines) + '\n'