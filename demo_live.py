# demo_live.py
# Demostración en vivo del pipeline SOAR completo.
# Arranca el listener, envía webhooks, muestra resultados y para el listener.
# Uso: python demo_live.py

import subprocess
import sys
import time
import json
import os
import requests
import shutil

LISTENER_URL = "http://localhost:5000"
WEBHOOK_URL = f"{LISTENER_URL}/webhook"
OUTPUT_DIR = "./output"


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(n, text):
    print(f"\n--- Paso {n}: {text} ---\n")


def wait_for_listener(timeout=10):
    """Espera a que el listener esté listo."""
    for _ in range(timeout * 10):
        try:
            resp = requests.get(f"{LISTENER_URL}/health", timeout=1)
            if resp.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.1)
    return False


def send_webhook(fixture_file, description):
    """Envía un webhook y muestra el resultado."""
    with open(fixture_file, encoding="utf-8") as f:
        payload = json.load(f)
    print(f"  Enviando: {description}")
    print(f"  Fixture:  {fixture_file}")
    print(f"  Tipo:     {payload.get('alert_type')}")
    print(f"  ID:       {payload.get('incident_id')}")
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    print(f"  Status:   {resp.status_code}")
    print(f"  Response: {json.dumps(resp.json(), ensure_ascii=False)}")
    return resp


def show_ticket(incident_id):
    """Muestra el ticket generado."""
    json_path = os.path.join(OUTPUT_DIR, f"{incident_id}.json")
    txt_path = os.path.join(OUTPUT_DIR, f"{incident_id}.txt")

    if os.path.exists(json_path):
        print(f"\n  Ticket JSON: {json_path}")
        with open(json_path, encoding="utf-8") as f:
            ticket = json.load(f)
        print(f"  Severidad:   {ticket['severity']}")
        print(f"  Diagnóstico: {ticket['diagnostic_summary'][:100]}...")
        print(f"  Tiempo:      {ticket['processing_time_ms']}ms")
        print(f"  Errores:     {ticket['errors']}")

    if os.path.exists(txt_path):
        print(f"\n  Ticket TXT: {txt_path}")
        with open(txt_path, encoding="utf-8") as f:
            print(f.read())


def main():
    print_header("DEMOSTRACIÓN EN VIVO — Pipeline SOAR")

    # Limpiar output anterior
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            os.remove(os.path.join(OUTPUT_DIR, f))

    # Paso 1 — Arrancar listener
    print_step(1, "Arrancando el listener")
    listener = subprocess.Popen(
        [sys.executable, "run.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if wait_for_listener():
        print("  Listener arrancado en http://localhost:5000")
    else:
        print("  ERROR: el listener no arrancó")
        listener.kill()
        sys.exit(1)

    try:
        # Paso 2 — Health check
        print_step(2, "Verificando health check")
        resp = requests.get(f"{LISTENER_URL}/health")
        print(f"  {json.dumps(resp.json(), ensure_ascii=False)}")

        # Paso 3 — Webhook VPN
        print_step(3, "Enviando alerta VPN (caso de uso 1)")
        send_webhook("tests/fixtures/webhook_vpn.json", "Caída de túnel VPN")
        time.sleep(0.5)
        show_ticket("INC-20260315-VPN001")

        # Paso 4 — Webhook saturación
        print_step(4, "Enviando alerta de saturación (caso de uso 2)")
        send_webhook("tests/fixtures/webhook_resource.json", "Saturación de recursos")
        time.sleep(0.5)
        show_ticket("INC-20260315-CPU002")

        # Paso 5 — Deduplicación
        print_step(5, "Deduplicación — mismo webhook VPN otra vez")
        send_webhook("tests/fixtures/webhook_vpn.json", "Mismo incident_id (duplicado)")

        # Paso 6 — Errores
        print_step(6, "Gestión de errores")
        print("  6a. Webhook con campos faltantes:")
        resp = requests.post(WEBHOOK_URL, json={"alert_type": "vpn_down", "device_ip": "10.0.0.1"}, timeout=10)
        print(f"  Status: {resp.status_code}")
        print(f"  Error:  {json.dumps(resp.json(), ensure_ascii=False)}")

        print("\n  6b. Tipo de alerta no soportado:")
        resp = requests.post(WEBHOOK_URL, json={
            "incident_id": "INC-TEST", "alert_type": "tipo_desconocido",
            "device_ip": "10.0.0.1", "device_hostname": "TEST",
            "customer_id": "TEST", "timestamp": "2026-04-12T10:00:00Z"
        }, timeout=10)
        print(f"  Status: {resp.status_code}")
        print(f"  Error:  {json.dumps(resp.json(), ensure_ascii=False)}")

        # Paso 7 — Clasificador de severidad
        print_step(7, "Clasificador de severidad")
        from src.severity import classify
        casos = [
            ("vpn_down", {"resource_type": "vpn", "threshold_value": 0}, "caída de túnel"),
            ("resource_saturation", {"resource_type": "cpu", "threshold_value": 95}, "cpu 95%"),
            ("resource_saturation", {"resource_type": "cpu", "threshold_value": 75}, "cpu 75%"),
            ("resource_saturation", {"resource_type": "cpu", "threshold_value": 50}, "cpu 50%"),
            ("resource_saturation", {"resource_type": "mem", "threshold_value": 97}, "mem 97%"),
            ("resource_saturation", {"resource_type": "mem", "threshold_value": 82}, "mem 82%"),
            ("resource_saturation", {"resource_type": "mem", "threshold_value": 60}, "mem 60%"),
        ]
        for tipo, alert, label in casos:
            resultado = classify(tipo, alert, {}).value
            print(f"  {label:<20} -> {resultado}")

        # Resumen
        print_header("DEMOSTRACIÓN COMPLETADA")
        tickets = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".json")]
        print(f"  Tickets generados: {len(tickets)}")
        for t in sorted(tickets):
            print(f"    - {t}")
        print()

    finally:
        listener.kill()
        listener.wait()
        print("  Listener detenido.\n")


if __name__ == "__main__":
    main()
