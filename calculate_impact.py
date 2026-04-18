# calculate_impact.py
# Proyección de impacto operativo: ahorro estimado en horas/hombre.
#
# Lee los resultados de measure_triage_time.py (metrics_summary.json) y calcula
# la proyección de ahorro mensual y anual para distintos volúmenes de alertas.
#
# Uso:
#   python calculate_impact.py                        # usa datos de metrics_summary.json
#   python calculate_impact.py --manual-time 12       # tiempo manual en minutos (defecto: 12)
#   python calculate_impact.py --alerts 5 10 20 30    # escenarios de alertas/día
#
# Salida:
#   - output/impact_projection.json   — tabla de proyección completa
#   - Resumen por consola

import argparse
import json
import os
import sys

OUTPUT_DIR = os.getenv('OUTPUT_DIR', './output')


def load_automated_time():
    """Lee el tiempo automatizado real de metrics_summary.json (en ms)."""
    summary_path = os.path.join(OUTPUT_DIR, 'metrics_summary.json')
    if not os.path.exists(summary_path):
        return None

    with open(summary_path, encoding='utf-8') as f:
        summary = json.load(f)

    # Usar la mediana del processing_time de ambos tipos
    times = []
    for key in ['vpn', 'resource']:
        data = summary.get(key, {})
        pt = data.get('processing_time', {})
        if 'mediana_ms' in pt:
            times.append(pt['mediana_ms'])

    if times:
        return sum(times) / len(times)
    return None


def calculate_projection(manual_time_min, auto_time_min, alerts_per_day,
                         working_days=22):
    """Calcula la proyección de ahorro para un volumen de alertas dado."""
    saving_per_ticket = manual_time_min - auto_time_min
    reduction_pct = (saving_per_ticket / manual_time_min) * 100

    monthly_tickets = alerts_per_day * working_days
    monthly_saving_min = monthly_tickets * saving_per_ticket
    monthly_saving_hours = monthly_saving_min / 60
    annual_saving_hours = monthly_saving_hours * 12

    return {
        'alerts_per_day': alerts_per_day,
        'working_days_month': working_days,
        'monthly_tickets': monthly_tickets,
        'manual_time_min': round(manual_time_min, 2),
        'automated_time_min': round(auto_time_min, 4),
        'saving_per_ticket_min': round(saving_per_ticket, 2),
        'reduction_pct': round(reduction_pct, 1),
        'monthly_saving_hours': round(monthly_saving_hours, 1),
        'annual_saving_hours': round(annual_saving_hours, 0),
    }


def print_results(projections, manual_time, auto_time_ms):
    """Muestra la tabla de proyección por consola."""
    print(f'\n{"="*70}')
    print('  PROYECCIÓN DE IMPACTO OPERATIVO')
    print(f'{"="*70}')
    print(f'  Tiempo triaje manual (referencia):    {manual_time} min/ticket')
    print(f'  Tiempo triaje automatizado (mediana): {auto_time_ms:.0f} ms/ticket')
    print(f'  Reducción:                            {projections[0]["reduction_pct"]}%')

    print(f'\n  {"Alertas/día":>12} {"Tickets/mes":>12} {"Ahorro/mes (h)":>15} {"Ahorro/año (h)":>15}')
    print(f'  {"-"*12} {"-"*12} {"-"*15} {"-"*15}')

    for p in projections:
        print(f'  {p["alerts_per_day"]:>12} {p["monthly_tickets"]:>12} '
              f'{p["monthly_saving_hours"]:>15.1f} {p["annual_saving_hours"]:>15.0f}')

    print(f'\n{"="*70}')
    print(f'  Resultados guardados en {OUTPUT_DIR}/impact_projection.json')
    print(f'{"="*70}\n')


def main():
    parser = argparse.ArgumentParser(
        description='Proyección de impacto operativo del sistema SOAR'
    )
    parser.add_argument(
        '--manual-time', type=float, default=12.0,
        help='Tiempo medio de triaje manual en minutos (por defecto: 12)'
    )
    parser.add_argument(
        '--alerts', type=int, nargs='+', default=[5, 10, 15, 20, 30],
        help='Escenarios de alertas/día a proyectar (por defecto: 5 10 15 20 30)'
    )
    args = parser.parse_args()

    # Leer tiempo automatizado real
    auto_time_ms = load_automated_time()
    if auto_time_ms is not None:
        print(f'[OK] Tiempo automatizado leído de metrics_summary.json: {auto_time_ms:.0f} ms')
        auto_time_min = auto_time_ms / 60000  # ms → minutos
    else:
        print('[!] No se encontró metrics_summary.json — usando estimación de 100ms')
        auto_time_ms = 100.0
        auto_time_min = 100.0 / 60000

    # Calcular proyecciones
    projections = []
    for n in sorted(args.alerts):
        proj = calculate_projection(args.manual_time, auto_time_min, n)
        projections.append(proj)

    # Guardar resultados
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output = {
        'manual_time_min': args.manual_time,
        'automated_time_ms': round(auto_time_ms, 1),
        'automated_time_min': round(auto_time_min, 4),
        'source': 'metrics_summary.json' if load_automated_time() else 'estimación',
        'projections': projections,
    }
    output_path = os.path.join(OUTPUT_DIR, 'impact_projection.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print_results(projections, args.manual_time, auto_time_ms)


if __name__ == '__main__':
    main()
