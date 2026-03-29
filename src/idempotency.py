# src/idempotency.py
# Mecanismo de deduplicación de webhooks en memoria.
# Para producción, sustituir por Redis o base de datos persistente.
import time
from threading import Lock

# Almacén en memoria: {incident_id: timestamp_recepcion}
_processed: dict = {}
_lock = Lock()
TTL_SECONDS = 3600  # Considerar duplicado durante 1 hora


def is_duplicate(incident_id: str) -> bool:
    """
    Devuelve True si el incident_id ya fue procesado recientemente.
    Efecto secundario: si no es duplicado, lo registra para futuros checks.
    """
    _cleanup_expired()
    with _lock:
        if incident_id in _processed:
            return True
        _processed[incident_id] = time.monotonic()
        return False


def reset_for_testing():
    """Limpia el registro. Solo para uso en tests."""
    with _lock:
        _processed.clear()


def _cleanup_expired():
    """Elimina entradas expiradas para evitar memory leak."""
    now = time.monotonic()
    with _lock:
        expired = [k for k, v in _processed.items() if now - v > TTL_SECONDS]
        for k in expired:
            del _processed[k]
