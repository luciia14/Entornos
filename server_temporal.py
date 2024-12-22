import asyncio
from asyncua import Server, ua
from datetime import datetime, timedelta, timezone
import os


class SubscriptionHandler:
    def __init__(self, hora_simulada, velocidad_simulada):
        self.hora_simulada = hora_simulada
        self.velocidad_simulada = velocidad_simulada
        self.hora_actual = datetime(2024, 11, 28, 4, 0, 0, tzinfo=timezone.utc)  # Hora inicial en UTC
        self.velocidad_actual = 1

    async def datachange_notification(self, node, val, data):
        """Se ejecuta cuando un cliente modifica las variables."""
        if node == self.hora_simulada:
            try:
                # Validar y asignar la hora modificada
                if isinstance(val, datetime):
                    self.hora_actual = val
                else:
                    self.hora_actual = datetime.strptime(val, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                print(f"Hora simulada modificada por cliente: {self.hora_actual}")
            except Exception as e:
                print(f"Error al interpretar la hora modificada: {e}")
        elif node == self.velocidad_simulada:
            self.velocidad_actual = max(val, 0.1)  # Prevenir división por 0
            print(f"Velocidad simulada modificada por cliente: {self.velocidad_actual}")

    async def actualizar_hora(self):
        """Incrementa la hora simulada automáticamente según la velocidad."""
        while True:
            try:
                # Incrementar la hora simulada
                self.hora_actual += timedelta(minutes=5)
                await self.hora_simulada.write_value(self.hora_actual)
                print(f"Hora simulada actualizada: {self.hora_actual.strftime('%Y-%m-%d %H:%M:%S %Z')}")

                # Ajustar el tiempo de espera según la velocidad actual
                await asyncio.sleep(1 / self.velocidad_actual)
            except Exception as e:
                print(f"Error al actualizar la hora simulada: {e}")


async def main():
    # Crear el servidor OPC UA
    servidor = Server()
    await servidor.init()
    servidor.set_endpoint("opc.tcp://localhost:4840/entornos/bla/temporal/")

    uri = "http://www.epsa.upv.es/entornos/bla/temporal"
    idx = await servidor.register_namespace(uri)

    # Importar el archivo XML
    try:
        print("Comprobando si el archivo XML existe:", os.path.isfile("trabajo_final.xml"))
        await servidor.import_xml("nodo_hora.xml")
        print("Archivo XML importado correctamente")
    except Exception as e:
        print(f"Error al importar el archivo XML: {e}")
        return

    # Verificar nodos importados
    print("\nVerificando nodos importados:")
    try:
        # Obtener el nodo ObjetoTemporal
        nodo_objeto_temporal = await servidor.nodes.objects.get_child([f"{idx}:ObjetoTemporal"])

        # Obtener las variables hijo
        hora_simulada = await nodo_objeto_temporal.get_child([f"{idx}:HoraSimulada"])
        velocidad_simulada = await nodo_objeto_temporal.get_child([f"{idx}:VelocidadSimulacion"])

        print(f"Nodo ObjetoTemporal encontrado: {nodo_objeto_temporal}")
        print(f"Nodo HoraSimulada encontrado: {hora_simulada}")
        print(f"Nodo VelocidadSimulada encontrado: {velocidad_simulada}")
    except Exception as e:
        print(f"Error al verificar nodos importados: {e}")
        return

    # Configurar variables como escribibles
    await hora_simulada.set_writable()
    
    await velocidad_simulada.set_writable()

    # Crear manejador y suscripciones
    handler = SubscriptionHandler(hora_simulada, velocidad_simulada)
    subscription = await servidor.create_subscription(100, handler)
    await subscription.subscribe_data_change(hora_simulada)
    await subscription.subscribe_data_change(velocidad_simulada)

    # Iniciar el servidor
    await servidor.start()
    print(f"Servidor OPC UA iniciado en {servidor.endpoint}")

    # Ejecutar el actualizador de hora en un bucle asincrónico
    try:
        await handler.actualizar_hora()
    finally:
        await servidor.stop()
        print("Servidor detenido")


if __name__ == "__main__":
    asyncio.run(main())


