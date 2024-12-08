import pandas as pd
import asyncio
from asyncua import Server, Client

ARCHIVO_CSV = "/home/alopalm/entornos/trabajo_final/cincominutales-rambla-poyo-29102024.csv"
ENDPOINT_OPC_UA = "opc.tcp://localhost:4842/es/upv/epsa/entornos/bla/estacion_aforo/"
URI = "http://www.epsa.upv.es/entornos"
URL_SERVIDOR_TEMPORAL = "opc.tcp://localhost:4840/freeopcua/server/"

def cargar_datos_csv(ruta_csv):
    df = pd.read_csv(ruta_csv)
    df['Caudal'] = df['Caudal'].replace(',', '.', regex=True)
    df['Caudal'] = pd.to_numeric(df['Caudal'], errors='coerce')
    df['Estado'] = df['Estado'].fillna('Desconocido')
    return df

async def configurar_servidor(endpoint, uri):
    servidor = Server()
    await servidor.init()
    servidor.set_endpoint(endpoint)
    idx = await servidor.register_namespace(uri)

    estacion_aforo = await servidor.nodes.objects.add_object(idx, "EstacionAforo")

    caudal = await estacion_aforo.add_variable(idx, "Caudal_m3_s", 0.0)
    estado = await estacion_aforo.add_variable(idx, "Estado", "Desconocido")
    hora_variable = await estacion_aforo.add_variable(idx, "Hora", "")
    
    for variable in [caudal, estado, hora_variable]:
        await variable.set_writable()

    return servidor, caudal, estado, hora_variable

async def leer_hora_simulada(cliente):
    nodo_hora_simulada = cliente.get_node("ns=2;i=2")
    hora_simulada = await nodo_hora_simulada.read_value()
    return pd.to_datetime(hora_simulada)

async def actualizar_variables(caudal_var, estado_var, hora_var, df, hora_simulada):
    fila = df[df['Fecha'] == hora_simulada.strftime('%Y-%m-%d %H:%M:%S')]
    if not fila.empty:
        caudal_valor = fila['Caudal'].iloc[0]
        estado_valor = fila['Estado'].iloc[0]

        await caudal_var.write_value(caudal_valor)
        await estado_var.write_value(estado_valor)
        await hora_var.write_value(hora_simulada.strftime('%H:%M:%S'))

        print(f"Hora: {hora_simulada}, Caudal: {caudal_valor}, Estado: {estado_valor}")
    else:
        print(f"No se encontraron datos para la hora simulada: {hora_simulada}")

async def main():
    df = cargar_datos_csv(ARCHIVO_CSV)

    servidor, caudal_var, estado_var, hora_var = await configurar_servidor(ENDPOINT_OPC_UA, URI)
    await servidor.start()
    print(f"Servidor OPC UA iniciado en: {servidor.endpoint}")

    cliente_temporal = Client(URL_SERVIDOR_TEMPORAL)
    await cliente_temporal.connect()

    try:
        while True:
            hora_simulada = await leer_hora_simulada(cliente_temporal)
            await actualizar_variables(caudal_var, estado_var, hora_var, df, hora_simulada)
            await asyncio.sleep(0.2)
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario.")
    finally:
        await cliente_temporal.disconnect()
        await servidor.stop()

if __name__ == "__main__":
    asyncio.run(main())
