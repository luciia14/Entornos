import time
import pandas as pd
from asyncua.sync import Server

# Ruta del archivo CSV
archivo_csv = "/home/lucy/openc_ua/cincominutales-rambla-poyo-29102024.csv"
servidor = Server()
servidor.set_endpoint("opc.tcp://localhost:4840/es/upv/epsa/entornos/estacion_aforo/")

# Leer los datos del CSV
df = pd.read_csv(archivo_csv)

# Reemplazar los valores NaN en la columna 'Estado' por 'Desconocido' o cualquier valor predeterminado
df['Estado'].fillna('Desconocido', inplace=True)

uri = "http://www.epsa.upv.es/entornos"
idx = servidor.register_namespace(uri)

# Crear un objeto para la estación de aforo
estacion_aforo = servidor.nodes.objects.add_object(idx, "EstacionAforo")

# Crear las variables
caudal = estacion_aforo.add_variable(idx, "Caudal_m3_s", 0.0)
caudal.set_writable()

nivel_agua = estacion_aforo.add_variable(idx, "NivelAgua_m", 0.0)
nivel_agua.set_writable()

# Iniciar el servidor
servidor.start()
print("Servidor OPC UA de la Estación de Aforo iniciado en:")
print("opc.tcp://localhost:4840/es/upv/epsa/entornos/estacion_aforo/")

try:
    for index, row in df.iterrows():
        # Leer los valores de caudal y estado del CSV
        try:
            caudal_valor = row['Caudal']
            
            # Verificar si el valor es una cadena
            if isinstance(caudal_valor, str):
                # Reemplazar la coma por punto y convertir a float
                caudal_valor = float(caudal_valor.replace(',', '.'))
            # Si ya es float, no se hace nada

        except ValueError:
            print(f"Error de conversión en la fila {index}. Caudal no es un número válido.")
            continue
        
        estado = row['Estado']  # Columna Estado
        
        # Asignar el valor de caudal
        caudal.write_value(caudal_valor)
        
        # Actualizar el nivel de agua con algún valor (por ejemplo, puedes calcularlo en función del caudal o hacerlo aleatorio)
        nivel_agua_valor = 1.0  # Valor estático o calculado
        nivel_agua.write_value(nivel_agua_valor)
        
        # Imprimir información para depuración
        print(f"Fecha: {row['Fecha']}, Caudal: {caudal_valor}, Estado: {estado}")
        
        time.sleep(0.2)  # Espera de 1 segundo antes de la siguiente iteración
except KeyboardInterrupt:
    print("Servidor detenido.")
    servidor.stop()



