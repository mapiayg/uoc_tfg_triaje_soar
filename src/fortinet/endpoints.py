"""
src/fortinet/endpoints.py
Constantes de endpoints de la API REST de FortiOS utilizados por el sistema.

Todos los endpoints son relativos a la base URL: https://{FORTI_HOST}/api/v2
Documentación oficial: https://fndn.fortinet.net

Versión FortiOS validada: 7.4.x
"""

# ---------------------------------------------------------------------------
# Módulo VPN — diagnóstico de caída de túnel IPSec
# ---------------------------------------------------------------------------

# Estado de todos los túneles IPSec activos
# Respuesta: lista de túneles con name, tun_id, proxyid, rgwy, bytes
VPN_IPSEC_STATUS = "/monitor/vpn/ipsec"

# Estado de sesiones SSL-VPN activas (uso auxiliar)
VPN_SSL_STATUS = "/monitor/vpn/ssl"

# Configuración de túneles IPSec — phase1-interface
# Uso: filtrar por nombre de túnel con params={'filter': 'name=@<tunnel_name>'}
VPN_IPSEC_CONFIG = "/cmdb/vpn.ipsec/phase1-interface"

# Estado de interfaces de red
# Respuesta: lista de interfaces con name, link, speed, ip
SYSTEM_INTERFACE_STATUS = "/monitor/system/interface"

# ---------------------------------------------------------------------------
# Módulo Saturación — diagnóstico de CPU/memoria
# ---------------------------------------------------------------------------

# Uso de recursos del sistema: CPU, memoria, sesiones
# Uso: params={'resource': 'cpu,mem,session'}
# Uso: params={'resource': 'process'} para top procesos
SYSTEM_RESOURCE_USAGE = "/monitor/system/resource/usage"

# Contador de sesiones activas del firewall
# Uso: params={'count': 1} para obtener sólo el total
FIREWALL_SESSION_COUNT = "/monitor/firewall/session"

# ---------------------------------------------------------------------------
# Diagnóstico auxiliar
# ---------------------------------------------------------------------------

# Estado general del sistema (versión FortiOS, hostname, uptime)
# Usado por test_api_connection.py para verificar autenticación
SYSTEM_STATUS = "/monitor/system/status"

# Tabla de rutas IPv4
ROUTER_IPV4 = "/monitor/router/ipv4"
