import time
import pandas as pd
import math
import asyncio
from asyncua import Server, Client

# Ruta del archivo Excel
archivo_excel = r"/home/alopalm/entornos/trabajo_final/Pluvi_metroChiva_29octubre2024.xlsx"

# Leer las columnas A (hora) y B (precipitaciones) desde la fila 8
df = pd.read_excel(archivo_excel, usecols=[0, 1], skiprows=7, nrows=289, engine='openpyxl')

# Convertir la columna B (precipitaciones) en una lista de valores numéricos
precipitaciones_lista = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().tolist()

# Redondear los valores de precipitaciones hacia arriba y mantener solo un decimal
precipitaciones_lista = [round(math.ceil(valor * 10) / 10, 1) for valor in precipitaciones_lista]

# Crear el servidor OPC UA para el pluviómetro
servidor = Server()
servidor.set_endpoint("opc.tcp://localhost:4841/es/upv/epsa/entornos/bla/pluviometro/")

# Registrar un espacio de nombres único para los nodos
uri = "http://www.epsa.upv.es/entornos"
async def iniciar_servidor():
    await servidor.init()
    idx = await servidor.register_namespace(uri)

    # Crear un objeto para el pluviómetro
    pluviometro = await servidor.nodes.objects.add_object(idx, "Pluviometro")

    # Crear una variable para representar las precipitaciones en mm/h
    precipitaciones = await pluviometro.add_variable(idx, "Precipitaciones_mm_h", 0.0)
    await precipitaciones.set_writable()  # Permitir que los clientes modifiquen el valor

    # Crear una variable para representar la hora
    hora_variable = await pluviometro.add_variable(idx, "Hora", "")
    await hora_variable.set_writable()  # Permitir que los clientes modifiquen el valor

    # Iniciar el servidor
    await servidor.start()
    print("Servidor OPC UA del Pluviómetro iniciado en:")
    print(servidor.endpoint)

    return precipitaciones, hora_variable

# URL del servidor temporal al cual nos conectaremos como cliente
url_servidor_temporal = "opc.tcp://localhost:4840/es/upv/epsa/entornos/bla/temporal/"

# Conectar como cliente al servidor temporal
async def main():
    precipitaciones, hora_variable = await iniciar_servidor()
    client_temporal = Client(url_servidor_temporal)

    try:
        # Conectar al servidor temporal
        await client_temporal.connect()
        print("Conectado al servidor temporal en:", url_servidor_temporal)

        # Obtener el nodo de la hora simulada
        nodo_hora_simulada = client_temporal.get_node("ns=2;i=2")
        print("Nodo de hora simulada obtenido:", nodo_hora_simulada)

        while True:
            # Leer la hora simulada del servidor temporal
            hora_simulada = await nodo_hora_simulada.read_value()
            print(f"Hora simulada leída: {hora_simulada}")

            # Eliminar la zona horaria de la hora simulada (si la tiene)
            hora_simulada = hora_simulada.replace(tzinfo=None)
            

            # Buscar el valor de precipitaciones correspondiente en el DataFrame
            encontrado = False
            for i, fila in df.iterrows():
                hora_fila = fila.iloc[0]
                # Convertir la hora del DataFrame a datetime para comparar
                if isinstance(hora_fila, pd.Timestamp):
                    hora_fila = hora_fila.replace(second=0, microsecond=0)  
                else:
                    hora_fila = pd.to_datetime(hora_fila).replace(second=0, microsecond=0)

                        
                if hora_fila.time() == hora_simulada.time():
                    valor_precipitacion = precipitaciones_lista[i]

                    # Asignar los valores al servidor del pluviómetro
                    await precipitaciones.write_value(valor_precipitacion)
                    await hora_variable.write_value(hora_simulada.strftime('%H:%M:%S'))

                    print(f"Actualizando precipitaciones a: {valor_precipitacion} mm/h")
                    print(f"Hora actualizada a: {hora_simulada.strftime('%H:%M:%S')}")
                    
                    encontrado = True
                    break

            if not encontrado:
                print("No se encontró una coincidencia para la hora simulada.")

            # Esperar un segundo antes de volver a leer la hora simulada
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("Servidor detenido.")
    finally:
        # Desconectar el cliente y detener el servidor
        await client_temporal.disconnect()
        await servidor.stop()
        print("Servidor del Pluviómetro detenido.")

# Ejecutar la función principal
if __name__ == "__main__":
    asyncio.run(main())







