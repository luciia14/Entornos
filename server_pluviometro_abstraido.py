import time
import pandas as pd
import math
import asyncio
from asyncua import Server, Client

EXCEL_PATH = "/home/alopalm/entornos/trabajo_final/Pluvi_metroChiva_29octubre2024.xlsx"
TEMPORAL_SERVER_URL = "opc.tcp://localhost:4840/es/upv/epsa/entornos/bla/temporal/"
PLUVIOMETRO_SERVER_URL = "opc.tcp://localhost:4841/es/upv/epsa/entornos/bla/pluviometro/"
NAMESPACE_URI = "http://www.epsa.upv.es/entornos"
SLEEP_INTERVAL = 1

def cargar_datos_excel(ruta_excel):
    df = pd.read_excel(ruta_excel, usecols=[0, 1], skiprows=7, nrows=289, engine='openpyxl')
    precipitaciones_lista = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().tolist()
    precipitaciones_lista = [round(math.ceil(valor * 10) / 10, 1) for valor in precipitaciones_lista]
    return df, precipitaciones_lista

def buscar_precipitacion_por_hora(df, precipitaciones, hora_simulada):
    for i, fila in df.iterrows():
        hora_fila = pd.to_datetime(fila.iloc[0]).replace(second=0, microsecond=0)
        if hora_fila.time() == hora_simulada.time():
            return precipitaciones[i]
    return None

async def iniciar_servidor_pluviometro():
    servidor = Server()
    servidor.set_endpoint(PLUVIOMETRO_SERVER_URL)
    await servidor.init()
    idx = await servidor.register_namespace(NAMESPACE_URI)

    pluviometro = await servidor.nodes.objects.add_object(idx, "Pluviometro")
    precipitaciones = await pluviometro.add_variable(idx, "Precipitaciones_mm_h", 0.0)
    await precipitaciones.set_writable()
    hora_variable = await pluviometro.add_variable(idx, "Hora", "")
    await hora_variable.set_writable()

    await servidor.start()
    print(f"Servidor OPC UA del Pluviómetro iniciado en {PLUVIOMETRO_SERVER_URL}")
    return servidor, precipitaciones, hora_variable

async def conectar_servidor_temporal():
    cliente = Client(TEMPORAL_SERVER_URL)
    await cliente.connect()
    nodo_hora_simulada = cliente.get_node("ns=2;i=2")
    print(f"Conectado al servidor temporal en {TEMPORAL_SERVER_URL}")
    return cliente, nodo_hora_simulada

async def main():
    df, precipitaciones_lista = cargar_datos_excel(EXCEL_PATH)
    servidor, nodo_precipitaciones, nodo_hora = await iniciar_servidor_pluviometro()
    cliente_temporal, nodo_hora_simulada = await conectar_servidor_temporal()

    try:
        while True:
            hora_simulada = await nodo_hora_simulada.read_value()
            hora_simulada = hora_simulada.replace(tzinfo=None)

            valor_precipitacion = buscar_precipitacion_por_hora(df, precipitaciones_lista, hora_simulada)

            if valor_precipitacion is not None:
                await nodo_precipitaciones.write_value(valor_precipitacion)
                await nodo_hora.write_value(hora_simulada.strftime('%H:%M:%S'))
                print(f"Precipitaciones: {valor_precipitacion} mm/h | Hora: {hora_simulada.strftime('%H:%M:%S')}")
            else:
                print(f"No se encontró una coincidencia para la hora simulada: {hora_simulada}")

            await asyncio.sleep(SLEEP_INTERVAL)

    except KeyboardInterrupt:
        print("Servidor detenido manualmente.")
    finally:
        await cliente_temporal.disconnect()
        await servidor.stop()
        print("Servidor OPC UA del Pluviómetro detenido.")

if __name__ == "__main__":
    asyncio.run(main())
