import time
import pandas as pd
import math
from asyncua.sync import Server

# Ruta del archivo Excel
archivo_excel = r"/home/lucy/openc_ua/PluviómetroChiva_29octubre2024.xlsx"

# Leer las columnas A (hora) y B (precipitaciones) desde la fila 8
# Usar índices 0 y 1 para seleccionar las columnas correspondientes
df = pd.read_excel(archivo_excel, usecols=[0, 1], skiprows=7, nrows=289, engine='openpyxl')

# Convertir la columna B (precipitaciones) en una lista de valores numéricos
precipitaciones_lista = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().tolist()

# Redondear los valores de precipitaciones hacia arriba y mantener solo un decimal
precipitaciones_lista = [round(math.ceil(valor * 10) / 10, 1) for valor in precipitaciones_lista]

# Crear el servidor OPC UA
servidor = Server()
servidor.set_endpoint("opc.tcp://localhost:4840/es/upv/epsa/entornos/pluviometro/")

# Registrar un espacio de nombres único para los nodos
uri = "http://www.epsa.upv.es/entornos"
idx = servidor.register_namespace(uri)

# Crear un objeto para el pluviómetro
pluviometro = servidor.nodes.objects.add_object(idx, "Pluviometro")

# Crear una variable para representar las precipitaciones en mm/h
precipitaciones = pluviometro.add_variable(idx, "Precipitaciones_mm_h", 0.0)  # Valor inicial 0.0
precipitaciones.set_writable()  # Permitir que los clientes modifiquen el valor

# Crear una variable para representar la hora
hora_variable = pluviometro.add_variable(idx, "Hora", "")  # Valor inicial vacío
hora_variable.set_writable()  # Permitir que los clientes modifiquen el valor

# Iniciar el servidor
servidor.start()
print("Servidor OPC UA del Pluviómetro iniciado en:")
print("opc.tcp://0.0.0.0:4840/es/upv/epsa/entornos/pluviometro/")

try:
    # Simular actualizaciones de precipitaciones y hora
    for i, valor in enumerate(precipitaciones_lista):
        time.sleep(1)  # Actualizar cada segundo
        
        # Leer la hora de la columna A correspondiente
        hora = df.iloc[i, 0]  # Obtener la hora de la fila actual
        
        # Convertir la hora a formato string si es necesario
        if isinstance(hora, pd.Timestamp):
            hora = hora.strftime('%H:%M:%S')  # Formato hora: HH:MM:SS
        else:
            hora = str(hora)  # En caso de que la hora ya esté como string

        # Asignar los valores al servidor
        precipitaciones.set_value(valor)  # Asignar el valor de precipitaciones desde la lista
        hora_variable.set_value(hora)  # Asignar el valor de la hora correspondiente
        
        print(f"Actualizando precipitaciones a: {valor} mm/h")
        print(f"Hora actualizada a: {hora}")
except KeyboardInterrupt:
    print("Servidor detenido.")
finally:
    servidor.stop()


