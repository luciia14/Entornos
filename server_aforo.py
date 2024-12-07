import pandas as pd
import asyncio
from asyncua import Server, Client

# Ruta del archivo CSV
archivo_csv = "/home/alopalm/entornos/trabajo_final/cincominutales-rambla-poyo-29102024.csv"

# Leer los datos del CSV
df = pd.read_csv(archivo_csv)

# Limpiar y preparar los datos
df['Caudal'] = df['Caudal'].replace(',', '.', regex=True)  # Reemplazar comas por puntos
df['Caudal'] = pd.to_numeric(df['Caudal'], errors='coerce')  # Convertir a números, NaN si no se puede
df['Estado'] = df['Estado'].fillna('Desconocido')  # Rellenar valores faltantes

# Crear el servidor OPC UA
servidor = Server()
servidor.set_endpoint("opc.tcp://localhost:4842/es/upv/epsa/entornos/bla/estacion_aforo/")

uri = "http://www.epsa.upv.es/entornos"

async def iniciar_servidor():
    """Función para inicializar el servidor OPC UA y crear los nodos."""
    await servidor.init()
    idx = await servidor.register_namespace(uri)

    # Crear un objeto para la estación de aforo
    estacion_aforo = await servidor.nodes.objects.add_object(idx, "EstacionAforo")

    # Crear las variables del servidor
    caudal = await estacion_aforo.add_variable(idx, "Caudal_m3_s", 0.0)
    await caudal.set_writable()
    estado = await estacion_aforo.add_variable(idx, "Estado", "Desconocido")
    await estado.set_writable()
    hora_variable = await estacion_aforo.add_variable(idx, "Hora", "")
    await hora_variable.set_writable()

    await servidor.start()
    print("Servidor OPC UA iniciado en:")
    print(servidor.endpoint)
    return caudal, estado, hora_variable

async def main():
    caudal, estado, hora_variable = await iniciar_servidor()

    # Simular conexión al servidor temporal para la hora simulada
    url_servidor_temporal = "opc.tcp://localhost:4840/freeopcua/server/"
    cliente_temporal = Client(url_servidor_temporal)
    await cliente_temporal.connect()

    try:
        nodo_hora_simulada = cliente_temporal.get_node("ns=2;i=2")  # Nodo de hora simulada
        while True:
            # Leer la hora simulada
            hora_simulada = await nodo_hora_simulada.read_value()
            hora_simulada = pd.to_datetime(hora_simulada)  # Convertir a formato datetime

            # Buscar datos coincidentes en el DataFrame
            fila = df[df['Fecha'] == hora_simulada.strftime('%Y-%m-%d %H:%M:%S')]

            if not fila.empty:
                caudal_valor = fila['Caudal'].iloc[0]
                estado_valor = fila['Estado'].iloc[0]

                # Actualizar valores en el servidor
                await caudal.write_value(caudal_valor)
                await estado.write_value(estado_valor)
                await hora_variable.write_value(hora_simulada.strftime('%H:%M:%S'))

                print(f"Hora: {hora_simulada}, Caudal: {caudal_valor}, Estado: {estado_valor}")
            else:
                print(f"No se encontraron datos para la hora simulada: {hora_simulada}")

            await asyncio.sleep(0.2)  # Esperar antes de la siguiente iteración
    except KeyboardInterrupt:
        print("Servidor detenido.")
    finally:
        await cliente_temporal.disconnect()
        await servidor.stop()

if __name__ == "__main__":
    asyncio.run(main())
