# generate_trial_alerts.py
# Genera las 10 alertas para los trials comparativos (capítulo 6 de la memoria):
# 5 alertas VPN + 5 alertas de saturación.
#
# Cada alerta tiene datos distintos (cliente, dispositivo, IP, túnel, umbral)
# pero sigue el mismo esquema que los fixtures originales. Esto hace que los
# trials sean más realistas: el técnico debe leer datos diferentes cada vez
# y el sistema debe procesar payloads variados correctamente.
#
# Las 5 alertas de saturación cubren las tres severidades (critical, warning,
# info) y ambos tipos de recurso (cpu, mem), de modo que con sólo 5 trials se
# valida todo el espacio de decisión del clasificador.
#
# Uso:
#   python generate_trial_alerts.py
#
# Salida:
#   output/trials/vpn_01.json ... vpn_05.json
#   output/trials/resource_01.json ... resource_05.json

import json
import os
import time

OUTPUT_DIR = os.path.join(os.getenv('OUTPUT_DIR', './output'), 'trials')

# --- Datos variados pero realistas (5 conjuntos por tipo) ---

CLIENTS = [
    {'id': 'CLIENTE-A', 'name': 'Sede Central Madrid'},
    {'id': 'CLIENTE-B', 'name': 'Delegación Barcelona'},
    {'id': 'CLIENTE-C', 'name': 'Oficina Valencia'},
    {'id': 'CLIENTE-D', 'name': 'Centro Datos Sevilla'},
    {'id': 'CLIENTE-E', 'name': 'Sede Bilbao'},
]

FIREWALLS = [
    {'hostname': 'FW-MADRID-01', 'ip': '10.10.1.1'},
    {'hostname': 'FW-BCN-02', 'ip': '10.10.2.1'},
    {'hostname': 'FW-VLC-01', 'ip': '10.10.3.1'},
    {'hostname': 'FW-SVQ-03', 'ip': '10.10.4.1'},
    {'hostname': 'FW-BIO-01', 'ip': '10.10.5.1'},
]

VPN_TUNNELS = [
    {'name': 'VPN-SEDE-CENTRAL-MADRID', 'gw': '10.20.1.1'},
    {'name': 'VPN-BACKUP-BCN', 'gw': '10.20.2.1'},
    {'name': 'VPN-INTERSITE-VLC', 'gw': '10.20.3.1'},
    {'name': 'VPN-DC-SEVILLA', 'gw': '10.20.4.1'},
    {'name': 'VPN-CORPORATIVA-BIO', 'gw': '10.20.5.1'},
]

# Umbrales que cubren las 3 severidades y ambos recursos (cpu, mem)
THRESHOLDS = [
    {'resource': 'cpu', 'value': 97.2, 'severity_expected': 'critical'},
    {'resource': 'mem', 'value': 96.3, 'severity_expected': 'critical'},
    {'resource': 'cpu', 'value': 85.4, 'severity_expected': 'warning'},
    {'resource': 'mem', 'value': 82.7, 'severity_expected': 'warning'},
    {'resource': 'cpu', 'value': 55.0, 'severity_expected': 'info'},
]

NUM_TRIALS = 5


def generate_vpn_alert(trial_num, client, firewall, tunnel):
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
        'description': f"Tunnel {tunnel['name']} down - {client['name']}",
    }


def generate_resource_alert(trial_num, client, firewall, threshold):
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
        'description': f"{threshold['resource'].upper()} usage {threshold['value']}% - {client['name']}",
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f'Generando {NUM_TRIALS} alertas VPN...')
    for i in range(NUM_TRIALS):
        alert = generate_vpn_alert(i + 1, CLIENTS[i], FIREWALLS[i], VPN_TUNNELS[i])
        path = os.path.join(OUTPUT_DIR, f'vpn_{i+1:02d}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(alert, f, indent=2, ensure_ascii=False)
        print(f'  {path} - {alert["customer_id"]} / {alert["vpn_tunnel_name"]}')

    print(f'\nGenerando {NUM_TRIALS} alertas de saturacion...')
    for i in range(NUM_TRIALS):
        alert = generate_resource_alert(i + 1, CLIENTS[i], FIREWALLS[i], THRESHOLDS[i])
        path = os.path.join(OUTPUT_DIR, f'resource_{i+1:02d}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(alert, f, indent=2, ensure_ascii=False)
        sev = THRESHOLDS[i]['severity_expected']
        print(f'  {path} - {alert["customer_id"]} / {alert["resource_type"]} {alert["threshold_value"]}% -> {sev}')

    print(f'\n{NUM_TRIALS * 2} alertas generadas en {OUTPUT_DIR}/')


if __name__ == '__main__':
    main()