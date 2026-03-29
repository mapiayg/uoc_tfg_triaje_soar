# simulate_webhook.py
# Uso: python simulate_webhook.py [vpn|resource]
import requests
import json
import sys
import os

LISTENER_URL = os.getenv('LISTENER_URL', 'http://localhost:5000/webhook')


def send_webhook(fixture_file: str):
    if not os.path.exists(fixture_file):
        print(f'[ERROR] No se encuentra el fixture: {fixture_file}')
        return
    with open(fixture_file, encoding='utf-8') as f:
        payload = json.load(f)
    print(f'[>] Enviando webhook a {LISTENER_URL}')
    print(f'    Fixture: {fixture_file}')
    print(f'    alert_type: {payload.get("alert_type")}')
    print(f'    incident_id: {payload.get("incident_id")}')
    try:
        resp = requests.post(
            LISTENER_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f'[<] Status: {resp.status_code}')
        print(f'    Response: {resp.json()}')
    except requests.exceptions.ConnectionError:
        print('[ERROR] No se puede conectar al listener. ¿Está arrancado? (python run.py)')


if __name__ == '__main__':
    alert_type = sys.argv[1] if len(sys.argv) > 1 else 'vpn'
    fixtures = {
        'vpn': 'tests/fixtures/webhook_vpn.json',
        'resource': 'tests/fixtures/webhook_resource.json',
    }
    fixture = fixtures.get(alert_type, fixtures['vpn'])
    send_webhook(fixture)
