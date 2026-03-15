"""
test_api_connection.py
Verificación rápida de conectividad con la API REST de FortiOS.

Uso:
    python test_api_connection.py

Requiere que el fichero .env esté configurado con FORTI_HOST y FORTI_TOKEN,
o que las variables de entorno estén definidas en el sistema.

Semana 2: ejecutar este script una vez configurado el API user en FortiOS
para confirmar que el entorno de laboratorio está operativo.
"""

import os
import sys
import json

try:
    import requests
    import urllib3
except ImportError:
    print("[ERROR] Dependencias no instaladas. Ejecuta: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv opcional; también acepta variables de entorno del sistema

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FORTI_HOST = os.getenv("FORTI_HOST", "192.168.100.1")
FORTI_TOKEN = os.getenv("FORTI_TOKEN", "")
VERIFY_SSL = os.getenv("FORTI_VERIFY_SSL", "false").lower() == "true"


def check_connectivity() -> bool:
    """Comprueba que el host de FortiOS es alcanzable por red."""
    import socket
    try:
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((FORTI_HOST, 443))
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def test_system_status() -> dict:
    """Consulta el endpoint de estado del sistema (no requiere autenticación completa)."""
    url = f"https://{FORTI_HOST}/api/v2/monitor/system/status"
    headers = {"Authorization": f"Bearer {FORTI_TOKEN}"}
    response = requests.get(url, headers=headers, verify=VERIFY_SSL, timeout=10)
    response.raise_for_status()
    return response.json()


def test_vpn_endpoint() -> dict:
    """Consulta el endpoint de túneles IPSec (endpoint clave para el módulo VPN)."""
    url = f"https://{FORTI_HOST}/api/v2/monitor/vpn/ipsec"
    headers = {"Authorization": f"Bearer {FORTI_TOKEN}"}
    response = requests.get(url, headers=headers, verify=VERIFY_SSL, timeout=10)
    response.raise_for_status()
    return response.json()


def test_resource_endpoint() -> dict:
    """Consulta el endpoint de uso de recursos (endpoint clave para el módulo de saturación)."""
    url = f"https://{FORTI_HOST}/api/v2/monitor/system/resource/usage"
    headers = {"Authorization": f"Bearer {FORTI_TOKEN}"}
    response = requests.get(url, headers=headers, verify=VERIFY_SSL, timeout=10)
    response.raise_for_status()
    return response.json()


def run_checks():
    print("=" * 60)
    print("  VERIFICACIÓN DE CONECTIVIDAD — API REST FortiOS")
    print("=" * 60)
    print(f"  Host:  {FORTI_HOST}")
    print(f"  Token: {'configurado' if FORTI_TOKEN else 'NO configurado (falta en .env)'}")
    print(f"  SSL:   {'verificado' if VERIFY_SSL else 'deshabilitado (laboratorio)'}")
    print("=" * 60)

    if not FORTI_TOKEN:
        print("\n[AVISO] FORTI_TOKEN no está configurado en .env.")
        print("        Completa el token tras crear el API user en FortiOS (semana 2).")
        print("        Ejecuta de nuevo este script cuando tengas el token.\n")

    # 1. Conectividad de red
    print("\n[1/3] Verificando conectividad de red...")
    if check_connectivity():
        print(f"      OK — {FORTI_HOST}:443 accesible")
    else:
        print(f"      ERROR — No se puede alcanzar {FORTI_HOST}:443")
        print("      Verifica: VM arrancada, red Host-Only activa, IP correcta.")
        sys.exit(1)

    # 2. Estado del sistema
    print("\n[2/3] Consultando estado del sistema FortiOS...")
    try:
        data = test_system_status()
        version = data.get("version", data.get("results", {}).get("version", "desconocida"))
        print(f"      OK — FortiOS versión: {version}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("      ERROR 401 — Token inválido o sin permisos.")
            print("      Verifica que el API user tiene el perfil api-readonly asignado.")
        else:
            print(f"      ERROR HTTP {e.response.status_code}: {e.response.text}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("      ERROR — Conexión rechazada. ¿El API REST está habilitado en FortiOS?")
        sys.exit(1)

    # 3. Endpoints de diagnóstico
    print("\n[3/3] Verificando endpoints de diagnóstico...")

    endpoints_ok = 0
    for name, fn in [("vpn/ipsec", test_vpn_endpoint),
                     ("system/resource/usage", test_resource_endpoint)]:
        try:
            result = fn()
            count = len(result.get("results", []))
            print(f"      OK — /monitor/{name} ({count} resultado/s)")
            endpoints_ok += 1
        except requests.exceptions.HTTPError as e:
            print(f"      ERROR — /monitor/{name}: HTTP {e.response.status_code}")
        except Exception as e:
            print(f"      ERROR — /monitor/{name}: {e}")

    print("\n" + "=" * 60)
    if endpoints_ok == 2:
        print("  RESULTADO: Entorno de laboratorio operativo.")
        print("  El sistema puede integrarse con la API REST de FortiOS.")
    else:
        print("  RESULTADO: Conectividad parcial. Revisa los errores anteriores.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_checks()
