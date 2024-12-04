import time
import asyncio
from asyncua import Client, ua
from datetime import datetime, timedelta

# Esta función se llamará cuando se reciba una nueva actualización de precipitaciones
class MyHandler:
    async def datachange_notification(self, node, value, data):
        print(f"Actualización de precipitaciones recibida: {value} mm/h")

# Función principal asíncrona
async def main():
    # Pedir la fecha y hora de inicio al usuario
    fecha_hora_str = input("Introduce la fecha y hora de inicio de la simulación (formato DD/MM/YYYY HH:MM:SS): ")
    try:
        # Convertir la fecha y hora de inicio en un objeto datetime
        hora_inicio = datetime.strptime(fecha_hora_str, "%d/%m/%Y %H:%M:%S")
    except ValueError:
        print("Formato de fecha y hora inválido. Usando la fecha y hora actual como valor predeterminado.")
        hora_inicio = datetime.now().replace(second=0, microsecond=0)  # Usar la fecha y hora actual si el formato es incorrecto

    print(f"Hora de inicio de la simulación: {hora_inicio}")

    # Pedir la velocidad de simulación (número de minutos de simulación por cada minuto real)
    velocidad_str = input("Introduce la velocidad de simulación (número de minutos simulados por minuto real): ")
    try:
        velocidad = int(velocidad_str)
    except ValueError:
        print("Valor inválido para la velocidad. Usando velocidad 1 por defecto.")
        velocidad = 1  # Si la entrada no es válida, usar velocidad 1 como predeterminado

    # Conectar al servidor de pluviómetro
    url_pluviometro = "opc.tcp://localhost:4840/es/upv/epsa/entornos/pluviometro/"
    client = Client(url_pluviometro)

    try:
        # Conectar al servidor
        await client.connect()

        # Obtener el nodo de las precipitaciones
        nodo_precipitaciones = client.get_node("ns=2;i=2")  # Asegúrate de que este es el ID correcto del nodo en tu servidor

        # Crear el handler para las notificaciones de cambio de datos
        handler = MyHandler()

        # Suscribir a los cambios de la variable de precipitaciones
        subscription = await client.create_subscription(500, handler)
        await subscription.subscribe_data_change(nodo_precipitaciones)

        # Crear el servidor OPC UA para la hora simulada
        from asyncua.sync import Server  # Importamos Server de asyncua.sync ya que estamos trabajando en un entorno asíncrono
        servidor = Server()
        endpoint = "opc.tcp://localhost:4841/freeopcua/server/"  # Cambié el puerto aquí
        servidor.set_endpoint(endpoint)

        # Definir el URI y registrar el espacio de nombres
        uri = "http://www.epsa.upv.es/entornos/temporal"
        idx = servidor.register_namespace(uri)

        # Crear el objeto en el espacio de nombres
        mi_obj = servidor.nodes.objects.add_object(idx, "HoraSimulada")

        # Crear la variable dentro del objeto para almacenar la hora simulada
        hora_simulada = mi_obj.add_variable(idx, "HoraSimulada", hora_inicio)

        # Hacer la variable escribible (aunque no la modificaremos)
        hora_simulada.set_writable()

        # Iniciar el servidor
        servidor.start()

        print(f"Servidor OPC UA iniciado en {endpoint}")

        # Inicializar la hora simulada
        hora_actual = hora_inicio

        while True:
            # Incrementar la hora simulada según la velocidad especificada
            hora_actual += timedelta(minutes=velocidad)

            # Escribir el nuevo valor en la variable
            hora_simulada.write_value(hora_actual)

            # Imprimir la hora simulada en consola
            print("Hora simulada:", hora_actual)

            # Esperar 1 minuto en tiempo real antes de actualizar la hora simulada
            await asyncio.sleep(1)  # Usamos asyncio.sleep en lugar de time.sleep

    except Exception as e:
        print(f"Ocurrió un error: {e}")
    finally:
        # Detener el servidor cuando se interrumpe el ciclo
        if 'servidor' in locals():
            servidor.stop()
            print("Servidor detenido")

        # Cerrar la conexión del cliente
        await client.disconnect()

# Ejecutar la función principal
if __name__ == "__main__":
    asyncio.run(main())

