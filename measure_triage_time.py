# measure_triage_time.py
# Medición automatizada del tiempo de triaje para pruebas comparativas.
#
# Ejecuta N trials por tipo de alerta (VPN y saturación), cronometra cada uno
# y genera un informe con estadísticas (mediana, media, mín, máx, desviación).
#
# Usa alertas variadas generadas por generate_trial_alerts.py (distintos
# clientes, dispositivos, túneles, umbrales). Si no existen, las genera
# automáticamente antes de ejecutar los trials.
#
# Uso:
#   python measure_triage_time.py              # 10 trials por tipo (por defecto)
#   python measure_triage_time.py --trials 5   # 5 trials por tipo
#
# Requisitos:
#   - El listener debe estar arrancado: python run.py
#   - La FortiOS VM debe estar accesible en 192.168.75.2
#
# Salida:
#   - output/metrics_vpn.json         — resultados detallados VPN
#   - output/metrics_resource.json    — resultados detallados saturación
#   - output/metrics_summary.json     — resumen comparativo
#   - Resumen por consola

import argparse
import json
import os
import statistics
import sys
import time
import uuid

import requests

LISTENER_URL = os.getenv('LISTENER_URL', 'http://localhost:5000/webhook')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', './output')
TRIALS_DIR = os.path.join(OUTPUT_DIR, 'trials')
FIXTURES_FALLBACK = {
    'vpn': 'tests/fixtures/webhook_vpn.json',
    'resource': 'tests/fixtures/webhook_resource.json',
}


