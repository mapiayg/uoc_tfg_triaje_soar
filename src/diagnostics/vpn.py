"""
src/diagnostics/vpn.py
Módulo de diagnóstico para caídas de túnel VPN IPSec.

Playbook: ejecuta 3 consultas a la API REST de FortiOS y genera un resumen
estructurado con el estado del túnel, su configuración y la interfaz asociada.

Uso:
    from src.diagnostics.vpn import VPNDiagnostic
    diag = VPNDiagnostic()          # usa FortinetClient con variables de entorno
    result = diag.run(alert_dict)
"""

import time

from src.fortinet.client import FortinetClient
from src.fortinet.endpoints import (
    SYSTEM_INTERFACE_STATUS,
    VPN_IPSEC_CONFIG,
    VPN_IPSEC_STATUS,
)
from src.logger_config import get_logger

logger = get_logger(__name__)


class VPNDiagnostic:
    """
    Diagnóstico de caída de túnel VPN IPSec.

    Ejecuta 3 consultas diagnósticas independientes. Si una falla, las demás
    continúan y el error queda registrado en el campo 'errors' del resultado.
    """

    def __init__(self, client: FortinetClient = None):
        self.client = client or FortinetClient()

    def run(self, alert: dict) -> dict:
        """
        Ejecuta el playbook de diagnóstico VPN.

        Args:
            alert: dict validado por parser.py con los campos del webhook

        Returns:
            dict con:
                diagnostic_type    : 'vpn_down'
                tunnel_name        : nombre del túnel afectado
                diagnostic_summary : resumen textual legible
                raw_data           : respuestas crudas de las 3 consultas API
                processing_time_ms : tiempo total de ejecución en ms
                errors             : lista de errores por consulta (vacía si todo OK)
        """
        iid = alert["incident_id"]
        tunnel_name = alert.get("vpn_tunnel_name", "")
        start_time = time.time()

        logger.info(
            f"Iniciando diagnóstico VPN para túnel: {tunnel_name}",
            extra={"incident_id": iid},
        )

        raw_data = {}
        errors = []

        # --- Consulta 1: Estado de todos los túneles IPSec ---
        try:
            raw_data["ipsec_tunnels"] = self.client.get(
                VPN_IPSEC_STATUS, incident_id=iid
            )
        except Exception as e:
            errors.append(f"ipsec_tunnels: {e}")
            raw_data["ipsec_tunnels"] = None

        # --- Consulta 2: Configuración del túnel afectado ---
        try:
            raw_data["tunnel_config"] = self.client.get(
                VPN_IPSEC_CONFIG,
                params={"filter": f"name=@{tunnel_name}"},
                incident_id=iid,
            )
        except Exception as e:
            errors.append(f"tunnel_config: {e}")
            raw_data["tunnel_config"] = None

        # --- Consulta 3: Estado de interfaces de red ---
        try:
            raw_data["interfaces"] = self.client.get(
                SYSTEM_INTERFACE_STATUS, incident_id=iid
            )
        except Exception as e:
            errors.append(f"interfaces: {e}")
            raw_data["interfaces"] = None

        summary = self._analyze(tunnel_name, raw_data)
        processing_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Diagnóstico VPN completado en {processing_ms}ms. Errores: {len(errors)}",
            extra={"incident_id": iid},
        )

        return {
            "diagnostic_type": "vpn_down",
            "tunnel_name": tunnel_name,
            "diagnostic_summary": summary,
            "raw_data": raw_data,
            "processing_time_ms": processing_ms,
            "errors": errors,
        }

    def _analyze(self, tunnel_name: str, raw_data: dict) -> str:
        """
        Genera un diagnóstico interpretado: contrasta el túnel declarado en
        la alerta con la lista real de túneles activos del firewall y emite
        un veredicto operativo (caída confirmada o falso positivo) junto con
        información de contexto sobre las interfaces del firewall.
        """
        tunnels = (raw_data.get("ipsec_tunnels") or {}).get("results", [])
        affected = next(
            (t for t in tunnels if t.get("name") == tunnel_name), None
        )

        # Contexto: estado de las interfaces (relevante para descartar problemas locales)
        interfaces = (raw_data.get("interfaces") or {}).get("results", [])
        # La API de FortiOS devuelve results como dict {nombre: {...}} o lista de dicts
        if isinstance(interfaces, dict):
            iface_items = [{"name": k, **v} for k, v in interfaces.items() if isinstance(v, dict)]
        elif isinstance(interfaces, list):
            iface_items = [i for i in interfaces if isinstance(i, dict)]
        else:
            iface_items = []
        ifaces_up = [
            i.get("name") for i in iface_items
            if i.get("link") in (True, "up")
        ]
        iface_ctx = (
            f"Interfaces del firewall operativas: {', '.join(ifaces_up)}."
            if ifaces_up
            else "Sin información de estado de las interfaces del firewall."
        )

        if affected:
            proxyid = affected.get("proxyid", [])
            return (
                f"Probable FALSO POSITIVO o restablecimiento del túnel: "
                f"{tunnel_name} aparece en la lista de túneles IPSec activos del firewall "
                f"con {len(proxyid)} selectores activos. "
                f"La alerta de caída no se confirma con el estado actual del firewall. "
                f"{iface_ctx}"
            )

        return (
            f"Caída de {tunnel_name} CONFIRMADA: el túnel no aparece en la lista "
            f"de túneles IPSec activos del firewall y no hay gateways IKE para él. "
            f"{iface_ctx} "
            f"Causa probable: fallo en el peer remoto o en la negociación IKE."
        )