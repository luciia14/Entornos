import asyncio
from asyncua import Server
from datetime import datetime, timedelta

def obtener_hora_inicio():
    fecha_hora_str = input("Introduce la fecha y hora de inicio de la simulación (formato DD/MM/YYYY HH:MM:SS): ")
    try:
        return datetime.strptime(fecha_hora_str, "%d/%m/%Y %H:%M:%S")
    except ValueError:
        print("Formato de fecha y hora inválido. Usando la fecha y hora actual como valor predeterminado.")
        return datetime.now().replace(second=0, microsecond=0)

def obtener_velocidad_simulacion():
    velocidad_str = input("Introduce la velocidad de simulación (número de minutos simulados por minuto real): ")
    try:
        return int(velocidad_str)
    except ValueError:
        print("Valor inválido para la velocidad. Usando velocidad 1 por defecto.")
        return 1

async def configurar_servidor(endpoint, uri):
    servidor = Server()
    await servidor.init()
    servidor.set_endpoint(endpoint)
    idx = await servidor.register_namespace(uri)
    return servidor, idx

async def agregar_variable_hora_simulada(servidor, idx, hora_inicio):
    mi_obj = await servidor.nodes.objects.add_object(idx, "HoraSimulada")
    hora_simulada = await mi_obj.add_variable(idx, "HoraSimulada", hora_inicio)
    await hora_simulada.set_writable()
    return hora_simulada

async def iniciar_simulacion(servidor, hora_simulada, hora_inicio, velocidad):
    hora_actual = hora_inicio
    try:
        while True:
            hora_actual += timedelta(minutes=5 * velocidad)
            await hora_simulada.write_value(hora_actual)
            print(f"Hora simulada: {hora_actual.strftime('%Y-%m-%d %H:%M:%S')}")
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Ocurrió un error: {e}")
    finally:
        await servidor.stop()
        print("Servidor detenido")

async def main():
    hora_inicio = obtener_hora_inicio()
    print(f"Hora de inicio de la simulación: {hora_inicio}")

    velocidad = obtener_velocidad_simulacion()
    
    endpoint = "opc.tcp://localhost:4841/freeopcua/server/"
    uri = "http://www.epsa.upv.es/entornos/temporal"

    servidor, idx = await configurar_servidor(endpoint, uri)
    hora_simulada = await agregar_variable_hora_simulada(servidor, idx, hora_inicio)

    await servidor.start()
    print(f"Servidor OPC UA iniciado en {servidor.endpoint}")
    await iniciar_simulacion(servidor, hora_simulada, hora_inicio, velocidad)

if __name__ == "__main__":
    asyncio.run(main())
