# src/listener.py
from flask import Flask, request, jsonify
import os
import hashlib
import hmac
from src.parser import parse_and_validate_webhook
from src.router import route_alert
from src.idempotency import is_duplicate
from src.logger_config import get_logger

app = Flask(__name__)
app.json.ensure_ascii = False
logger = get_logger(__name__)

WEBHOOK_SECRET = os.getenv('LISTENER_SECRET', '')


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verificación HMAC opcional para autenticar el origen del webhook."""
    if not WEBHOOK_SECRET:
        return True  # Sin secret configurado, acepta todo (modo laboratorio)
    expected = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f'sha256={expected}', signature)


@app.route('/webhook', methods=['POST'])
def receive_webhook():
    # 1. Verificar firma HMAC (si LISTENER_SECRET está configurado)
    sig = request.headers.get('X-Signature', '')
    if not verify_signature(request.data, sig):
        logger.warning('Webhook rechazado: firma inválida')
        return jsonify({'error': 'Invalid signature'}), 401

    # 2. Parsear y validar estructura del payload
    try:
        alert = parse_and_validate_webhook(request.json)
    except ValueError as e:
        logger.error(f'Webhook malformado: {e}')
        return jsonify({'error': str(e)}), 400

    # 3. Verificar idempotencia (deduplicación)
    incident_id = alert['incident_id']
    if is_duplicate(incident_id):
        logger.info(
            f'Webhook duplicado ignorado',
            extra={'incident_id': incident_id}
        )
        return jsonify({'status': 'duplicate_ignored', 'incident_id': incident_id}), 200

    # 4. Enrutar al módulo de diagnóstico (stub esta semana, real en semana 5)
    logger.info('Webhook aceptado, iniciando diagnóstico', extra={'incident_id': incident_id})
    result = route_alert(alert)

    return jsonify({'status': 'processed', 'incident_id': incident_id}), 202


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check — útil para verificar que el servidor está en marcha."""
    return jsonify({'status': 'ok', 'service': 'triaje-soar-listener'}), 200
