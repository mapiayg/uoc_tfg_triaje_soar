# tests/test_parser.py
import pytest
from src.parser import parse_and_validate_webhook, _generate_incident_id


# --- Fixtures de payloads válidos ---

VALID_VPN_PAYLOAD = {
    'incident_id': 'INC-20260323-VPN001',
    'alert_type': 'vpn_down',
    'device_ip': '10.10.1.1',
    'device_hostname': 'FW-CLIENTE-A-01',
    'customer_id': 'CLIENTE-A',
    'timestamp': '2026-03-23T10:30:00Z',
    'vpn_tunnel_name': 'VPN-SEDE-CENTRAL-MADRID',
    'remote_gateway': '10.20.1.1',
    'description': 'Tunnel VPN-SEDE-CENTRAL-MADRID down',
}

VALID_RESOURCE_PAYLOAD = {
    'incident_id': 'INC-20260323-CPU001',
    'alert_type': 'resource_saturation',
    'device_ip': '10.10.2.1',
    'device_hostname': 'FW-CLIENTE-B-01',
    'customer_id': 'CLIENTE-B',
    'timestamp': '2026-03-23T11:00:00Z',
    'resource_type': 'cpu',
    'threshold_value': 95.5,
    'description': 'CPU usage above 90% threshold',
}


# --- Tests de casos válidos ---

class TestParserValidCases:

    def test_vpn_payload_parsed_correctly(self):
        result = parse_and_validate_webhook(VALID_VPN_PAYLOAD)
        assert result['alert_type'] == 'vpn_down'
        assert result['incident_id'] == 'INC-20260323-VPN001'
        assert result['device_ip'] == '10.10.1.1'
        assert result['device_hostname'] == 'FW-CLIENTE-A-01'
        assert result['customer_id'] == 'CLIENTE-A'
        assert result['timestamp'] == '2026-03-23T10:30:00Z'

    def test_resource_payload_parsed_correctly(self):
        result = parse_and_validate_webhook(VALID_RESOURCE_PAYLOAD)
        assert result['alert_type'] == 'resource_saturation'
        assert result['incident_id'] == 'INC-20260323-CPU001'

    def test_raw_webhook_preserved(self):
        """El parser debe conservar el payload original completo en raw_webhook."""
        result = parse_and_validate_webhook(VALID_VPN_PAYLOAD)
        assert result['raw_webhook'] == VALID_VPN_PAYLOAD

    def test_incident_id_generated_when_missing(self):
        """Si el webhook no incluye incident_id, el parser lo genera."""
        payload_without_id = {k: v for k, v in VALID_VPN_PAYLOAD.items() if k != 'incident_id'}
        result = parse_and_validate_webhook(payload_without_id)
        assert result['incident_id'].startswith('INC-')
        assert len(result['incident_id']) > 10

    def test_extra_fields_in_raw_webhook(self):
        """Campos adicionales (vpn_tunnel_name, etc.) deben estar en raw_webhook."""
        result = parse_and_validate_webhook(VALID_VPN_PAYLOAD)
        assert 'vpn_tunnel_name' in result['raw_webhook']


# --- Tests de casos de error ---

class TestParserErrorCases:

    def test_none_payload_raises_value_error(self):
        with pytest.raises(ValueError, match='Payload vacío'):
            parse_and_validate_webhook(None)

    def test_empty_dict_raises_value_error(self):
        with pytest.raises(ValueError, match='Campos obligatorios ausentes'):
            parse_and_validate_webhook({})

    def test_missing_alert_type_raises_value_error(self):
        payload = {k: v for k, v in VALID_VPN_PAYLOAD.items() if k != 'alert_type'}
        with pytest.raises(ValueError, match='alert_type'):
            parse_and_validate_webhook(payload)

    def test_missing_device_ip_raises_value_error(self):
        payload = {k: v for k, v in VALID_VPN_PAYLOAD.items() if k != 'device_ip'}
        with pytest.raises(ValueError, match='device_ip'):
            parse_and_validate_webhook(payload)

    def test_missing_customer_id_raises_value_error(self):
        payload = {k: v for k, v in VALID_VPN_PAYLOAD.items() if k != 'customer_id'}
        with pytest.raises(ValueError, match='customer_id'):
            parse_and_validate_webhook(payload)

    def test_invalid_alert_type_raises_value_error(self):
        payload = {**VALID_VPN_PAYLOAD, 'alert_type': 'unknown_alert'}
        with pytest.raises(ValueError, match='alert_type inválido'):
            parse_and_validate_webhook(payload)

    def test_empty_alert_type_raises_value_error(self):
        payload = {**VALID_VPN_PAYLOAD, 'alert_type': ''}
        with pytest.raises(ValueError, match='alert_type inválido'):
            parse_and_validate_webhook(payload)


# --- Tests del generador de incident_id ---

class TestIncidentIdGeneration:

    def test_incident_id_format(self):
        """El incident_id debe seguir el patrón INC-YYYYMMDD-XXXXXXXX."""
        iid = _generate_incident_id()
        parts = iid.split('-')
        assert parts[0] == 'INC'
        assert len(parts[1]) == 8   # YYYYMMDD
        assert len(parts[2]) == 8   # 8 chars de UUID

    def test_incident_ids_are_unique(self):
        """Dos llamadas consecutivas deben producir IDs diferentes."""
        id1 = _generate_incident_id()
        id2 = _generate_incident_id()
        assert id1 != id2
