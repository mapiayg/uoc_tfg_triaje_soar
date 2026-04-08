# demo_severity.py
# Muestra las reglas de clasificacion de severidad del sistema.
# Uso: python demo_severity.py
from src.severity import classify

casos = [
    ('vpn_down',            {'resource_type': 'vpn',  'threshold_value': 0 }),
    ('resource_saturation', {'resource_type': 'cpu',  'threshold_value': 95}),
    ('resource_saturation', {'resource_type': 'cpu',  'threshold_value': 75}),
    ('resource_saturation', {'resource_type': 'cpu',  'threshold_value': 50}),
    ('resource_saturation', {'resource_type': 'mem',  'threshold_value': 97}),
    ('resource_saturation', {'resource_type': 'mem',  'threshold_value': 82}),
    ('resource_saturation', {'resource_type': 'mem',  'threshold_value': 60}),
]

for tipo, alert in casos:
    r = alert.get('resource_type', '-')
    t = alert.get('threshold_value', 0)
    if tipo == 'vpn_down':
        label = 'caída de túnel'
    else:
        label = f'{r} {t}%'
    resultado = classify(tipo, alert, {}).value
    print(f'  {tipo:<25} {label:<18} ->  {resultado}')