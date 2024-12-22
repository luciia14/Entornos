import pandas as pd
import asyncio
import logging
from asyncua import Server, Client, Node, ua
from datetime import datetime, timezone
import os

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("estacion_aforo")

# Ruta del archivo CSV
archivo_csv = "/home/alopalm/entornos/trabajo_final/cincominutales-rambla-poyo-29102024.csv"

# Leer y preparar los datos del archivo CSV
df = pd.read_csv(archivo_csv)

# Convertir las fechas del archivo a datetime UTC
df['Fecha'] = pd.to_datetime(df['Fecha']).dt.tz_localize(timezone.utc)

# Limpiar y preparar los datos
df['Caudal'] = df['Caudal'].replace(',', '.', regex=True)  # Reemplazar comas por puntos
df['Caudal'] = pd.to_numeric(df['Caudal'], errors='coerce')  # Convertir a números, NaN si no se puede
df['Estado'] = df['Estado'].fillna('Desconocido')  # Rellenar valores faltantes


class SubscriptionHandler:

    def __init__(self, caudal, estado, hora_variable):
        self.caudal = caudal
        self.estado = estado
        self.hora_variable = hora_variable

    async def datachange_notification(self, node: Node, val, data):

        # Asegurarse de que está en UTC
        if val.tzinfo is None:
            hora_simulada = val.replace(tzinfo=timezone.utc)
        else:
            hora_simulada = val.astimezone(timezone.utc)

        # Actualizar directamente la hora en el servidor de estación de aforo
        await self.hora_variable.write_value(hora_simulada)

        # Buscar la fila correspondiente en el DataFrame
        fila = df[df['Fecha'] == hora_simulada]

        if not fila.empty:
            caudal_valor = fila['Caudal'].iloc[0]
            estado_valor = fila['Estado'].iloc[0]

            # Actualizar los valores en el servidor
            await self.caudal.write_value(caudal_valor)
            await self.estado.write_value(estado_valor)

            _logger.info(f"Actualizado: Hora={hora_simulada}, Caudal={caudal_valor}, Estado={estado_valor}")
        else:
            _logger.warning(f"No se encontraron datos para la hora simulada: {hora_simulada}")


async def iniciar_servidor():

    servidor = Server()
    servidor.set_endpoint("opc.tcp://localhost:4842/entornos/bla/estacion_aforo/")
    await servidor.init()

    uri = "http://www.epsa.upv.es/entornos/bla/estacion"
    idx = await servidor.register_namespace(uri)
    namespaces = await servidor.get_namespace_array()
    print("Namespaces registrados:", namespaces)
    # Importar el XML
    try:
        print("Comprobando si el archivo XML existe:", os.path.isfile("nodo_estacionaforo.xml"))
        await servidor.import_xml("nodo_estacionaforo.xml")
        print("Archivo XML importado correctamente")
    except Exception as e:
        print(f"Error al importar el archivo XML: {e}")
        return

    # Instanciar el ObjectType después de importar el XML
    try:
        # Crear una instancia de `EstacionAforoType`
        nodo_estacion_aforo_type = await servidor.nodes.base_object_type.get_child([f"{idx}:EstacionAforoType"])
        estacion_aforo = await servidor.nodes.objects.add_object(
            idx, "EstacionAforo", objecttype=nodo_estacion_aforo_type
        )

        # Obtener referencias a las variables del nodo instanciado
        caudal = await estacion_aforo.get_child([f"{idx}:Caudal_m3_s"])
        estado = await estacion_aforo.get_child([f"{idx}:Estado"])
        hora_variable = await estacion_aforo.get_child([f"{idx}:Hora"])

        print(f"Nodo EstacionAforo encontrado: {estacion_aforo}")
        print(f"Nodo Caudal encontrado: {caudal}")
        print(f"Nodo Estado encontrado: {estado}")
        print(f"Nodo Hora encontrado: {hora_variable}")

    except Exception as e:
        print(f"Error al instanciar o verificar nodos del ObjectType: {e}")
        return

    await servidor.start()
    print(f"Servidor OPC UA iniciado en {servidor.endpoint}")

    return servidor, caudal, estado, hora_variable

async def main():
    servidor, caudal, estado, hora_variable = await iniciar_servidor()

    # Conectar al servidor temporal
    url_servidor_temporal = "opc.tcp://localhost:4840/freeopcua/server/"
    cliente_temporal = Client(url_servidor_temporal)

    try:
        async with cliente_temporal:
            # Obtener el nodo de hora simulada
            nodo_hora_simulada = cliente_temporal.get_node("ns=2;s=HoraSimulada")
            _logger.info(f"Nodo de hora simulada obtenido: {nodo_hora_simulada}")

            # Crear el manejador de suscripciones
            handler = SubscriptionHandler(caudal, estado, hora_variable)

            # Crear una suscripción y suscribirse al nodo de hora simulada
            subscription = await cliente_temporal.create_subscription(100, handler)
            await subscription.subscribe_data_change(nodo_hora_simulada)

            await asyncio.Future()  # Esperar indefinidamente

    except KeyboardInterrupt:
        _logger.info("Servidor detenido manualmente.")
    finally:
        await servidor.stop()
        _logger.info("Servidor OPC UA de la estación de aforo detenido.")


if __name__ == "__main__":
    asyncio.run(main())

