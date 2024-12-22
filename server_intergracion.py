import asyncio
import logging
from datetime import datetime, timezone
from asyncua import Client, Server, ua

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("integracion")

# Configuración de las URLs de los servidores
PLUVIOMETRO_URL = "opc.tcp://localhost:4841/es/upv/epsa/entornos/bla/pluviometro/"
AFORO_URL = "opc.tcp://localhost:4842/es/upv/epsa/entornos/bla/estacion_aforo/"
TEMPORAL_URL = "opc.tcp://localhost:4840/es/upv/epsa/entornos/bla/temporal/"
INTEGRACION_URL = "opc.tcp://localhost:4850/integracion/"

class SubscriptionHandler:
    def __init__(self, server_vars, servidor):
        self.server_vars = server_vars
        self.servidor = servidor
        self.last_alert_state = False

    async def trigger_alert_event(self, precipitaciones_hora, caudal, estado_alerta):
        # Crear y configurar un evento personalizado
        event_generator = await self.servidor.get_event_generator(self.server_vars["alerta_event_type"], self.server_vars["integracion"])
        event_generator.event.Message = ua.LocalizedText(f"Estado de alerta {'activado' if estado_alerta else 'desactivado'}")
        event_generator.event.Severity = 100 if estado_alerta else 0
        event_generator.event.Time = datetime.now(timezone.utc)
        event_generator.event.Precipitaciones = precipitaciones_hora
        event_generator.event.Caudal = caudal
        event_generator.event.Estado = estado_alerta

        # Emitir el evento
        await event_generator.trigger()
        _logger.info(f"Evento emitido: Estado de alerta {'activado' if estado_alerta else 'desactivado'}.")

    async def datachange_notification(self, node, val, data):
        _logger.info(f"DataChange en nodo {node}, nuevo valor: {val}")
        if node == self.server_vars["temporal_hora_simulada"]:
            await self.server_vars["integracion_hora_simulada"].write_value(val)
        elif node == self.server_vars["pluviometro_precipitaciones"]:
            await self.server_vars["integracion_precipitaciones"].write_value(val)
        elif node == self.server_vars["pluviometro_precipitaciones_hora"]:
            await self.server_vars["integracion_precipitaciones_hora"].write_value(val)
        elif node == self.server_vars["aforo_caudal"]:
            await self.server_vars["integracion_caudal"].write_value(val)

        precipitaciones_hora = await self.server_vars["integracion_precipitaciones_hora"].read_value()
        caudal = await self.server_vars["integracion_caudal"].read_value()
        estado_alerta = precipitaciones_hora > 50 and caudal > 150

        # Emitir evento si cambia el estado de alerta
        if estado_alerta != self.last_alert_state:
            await self.trigger_alert_event(precipitaciones_hora, caudal, estado_alerta)
            self.last_alert_state = estado_alerta


async def main():
    # Crear servidor integrado
    servidor = Server()
    servidor.set_endpoint(INTEGRACION_URL)
    await servidor.init()
    uri = "http://www.epsa.upv.es/entornos/integracion"
    idx = await servidor.register_namespace(uri)

    # Importar el XML
    try:
        _logger.info("Importando archivo XML...")
        await servidor.import_xml("nodo_integracion.xml")
        _logger.info("Archivo XML importado correctamente.")
    except Exception as e:
        _logger.error(f"Error al importar el archivo XML: {e}")
        return

    # Obtener nodos desde el XML importado
    try:
        integracion = await servidor.nodes.objects.get_child([f"{idx}:Integracion"])
        precipitaciones = await integracion.get_child([f"{idx}:Precipitaciones"])
        precipitaciones_mm_h = await integracion.get_child([f"{idx}:Precipitaciones_mm_h"])
        caudal = await integracion.get_child([f"{idx}:Caudal_m3_s"])
        hora_simulada = await integracion.get_child([f"{idx}:HoraSimulada"])
        alerta_event_type = servidor.get_node(f"ns={idx};i=5000")  # Tipo de evento importado del XML

        _logger.info("Nodos obtenidos correctamente del XML.")
    except Exception as e:
        _logger.error(f"Error al obtener nodos del XML: {e}")
        return

    await servidor.start()
    _logger.info(f"Servidor de integración iniciado en {INTEGRACION_URL}")

    # Conexión a los servidores de origen
    async with Client(PLUVIOMETRO_URL) as pluviometro_client, \
               Client(AFORO_URL) as aforo_client, \
               Client(TEMPORAL_URL) as temporal_client:

        _logger.info("Conectado a los servidores de origen.")

        # Obtener nodos del servidor de origen
        try:
            pluviometro_precipitaciones = pluviometro_client.get_node("ns=2;s=Precipitaciones")
            pluviometro_precipitaciones_hora = pluviometro_client.get_node("ns=2;s=Precipitaciones_mm_h")
            aforo_caudal = aforo_client.get_node("ns=2;i=2")
            temporal_hora_simulada = temporal_client.get_node("ns=2;s=HoraSimulada")

            _logger.info("Nodos del servidor de origen obtenidos correctamente.")
        except Exception as e:
            _logger.error(f"Error al obtener nodos de los servidores de origen: {e}")
            return

        # Crear manejador de suscripciones
        server_vars = {
            "pluviometro_precipitaciones": pluviometro_precipitaciones,
            "pluviometro_precipitaciones_hora": pluviometro_precipitaciones_hora,
            "aforo_caudal": aforo_caudal,
            "temporal_hora_simulada": temporal_hora_simulada,
            "integracion_precipitaciones": precipitaciones,
            "integracion_precipitaciones_hora": precipitaciones_mm_h,
            "integracion_caudal": caudal,
            "integracion_hora_simulada": hora_simulada,
            "integracion": integracion,
            "alerta_event_type": alerta_event_type,
        }
        handler = SubscriptionHandler(server_vars, servidor)

        # Crear suscripciones
        pluviometro_subscription = await pluviometro_client.create_subscription(100, handler)
        aforo_subscription = await aforo_client.create_subscription(100, handler)
        temporal_subscription = await temporal_client.create_subscription(100, handler)

        # Suscribirse a los nodos
        await pluviometro_subscription.subscribe_data_change(pluviometro_precipitaciones)
        await pluviometro_subscription.subscribe_data_change(pluviometro_precipitaciones_hora)
        await aforo_subscription.subscribe_data_change(aforo_caudal)
        await temporal_subscription.subscribe_data_change(temporal_hora_simulada)

        # Mantener el servidor activo
        _logger.info("Esperando actualizaciones desde los servidores de origen...")
        await asyncio.Future()  # Esperar indefinidamente

    await servidor.stop()
    _logger.info("Servidor de integración detenido.")

if __name__ == "__main__":
    asyncio.run(main())
    
