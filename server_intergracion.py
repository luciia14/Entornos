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
    def __init__(self, server_vars):
        self.server_vars = server_vars

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
        await self.server_vars["integracion_estado_alerta"].write_value(estado_alerta)
        _logger.info(f"Estado de alerta actualizado: {'Activado' if estado_alerta else 'Desactivado'}")

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
        estado_alerta = await integracion.get_child([f"{idx}:EstadoAlerta"])

        _logger.info(f"Nodo Integracion encontrado: {integracion}")
        _logger.info(f"Nodo Precipitaciones encontrado: {precipitaciones}")
        _logger.info(f"Nodo Precipitaciones_mm_h encontrado: {precipitaciones_mm_h}")
        _logger.info(f"Nodo Caudal encontrado: {caudal}")
        _logger.info(f"Nodo HoraSimulada encontrado: {hora_simulada}")
        _logger.info(f"Nodo EstadoAlerta encontrado: {estado_alerta}")
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
            aforo_caudal = aforo_client.get_node("ns=2;i=2")  # Reemplaza esto con el NodeId correcto

            try:
                browse_name = await aforo_caudal.read_browse_name()
                _logger.info(f"Nodo Caudal encontrado: {browse_name}")
            except Exception as e:
                _logger.error(f"Error al verificar el nodo 'aforo_caudal': {e}")
                return

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
            "integracion_estado_alerta": estado_alerta,
        }
        handler = SubscriptionHandler(server_vars)

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

