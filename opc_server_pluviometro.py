import asyncio
import math
import pandas as pd
from datetime import datetime, timezone, timedelta
from asyncua import Server, Client, ua
import numpy as np
import os

# Ruta del archivo Excel
archivo_excel = r"/home/alopalm/entornos/trabajo_final/Pluvi_metroChiva_29octubre2024.xlsx"

# Leer las columnas A (hora) y B (precipitaciones) desde la fila 8
df = pd.read_excel(archivo_excel, usecols=[0, 1], skiprows=7, nrows=289, engine='openpyxl')

# Convertir la columna B (precipitaciones) en una lista de valores numéricos
precipitaciones_lista = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().tolist()
precipitaciones_lista = [round(math.ceil(valor * 10) / 10, 1) for valor in precipitaciones_lista]

# Crear el servidor OPC UA
servidor = Server()
servidor.set_endpoint("opc.tcp://localhost:4841/entornos/bla/pluviometro")

async def registrar_espacio_nombres():
    uri = "http://www.epsa.upv.es/entornos/bla/pluviometro"
    return await servidor.register_namespace(uri)

class SubscriptionHandler:
    def __init__(self, precipitaciones, hora_variable, precipitacion_hora):
        self.precipitaciones = precipitaciones
        self.hora_variable = hora_variable
        self.precipitacion_hora = precipitacion_hora
        self.acumulacion_precipitaciones = 0.0
        self.ultima_hora_acumulada = None

    async def datachange_notification(self, node, val, data):
        """Manejador de cambios de datos."""
        print(f"Hora simulada recibida: {val}")
        hora_simulada = val.replace(tzinfo=None)  # Eliminar la zona horaria

        # Buscar el valor de precipitaciones correspondiente
        encontrado = False
        for i, fila in df.iterrows():
            hora_fila = fila.iloc[0]
            if isinstance(hora_fila, pd.Timestamp):
                hora_fila = hora_fila.replace(second=0, microsecond=0)
            else:
                hora_fila = pd.to_datetime(hora_fila).replace(second=0, microsecond=0)

            if hora_fila == hora_simulada:
                valor_precipitacion = precipitaciones_lista[i]

                # Actualizar los valores en el servidor
                await self.precipitaciones.write_value(valor_precipitacion)
                await self.hora_variable.write_value(val)

                print(f"Actualizando precipitaciones a: {valor_precipitacion} mm/h")
                print(f"Hora actualizada a: {hora_simulada}")

                # Actualizar acumulación
                if self.ultima_hora_acumulada is None:
                    self.ultima_hora_acumulada = hora_simulada

                if hora_simulada - self.ultima_hora_acumulada < timedelta(hours=1):
                    self.acumulacion_precipitaciones += valor_precipitacion
                else:
                    self.acumulacion_precipitaciones = valor_precipitacion
                    self.ultima_hora_acumulada = hora_simulada

                await self.precipitacion_hora.write_value(round(self.acumulacion_precipitaciones, 1))
                print(f"Acumulación de precipitaciones: {round(self.acumulacion_precipitaciones, 1)} mm")
                encontrado = True
                break

        if not encontrado:
            # Si no se encuentra coincidencia, enviar valores por defecto
            await self.precipitaciones.write_value(0.0)
            await self.precipitacion_hora.write_value(0.0)
            await self.hora_variable.write_value(val)
            print("No se encontró coincidencia para la hora simulada. Valores por defecto enviados.")

async def iniciar_servidor():
    """Configura e inicia el servidor."""
    await servidor.init()
    idx = await registrar_espacio_nombres()

    # Importar el XML
    try:
        print("Comprobando si el archivo XML existe:", os.path.isfile("nodo_pluviometro.xml"))
        await servidor.import_xml("nodo_pluviometro.xml")
        print("Archivo XML importado correctamente")
    except Exception as e:
        print(f"Error al importar el archivo XML: {e}")
        return

    # Verificar los nodos importados
    print("\nVerificando nodos importados:")
    try:
        objeto_pluviometro = await servidor.nodes.objects.get_child([f"{idx}:Pluviometro"])
        precipitaciones = await objeto_pluviometro.get_child([f"{idx}:Precipitaciones"])
        hora_variable = await objeto_pluviometro.get_child([f"{idx}:Hora"])
        precipitacion_hora = await objeto_pluviometro.get_child([f"{idx}:Precipitaciones_mm_h"])

        print(f"Nodo Pluviometro encontrado: {objeto_pluviometro}")
        print(f"Nodo Precipitaciones encontrado: {precipitaciones}")
        print(f"Nodo Hora encontrado: {hora_variable}")
        print(f"Nodo Precipitaciones_mm_h encontrado: {precipitacion_hora}")

    except Exception as e:
        print(f"Error al verificar nodos importados: {e}")
        return

    await servidor.start()
    print("Servidor OPC UA del Pluviómetro iniciado en:", servidor.endpoint)

    return precipitaciones, hora_variable, precipitacion_hora

async def main():
    precipitaciones, hora_variable, precipitacion_hora = await iniciar_servidor()

    # Conectar al servidor temporal como cliente
    url_servidor_temporal = "opc.tcp://localhost:4840/"
    cliente_temporal = Client(url_servidor_temporal)

    try:
        async with cliente_temporal:
            print("Conectado al servidor temporal.")

            # Obtener el nodo de hora simulada
            nodo_hora_simulada = cliente_temporal.get_node("ns=2;s=HoraSimulada")
            print(f"Nodo HoraSimulada encontrado: {nodo_hora_simulada}")

            # Crear manejador de suscripciones
            handler = SubscriptionHandler(precipitaciones, hora_variable, precipitacion_hora)

            # Crear suscripción
            subscription = await cliente_temporal.create_subscription(100, handler)
            await subscription.subscribe_data_change(nodo_hora_simulada)
            await asyncio.Future()  # Mantener el servidor en ejecución

    except KeyboardInterrupt:
        print("Servidor detenido.")
    finally:
        await cliente_temporal.disconnect()
        await servidor.stop()
        print("Servidor del Pluviómetro detenido.")

# Corre el código solo si es el archivo principal
if __name__ == "__main__":
    asyncio.run(main())
