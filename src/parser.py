# src/parser.py
from datetime import datetime
import uuid

# Campos obligatorios del webhook WOCU
REQUIRED_FIELDS = {'alert_type', 'device_ip', 'device_hostname', 'customer_id', 'timestamp'}
VALID_ALERT_TYPES = {'vpn_down', 'resource_saturation'}


def parse_and_validate_webhook(data: dict) -> dict:
    """
    Valida el payload del webhook y normaliza los campos.
    Lanza ValueError si la estructura es inválida.
    Devuelve el alert dict normalizado con incident_id garantizado.
    """
    if data is None:
        raise ValueError('Payload vacío o no-JSON')

    # Verificar campos obligatorios
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ValueError(f'Campos obligatorios ausentes: {sorted(missing)}')

    # Validar tipo de alerta
    alert_type = data.get('alert_type', '')
    if alert_type not in VALID_ALERT_TYPES:
        raise ValueError(
            f'alert_type inválido: "{alert_type}". '
            f'Valores válidos: {sorted(VALID_ALERT_TYPES)}'
        )

    # Generar incident_id si no viene en el webhook
    incident_id = data.get('incident_id') or _generate_incident_id()

    alert = {
        'incident_id': incident_id,
        'alert_type': alert_type,
        'device_ip': data['device_ip'],
        'device_hostname': data['device_hostname'],
        'customer_id': data['customer_id'],
        'timestamp': data['timestamp'],
        'raw_webhook': data,
    }

    # Propagar campos adicionales específicos de cada tipo de alerta
    for extra_field in ('vpn_tunnel_name', 'resource_type', 'threshold_value'):
        if extra_field in data:
            alert[extra_field] = data[extra_field]

    return alert


def _generate_incident_id() -> str:
    date_str = datetime.now().strftime('%Y%m%d')
    short_uuid = str(uuid.uuid4())[:8].upper()
    return f'INC-{date_str}-{short_uuid}'
