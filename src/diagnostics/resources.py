"""
src/diagnostics/resources.py
Módulo de diagnóstico para saturación de recursos (CPU/memoria).

Playbook: ejecuta 3 consultas a la API REST de FortiOS y genera un resumen
estructurado con el consumo de recursos, las sesiones activas y el estado de interfaces.

Uso:
    from src.diagnostics.resources import ResourceDiagnostic
    diag = ResourceDiagnostic()
    result = diag.run(alert_dict)
"""

import time

from src.fortinet.client import FortinetClient
from src.fortinet.endpoints import (
    FIREWALL_SESSION_COUNT,
    SYSTEM_INTERFACE_STATUS,
    SYSTEM_RESOURCE_USAGE,
)
from src.logger_config import get_logger

logger = get_logger(__name__)


class ResourceDiagnostic:
    """
    Diagnóstico de saturación de recursos (CPU/memoria).

    Ejecuta 3 consultas diagnósticas independientes. Si una falla, las demás
    continúan y el error queda registrado en el campo 'errors' del resultado.
    """

    def __init__(self, client: FortinetClient = None):
        self.client = client or FortinetClient()

    def run(self, alert: dict) -> dict:
        iid = alert["incident_id"]
        resource_type = alert.get("resource_type", "cpu")
        threshold = alert.get("threshold_value", 0)
        start_time = time.time()

        logger.info(
            f"Iniciando diagnóstico de saturación: {resource_type} al {threshold}%",
            extra={"incident_id": iid},
        )

        raw_data = {}
        errors = []

        # --- Consulta 1: Consumo de recursos (CPU, memoria) ---
        try:
            raw_data["resource_usage"] = self.client.get(
                SYSTEM_RESOURCE_USAGE, incident_id=iid
            )
        except Exception as e:
            errors.append(f"resource_usage: {e}")
            raw_data["resource_usage"] = None

        # --- Consulta 2: Sesiones activas del firewall ---
        try:
            raw_data["session_count"] = self.client.get(
                FIREWALL_SESSION_COUNT, incident_id=iid
            )
        except Exception as e:
            errors.append(f"session_count: {e}")
            raw_data["session_count"] = None

        # --- Consulta 3: Estado de interfaces de red ---
        try:
            raw_data["interfaces"] = self.client.get(
                SYSTEM_INTERFACE_STATUS, incident_id=iid
            )
        except Exception as e:
            errors.append(f"interfaces: {e}")
            raw_data["interfaces"] = None

        summary = self._analyze(resource_type, threshold, raw_data)
        processing_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Diagnóstico saturación completado en {processing_ms}ms. Errores: {len(errors)}",
            extra={"incident_id": iid},
        )

        return {
            "diagnostic_type": "resource_saturation",
            "resource_type": resource_type,
            "threshold_value": threshold,
            "diagnostic_summary": summary,
            "raw_data": raw_data,
            "processing_time_ms": processing_ms,
            "errors": errors,
        }

    def _analyze(self, resource_type: str, threshold: float, raw_data: dict) -> str:
        """
        Genera un diagnóstico interpretado: compara el umbral declarado en la
        alerta con el valor real observado y emite un veredicto operativo
        (alerta confirmada, falso positivo o pico transitorio).
        """
        # Extraer valor real del recurso afectado
        observed = None
        cpu_current = None
        mem_current = None

        usage = raw_data.get("resource_usage")
        if usage and "results" in usage:
            results = usage["results"]
            if isinstance(results, dict):
                cpu_data = results.get("cpu")
                mem_data = results.get("mem")
                if cpu_data and isinstance(cpu_data, list) and len(cpu_data) > 0:
                    cpu_current = cpu_data[0].get("current")
                if mem_data and isinstance(mem_data, list) and len(mem_data) > 0:
                    mem_current = mem_data[0].get("current")

        if resource_type == "cpu":
            observed = cpu_current
        elif resource_type == "mem":
            observed = mem_current

        # Datos auxiliares para el contexto
        sessions = None
        sess_data = raw_data.get("session_count")
        if sess_data and "results" in sess_data:
            count = sess_data["results"]
            if isinstance(count, dict):
                sessions = count.get("count")

        # Veredicto: comparar valor real con umbral declarado
        if observed is None:
            verdict = (
                f"No se pudo obtener el valor real de {resource_type.upper()} del firewall "
                f"(consultar campo 'errors' del ticket). Alerta original: {threshold}%."
            )
        elif observed >= threshold:
            verdict = (
                f"Alerta CONFIRMADA: el firewall reporta {resource_type.upper()} "
                f"al {observed}%, igual o por encima del umbral declarado en la alerta ({threshold}%)."
            )
        elif observed >= threshold * 0.7:
            verdict = (
                f"Alerta DEGRADADA pero no en umbral crítico: {resource_type.upper()} "
                f"al {observed}% (umbral declarado {threshold}%). Posible pico parcialmente resuelto."
            )
        else:
            verdict = (
                f"Probable FALSO POSITIVO o pico ya resuelto: {resource_type.upper()} "
                f"al {observed}%, muy por debajo del umbral declarado en la alerta ({threshold}%)."
            )

        # Contexto adicional
        context = []
        if cpu_current is not None and resource_type != "cpu":
            context.append(f"CPU al {cpu_current}%")
        if mem_current is not None and resource_type != "mem":
            context.append(f"memoria al {mem_current}%")
        if sessions is not None:
            context.append(f"{sessions} sesiones activas")

        if context:
            return f"{verdict} Contexto del firewall: {', '.join(context)}."
        return verdict
