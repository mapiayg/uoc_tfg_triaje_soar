"""
src/fortinet/client.py
Cliente HTTP para la API REST de FortiOS con retry/backoff exponencial.

Todas las llamadas a la API del sistema pasan por esta clase.
Gestiona autenticación Bearer, SSL, timeouts y reintentos automáticos.
"""

import os
import time

import requests
import urllib3

from src.logger_config import get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)


class FortinetClient:
    """
    Cliente para la API REST de FortiOS.

    Parámetros (todos opcionales — se leen de variables de entorno si no se pasan):
        host       : IP o hostname del FortiGate (FORTI_HOST)
        token      : Token Bearer de autenticación (FORTI_TOKEN)
        verify_ssl : Verificar certificado SSL (FORTI_VERIFY_SSL). False en laboratorio.
    """

    def __init__(self, host: str = None, token: str = None, verify_ssl: bool = False):
        self.host = host or os.getenv("FORTI_HOST", "192.168.75.2")
        self.token = token or os.getenv("FORTI_TOKEN", "")
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{self.host}/api/v2"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def get(
        self,
        endpoint: str,
        params: dict = None,
        incident_id: str = None,
        max_retries: int = 3,
    ) -> dict:
        """
        Realiza una petición GET a la API REST de FortiOS.

        Implementa retry con backoff exponencial (1s, 2s, 4s) ante timeouts.
        Los errores HTTP (4xx, 5xx) y de conexión se propagan al llamador.

        Args:
            endpoint    : Ruta relativa al base_url (ej. '/monitor/vpn/ipsec')
            params      : Parámetros de query string opcionales
            incident_id : Correlation ID para el log (no afecta a la petición)
            max_retries : Número máximo de reintentos ante timeout (defecto: 3)

        Returns:
            dict con la respuesta JSON de FortiOS

        Raises:
            TimeoutError            : Si se agotan todos los reintentos
            requests.HTTPError      : Si FortiOS devuelve 4xx o 5xx
            requests.ConnectionError: Si no hay conectividad con el host
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(max_retries):
            try:
                resp = self.session.get(
                    url, params=params, verify=self.verify_ssl, timeout=15
                )
                resp.raise_for_status()
                logger.info(
                    f"API call OK: {endpoint}",
                    extra={"incident_id": incident_id},
                )
                return resp.json()

            except requests.exceptions.Timeout:
                wait = 2 ** attempt
                logger.warning(
                    f"Timeout en {endpoint}, reintento {attempt + 1}/{max_retries} en {wait}s",
                    extra={"incident_id": incident_id},
                )
                time.sleep(wait)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(
                        f"Rate limit (429) en {endpoint}, reintento {attempt + 1}/{max_retries} en {wait}s",
                        extra={"incident_id": incident_id},
                    )
                    time.sleep(wait)
                    continue
                logger.error(
                    f"HTTP error {e.response.status_code} en {endpoint}",
                    extra={"incident_id": incident_id},
                )
                raise

            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"Error de conexión en {endpoint}: {e}",
                    extra={"incident_id": incident_id},
                )
                raise

        raise TimeoutError(f"Max retries alcanzado para {endpoint}")