def load_trial_alert(alert_type, trial_num):
    """Carga la alerta variada para un trial concreto. Si no existe, usa el fixture base."""
    trial_path = os.path.join(TRIALS_DIR, f'{alert_type}_{trial_num:02d}.json')
    if os.path.exists(trial_path):
        with open(trial_path, encoding='utf-8') as f:
            return json.load(f)
    # Fallback al fixture base si no hay alertas generadas
    path = FIXTURES_FALLBACK[alert_type]
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def run_trial(payload, trial_num):
    """Ejecuta un trial: envía el webhook y mide el tiempo de respuesta."""
    # Generar incident_id único para evitar deduplicación
    date_str = time.strftime('%Y%m%d')
    short_id = uuid.uuid4().hex[:8].upper()
    payload['incident_id'] = f'INC-{date_str}-T{trial_num:03d}-{short_id}'

    start = time.perf_counter()
    try:
        resp = requests.post(
            LISTENER_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        end = time.perf_counter()
        elapsed_ms = round((end - start) * 1000, 1)

        # Leer el processing_time_ms del ticket generado
        ticket_path = os.path.join(OUTPUT_DIR, f'{payload["incident_id"]}.json')
        processing_ms = None
        if os.path.exists(ticket_path):
            with open(ticket_path, encoding='utf-8') as f:
                ticket = json.load(f)
                processing_ms = ticket.get('processing_time_ms')

        return {
            'trial': trial_num,
            'incident_id': payload['incident_id'],
            'http_status': resp.status_code,
            'response_time_ms': elapsed_ms,
            'processing_time_ms': processing_ms,
            'success': resp.status_code == 202,
        }

    except requests.exceptions.ConnectionError:
        return {
            'trial': trial_num,
            'incident_id': payload['incident_id'],
            'http_status': None,
            'response_time_ms': None,
            'processing_time_ms': None,
            'success': False,
            'error': 'No se puede conectar al listener',
        }
    except requests.exceptions.ReadTimeout:
        return {
            'trial': trial_num,
            'incident_id': payload['incident_id'],
            'http_status': None,
            'response_time_ms': None,
            'processing_time_ms': None,
            'success': False,
            'error': 'Timeout esperando respuesta del listener',
        }


def calculate_stats(results):
    """Calcula estadísticas de los trials exitosos."""
    successful = [r for r in results if r['success']]
    if not successful:
        return {'n': 0, 'error': 'Ningún trial exitoso'}

    response_times = [r['response_time_ms'] for r in successful]
    processing_times = [r['processing_time_ms'] for r in successful
                        if r['processing_time_ms'] is not None]

    stats = {
        'n_total': len(results),
        'n_exitosos': len(successful),
        'response_time': {
            'mediana_ms': round(statistics.median(response_times), 1),
            'media_ms': round(statistics.mean(response_times), 1),
            'min_ms': round(min(response_times), 1),
            'max_ms': round(max(response_times), 1),
            'desviacion_ms': round(statistics.stdev(response_times), 1) if len(response_times) > 1 else 0,
        },
    }

    if processing_times:
        stats['processing_time'] = {
            'mediana_ms': round(statistics.median(processing_times), 1),
            'media_ms': round(statistics.mean(processing_times), 1),
            'min_ms': round(min(processing_times), 1),
            'max_ms': round(max(processing_times), 1),
        }

    return stats


def run_trials(alert_type, n_trials):
    """Ejecuta N trials para un tipo de alerta y devuelve resultados + estadísticas."""
    print(f'\n{"="*60}')
    print(f'  Ejecutando {n_trials} trials para: {alert_type.upper()}')
    print(f'{"="*60}')

    results = []

    for i in range(1, n_trials + 1):
        payload = load_trial_alert(alert_type, i)
        result = run_trial(payload, i)
        results.append(result)

        status = 'OK' if result['success'] else 'FALLO'
        time_str = f"{result['response_time_ms']}ms" if result['response_time_ms'] else 'N/A'
        proc_str = f"(pipeline: {result['processing_time_ms']}ms)" if result.get('processing_time_ms') else ''
        print(f'  Trial {i:2d}/{n_trials}: {status} — {time_str} {proc_str}')

        # Pausa entre trials para evitar rate limiting
        if i < n_trials:
            time.sleep(0.5)

    stats = calculate_stats(results)
    return {'alert_type': alert_type, 'results': results, 'statistics': stats}


def print_summary(vpn_data, resource_data):
    """Muestra el resumen comparativo por consola."""
    print(f'\n{"="*60}')
    print('  RESUMEN DE PRUEBAS AUTOMATIZADAS')
    print(f'{"="*60}')

    for data in [vpn_data, resource_data]:
        stats = data['statistics']
        alert = data['alert_type'].upper()
        print(f'\n  {alert}:')
        print(f'    Trials exitosos: {stats.get("n_exitosos", 0)}/{stats.get("n_total", 0)}')
        if 'response_time' in stats:
            rt = stats['response_time']
            print(f'    Tiempo respuesta (mediana): {rt["mediana_ms"]}ms')
            print(f'    Tiempo respuesta (rango):   {rt["min_ms"]}ms – {rt["max_ms"]}ms')
        if 'processing_time' in stats:
            pt = stats['processing_time']
            print(f'    Tiempo pipeline (mediana):   {pt["mediana_ms"]}ms')

    print(f'\n{"="*60}')
    print(f'  Resultados guardados en {OUTPUT_DIR}/metrics_*.json')
    print(f'{"="*60}\n')


def main():
    parser = argparse.ArgumentParser(
        description='Medición automatizada del tiempo de triaje SOAR'
    )
    parser.add_argument(
        '--trials', type=int, default=10,
        help='Número de trials por tipo de alerta (por defecto: 10)'
    )
    args = parser.parse_args()

    # Verificar que el listener está arrancado
    try:
        resp = requests.get('http://localhost:5000/health', timeout=5)
        if resp.status_code != 200:
            print('[ERROR] El listener no responde correctamente en /health')
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print('[ERROR] No se puede conectar al listener. Arrancarlo con: python run.py')
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generar alertas variadas si no existen
    first_vpn = os.path.join(TRIALS_DIR, 'vpn_01.json')
    if not os.path.exists(first_vpn):
        print('[*] Generando alertas variadas para los trials...')
        import subprocess
        subprocess.run(
            [sys.executable, 'generate_trial_alerts.py', '--trials', str(args.trials)],
            check=True
        )
        print()

    # Ejecutar trials
    vpn_data = run_trials('vpn', args.trials)
    resource_data = run_trials('resource', args.trials)

    # Guardar resultados detallados
    for data, name in [(vpn_data, 'vpn'), (resource_data, 'resource')]:
        path = os.path.join(OUTPUT_DIR, f'metrics_{name}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Guardar resumen comparativo
    summary = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'trials_per_type': args.trials,
        'vpn': vpn_data['statistics'],
        'resource': resource_data['statistics'],
    }
    summary_path = os.path.join(OUTPUT_DIR, 'metrics_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print_summary(vpn_data, resource_data)


if __name__ == '__main__':
    main()
