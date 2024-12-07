import time
import pandas as pd
import math
from asyncua.sync import Server

def leer_datos_excel(ruta_archivo, columnas, fila_inicio, filas_leer):
    """Lee las columnas especificadas desde un archivo Excel, omitiendo filas iniciales."""
    return pd.read_excel(
        ruta_archivo,
        usecols=columnas,
        skiprows=fila_inicio,
        nrows=filas_leer,
        engine='openpyxl'
    )

def procesar_precipitaciones(datos_precipitaciones):
    """Procesa la lista de precipitaciones redondeándolas hacia arriba a un decimal."""
    return [round(math.ceil(valor * 10) / 10, 1) for valor in pd.to_numeric(datos_precipitaciones, errors='coerce').dropna()]

def configurar_servidor_opc(endpoint, uri):
    """Configura y devuelve un servidor OPC UA listo para usar."""
    servidor = Server()
    servidor.set_endpoint(endpoint)
    idx = servidor.register_namespace(uri)
    pluviometro = servidor.nodes.objects.add_object(idx, "Pluviometro")
    return servidor, idx, pluviometro

def agregar_variables_pluviometro(pluviometro, idx):
    """Agrega variables al objeto pluviómetro en el servidor OPC."""
    precipitaciones = pluviometro.add_variable(idx, "Precipitaciones_mm_h", 0.0)
    precipitaciones.set_writable()
    hora_variable = pluviometro.add_variable(idx, "Hora", "")
    hora_variable.set_writable()
    return precipitaciones, hora_variable

def actualizar_datos(servidor, precipitaciones_var, hora_var, datos, intervalo):
    """Simula actualizaciones de datos en el servidor OPC."""
    try:
        for i, (hora, valor) in enumerate(zip(datos.iloc[:, 0], datos.iloc[:, 1])):
            time.sleep(intervalo)
            hora = hora.strftime('%H:%M:%S') if isinstance(hora, pd.Timestamp) else str(hora)
            precipitaciones_var.set_value(valor)
            hora_var.set_value(hora)
            print(f"Actualizando precipitaciones a: {valor} mm/h")
            print(f"Hora actualizada a: {hora}")
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario.")
    finally:
        servidor.stop()
        print("Servidor detenido.")

if __name__ == "__main__":
    # Configuración del archivo y lectura de datos
    archivo_excel = r"/home/bpercam/entornos_trabajo/Pluvi_metroChiva_29octubre2024.xlsx"
    columnas_a_leer = [0, 1]
    fila_inicio = 7
    filas_leer = 289

    df = leer_datos_excel(archivo_excel, columnas_a_leer, fila_inicio, filas_leer)
    precipitaciones_lista = procesar_precipitaciones(df.iloc[:, 1])
    df.iloc[:, 1] = precipitaciones_lista

    # Configuración del servidor OPC UA
    endpoint = "opc.tcp://localhost:4840/es/upv/epsa/entornos/pluviometro/"
    uri = "http://www.epsa.upv.es/entornos"
    servidor, idx, pluviometro = configurar_servidor_opc(endpoint, uri)

    precipitaciones_var, hora_var = agregar_variables_pluviometro(pluviometro, idx)

    # Iniciar el servidor y actualizar datos
    servidor.start()
    print(f"Servidor OPC UA iniciado en: {endpoint}")
    actualizar_datos(servidor, precipitaciones_var, hora_var, df, intervalo=1)

