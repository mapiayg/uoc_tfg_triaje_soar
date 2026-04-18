# generate_trial_alerts.py
# Genera alertas variadas para los trials comparativos (capítulo 6).
#
# Cada alerta tiene datos distintos (cliente, dispositivo, IP, túnel, umbral)
# pero sigue el mismo esquema que los fixtures originales. Esto hace que los
# trials sean más realistas: el técnico debe leer datos diferentes cada vez
# y el sistema debe procesar payloads variados correctamente.
#
# Uso:
#   python generate_trial_alerts.py                # 10 VPN + 10 saturación (por defecto)
#   python generate_trial_alerts.py --trials 5     # 5 + 5
#
# Salida:
#   output/trials/vpn_01.json ... vpn_10.json
#   output/trials/resource_01.json ... resource_10.json

import argparse
import json
import os
import random
import time

OUTPUT_DIR = os.path.join(os.getenv('OUTPUT_DIR', './output'), 'trials')

# --- Datos variados pero realistas ---

CLIENTS = [
    {'id': 'CLIENTE-A', 'name': 'Sede Central Madrid'},
    {'id': 'CLIENTE-B', 'name': 'Delegación Barcelona'},
    {'id': 'CLIENTE-C', 'name': 'Oficina Valencia'},
    {'id': 'CLIENTE-D', 'name': 'Centro Datos Sevilla'},
    {'id': 'CLIENTE-E', 'name': 'Sede Bilbao'},
    {'id': 'CLIENTE-F', 'name': 'Oficina Málaga'},
    {'id': 'CLIENTE-G', 'name': 'Delegación Zaragoza'},
    {'id': 'CLIENTE-H', 'name': 'Centro Datos Lisboa'},
    {'id': 'CLIENTE-I', 'name': 'Sede Oporto'},
    {'id': 'CLIENTE-J', 'name': 'Oficina Vigo'},
]

FIREWALLS = [
    {'hostname': 'FW-MADRID-01', 'ip': '10.10.1.1'},
    {'hostname': 'FW-BCN-02', 'ip': '10.10.2.1'},
    {'hostname': 'FW-VLC-01', 'ip': '10.10.3.1'},
    {'hostname': 'FW-SVQ-03', 'ip': '10.10.4.1'},
    {'hostname': 'FW-BIO-01', 'ip': '10.10.5.1'},
    {'hostname': 'FW-AGP-02', 'ip': '10.10.6.1'},
    {'hostname': 'FW-ZAZ-01', 'ip': '10.10.7.1'},
    {'hostname': 'FW-LIS-01', 'ip': '10.10.8.1'},
    {'hostname': 'FW-OPO-02', 'ip': '10.10.9.1'},
    {'hostname': 'FW-VGO-01', 'ip': '10.10.10.1'},
]

VPN_TUNNELS = [
    {'name': 'VPN-SEDE-CENTRAL-MADRID', 'gw': '10.20.1.1'},
    {'name': 'VPN-BACKUP-BCN', 'gw': '10.20.2.1'},
    {'name': 'VPN-INTERSITE-VLC', 'gw': '10.20.3.1'},
    {'name': 'VPN-DC-SEVILLA', 'gw': '10.20.4.1'},
    {'name': 'VPN-CORPORATIVA-BIO', 'gw': '10.20.5.1'},
    {'name': 'VPN-SITE2SITE-AGP', 'gw': '10.20.6.1'},
    {'name': 'VPN-PRINCIPAL-ZAZ', 'gw': '10.20.7.1'},
    {'name': 'VPN-INTER-LIS', 'gw': '10.20.8.1'},
    {'name': 'VPN-REDUNDANCIA-OPO', 'gw': '10.20.9.1'},
    {'name': 'VPN-ENLACE-VGO', 'gw': '10.20.10.1'},
]

# Umbrales variados para saturación — cubren las 3 severidades
THRESHOLDS = [
    {'resource': 'cpu', 'value': 97.2, 'severity_expected': 'critical'},
    {'resource': 'cpu', 'value': 92.8, 'severity_expected': 'critical'},
    {'resource': 'cpu', 'value': 85.4, 'severity_expected': 'warning'},
    {'resource': 'cpu', 'value': 78.1, 'severity_expected': 'warning'},
    {'resource': 'cpu', 'value': 71.6, 'severity_expected': 'warning'},
    {'resource': 'mem', 'value': 96.3, 'severity_expected': 'critical'},
    {'resource': 'cpu', 'value': 55.0, 'severity_expected': 'info'},
    {'resource': 'cpu', 'value': 91.5, 'severity_expected': 'critical'},
    {'resource': 'mem', 'value': 82.7, 'severity_expected': 'warning'},
    {'resource': 'cpu', 'value': 45.2, 'severity_expected': 'info'},
]


def generate_vpn_alert(trial_num, client, firewall, tunnel):
    """Genera una alerta VPN con datos variados."""
    date_str = time.strftime('%Y%m%d')
    return {
        'incident_id': f'INC-{date_str}-VPN{trial_num:03d}',
        'alert_type': 'vpn_down',
        'device_ip': firewall['ip'],
        'device_hostname': firewall['hostname'],
        'customer_id': client['id'],
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'vpn_tunnel_name': tunnel['name'],
        'remote_gateway': tunnel['gw'],
        'description': f"Tunnel {tunnel['name']} down — {client['name']}",
    }


def generate_resource_alert(trial_num, client, firewall, threshold):
    """Genera una alerta de saturación con datos variados."""
    date_str = time.strftime('%Y%m%d')
    return {
        'incident_id': f'INC-{date_str}-RES{trial_num:03d}',
        'alert_type': 'resource_saturation',
        'device_ip': firewall['ip'],
        'device_hostname': firewall['hostname'],
        'customer_id': client['id'],
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'resource_type': threshold['resource'],
        'threshold_value': threshold['value'],
        'description': f"{threshold['resource'].upper()} usage {threshold['value']}% — {client['name']}",
    }


def main():
    parser = argparse.ArgumentParser(
        description='Genera alertas variadas para trials comparativos'
    )
    parser.add_argument(
        '--trials', type=int, default=10,
        help='Número de alertas por tipo (por defecto: 10)'
    )
    args = parser.parse_args()
    n = min(args.trials, 10)  # máximo 10 (por el número de datos variados)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generar alertas VPN
    print(f'Generando {n} alertas VPN...')
    for i in range(n):
        alert = generate_vpn_alert(i + 1, CLIENTS[i], FIREWALLS[i], VPN_TUNNELS[i])
        path = os.path.join(OUTPUT_DIR, f'vpn_{i+1:02d}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(alert, f, indent=2, ensure_ascii=False)
        print(f'  {path} — {alert["customer_id"]} / {alert["vpn_tunnel_name"]}')

    # Generar alertas de saturación
    print(f'\nGenerando {n} alertas de saturación...')
    for i in range(n):
        alert = generate_resource_alert(i + 1, CLIENTS[i], FIREWALLS[i], THRESHOLDS[i])
        path = os.path.join(OUTPUT_DIR, f'resource_{i+1:02d}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(alert, f, indent=2, ensure_ascii=False)
        sev = THRESHOLDS[i]['severity_expected']
        print(f'  {path} — {alert["customer_id"]} / {alert["resource_type"]} {alert["threshold_value"]}% → {sev}')

    print(f'\n{n * 2} alertas generadas en {OUTPUT_DIR}/')
    print(f'Severidades esperadas en saturación:')
    for t in THRESHOLDS[:n]:
        print(f'  {t["resource"]} {t["value"]}% → {t["severity_expected"]}')


if __name__ == '__main__':
    main()
