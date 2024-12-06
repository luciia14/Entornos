import asyncio
from asyncua import Server
from datetime import datetime, timedelta

# Función principal para ejecutar el servidor OPC UA
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

    # Crear el servidor OPC UA
    servidor = Server()
    await servidor.init()  # Inicializar el servidor correctamente
    servidor.set_endpoint("opc.tcp://localhost:4841/freeopcua/server/")

    # Definir el URI y registrar el espacio de nombres
    uri = "http://www.epsa.upv.es/entornos/temporal"
    idx = await servidor.register_namespace(uri)

    # Crear el objeto en el espacio de nombres
    mi_obj = await servidor.nodes.objects.add_object(idx, "HoraSimulada")

    # Crear la variable dentro del objeto para almacenar la hora simulada
    hora_simulada = await mi_obj.add_variable(idx, "HoraSimulada", hora_inicio)

    # Hacer la variable escribible (aunque no la modificaremos desde fuera)
    await hora_simulada.set_writable()

    # Iniciar el servidor
    await servidor.start()
    print(f"Servidor OPC UA iniciado en {servidor.endpoint}")

    try:
        # Inicializar la hora simulada
        hora_actual = hora_inicio

        while True:
            # Incrementar la hora simulada según la velocidad especificada (en intervalos de 5 minutos)
            hora_actual += timedelta(minutes=5 * velocidad)

            # Escribir el nuevo valor en la variable
            await hora_simulada.write_value(hora_actual)

            # Imprimir la hora simulada en consola
            print(f"Hora simulada: {hora_actual.strftime('%Y-%m-%d %H:%M:%S')}")

            # Esperar 1 segundo en tiempo real antes de actualizar la hora simulada
            await asyncio.sleep(1)

    except Exception as e:
        print(f"Ocurrió un error: {e}")

    finally:
        # Detener el servidor cuando se interrumpe el ciclo
        await servidor.stop()
        print("Servidor detenido")

# Ejecutar la función principal
if __name__ == "__main__":
    asyncio.run(main())

