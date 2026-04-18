# uoc_tfg_triaje_soar

Prototipo SOAR para la automatización del triaje inicial de incidencias de red.

**TFG — Diseño e implementación de un sistema SOAR para la automatización del triaje inicial de incidencias de red**
Universitat Oberta de Catalunya (UOC) · Administración de Redes y Sistemas Operativos
Autor: Miguel Ángel Piay García · mapiayg@uoc.edu

---

## Entorno de laboratorio

| Componente | Versión | Detalle |
|---|---|---|
| Python | 3.11.9 | |
| FortiOS VM | v7.4.11 | IP de gestión: `192.168.75.2` |
| VMware Workstation Pro | 25.0.1 | Red NAT — VMnet8 `192.168.75.0/24` |
| SO host | Windows 11 Pro | |

---

## Instalación

```bash
git clone https://github.com/mapiayg/uoc_tfg_triaje_soar.git
cd uoc_tfg_triaje_soar
python -m venv venv
source venv/Scripts/activate   # Git Bash
pip install -r requirements.txt
cp .env.example .env           # Editar .env con los valores reales
```

### Variables de entorno (`.env`)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `FORTI_HOST` | IP de la FortiOS VM | `192.168.75.2` |
| `FORTI_TOKEN` | Token del API user `soar-reader` | `xxxxxxxxxxxxxxxx` |
| `FORTI_VERIFY_SSL` | Verificar certificado SSL | `false` (laboratorio) |
| `LISTENER_SECRET` | Secreto HMAC para verificar webhooks (opcional) | dejar vacío en lab |
| `LOG_LEVEL` | Nivel de log | `INFO` |
| `OUTPUT_DIR` | Directorio de tickets generados | `output` |

---

## Verificar el entorno de laboratorio

```bash
python test_api_connection.py
```

---

## Ejecutar los tests

```bash
pytest tests/ -v
```

Requiere la FortiOS VM en marcha. Resultado esperado: **48 passed** (14 parser + 10 severity + 7 VPN + 7 resource + 10 router). Si la VM no está disponible, los tests de integración se saltan automáticamente (24 passed, 24 skipped).

---

## Arrancar el sistema

```bash
python run.py
```

El listener queda a la escucha en `http://localhost:5000`.

### Enviar alertas de prueba

```bash
python simulate_webhook.py vpn       # alerta de caída VPN
python simulate_webhook.py resource  # alerta de saturación de recursos
```

### Demostración automatizada

```bash
python demo_live.py
```

### Pruebas comparativas (validación)

```bash
python generate_trial_alerts.py            # genera alertas variadas en output/trials/
```

Con el listener arrancado (`python run.py`):

```bash
python measure_triage_time.py              # 10 trials por tipo de alerta
python measure_triage_time.py --trials 5   # 5 trials por tipo
```

Genera alertas variadas automáticamente si no existen, y guarda los resultados en `output/metrics_vpn.json`, `output/metrics_resource.json` y `output/metrics_summary.json`.

### Proyección de impacto operativo

```bash
python calculate_impact.py                        # usa datos de measure_triage_time.py
python calculate_impact.py --manual-time 12       # tiempo manual en minutos
python calculate_impact.py --alerts 5 10 20 30    # escenarios de alertas/día
```

Genera `output/impact_projection.json` con la tabla de ahorro estimado en horas/hombre.

---

## Estructura del proyecto

```
uoc_tfg_triaje_soar/
  README.md
  requirements.txt
  run.py                        # Punto de entrada
  simulate_webhook.py           # Simulador de webhooks WOCU
  test_api_connection.py        # Verificación de conectividad
  demo_live.py                  # Demostración automatizada
  demo_severity.py              # Demo del clasificador
  generate_trial_alerts.py      # Generador de alertas variadas para trials
  measure_triage_time.py        # Medición automatizada de trials
  calculate_impact.py           # Proyección de impacto operativo

  src/
    listener.py                 # Endpoint HTTP (Flask)
    parser.py                   # Validación del webhook
    idempotency.py              # Deduplicación con TTL
    router.py                   # Dispatcher de módulos
    severity.py                 # Clasificador de severidad
    output.py                   # Generador de ticket JSON + TXT
    logger_config.py            # Logging JSON
    diagnostics/
      vpn.py                    # Playbook VPN (3 consultas API)
      resources.py              # Playbook saturación (3 consultas API)
    fortinet/
      client.py                 # Cliente HTTP con retry/backoff
      endpoints.py              # Constantes de endpoints

  tests/
    conftest.py                 # Verificación de VM para tests de integración
    test_parser.py              # 14 tests unitarios
    test_severity.py            # 10 tests unitarios
    test_vpn_module.py          # 7 tests de integración (caso VPN)
    test_resource_module.py     # 7 tests de integración (caso saturación)
    test_router.py              # 10 tests de integración (pipeline completo)
    fixtures/
      webhook_vpn.json          # Payload alerta VPN
      webhook_resource.json     # Payload alerta saturación
      webhook_error_field.json  # Payload con campos faltantes
      webhook_error_type.json   # Payload con tipo inválido

  output/                       # Tickets generados (gitignored)
  logs/                         # Logs JSON (gitignored)
```

---

## Tipos de incidencia soportados

| Tipo | `alert_type` | Playbook |
|---|---|---|
| Caída de túnel VPN IPSec | `vpn_down` | Estado túnel · configuración phase1 · estado interfaz |
| Saturación de recursos | `resource_saturation` | Consumo CPU/mem · sesiones activas · estado interfaces |

---

## Arquitectura del sistema

```
WOCU (alerta)
    |
    v HTTP POST /webhook
+-----------------------+
|  Listener (Flask)     |  <- src/listener.py
|  + Idempotencia       |  <- src/idempotency.py
+-----------+-----------+
            |
            v
+-----------------------+
|  Parser / Validator   |  <- src/parser.py
|  (valida esquema)     |
+-----------+-----------+
            |
            v
+-----------------------+
|  Router / Dispatcher  |  <- src/router.py
|  (selecciona módulo)  |
+------+------+---------+
       |      |
       v      v
   VPN Diag  Resource Diag  <- src/diagnostics/vpn.py
                             <- src/diagnostics/resources.py
       |      |
       +------+
            |
            v
+-----------------------+
|  Clasificador         |  <- src/severity.py
|  de Severidad         |
+-----------+-----------+
            |
            v
+-----------------------+
|  Generador de         |  <- src/output.py
|  Tickets JSON + TXT   |
+-----------+-----------+
            |
            v
    Ticket INC-*.json
    + INC-*.txt
    + logs/soar.log
```
