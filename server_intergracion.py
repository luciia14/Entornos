from asyncua.sync import Client, Server

def obtener_nodo_por_nombre(nodo, nombre_nodo):
    """Busca un nodo por nombre dentro de un nodo dado."""
    for hijo in nodo.get_children():
        browse_name = hijo.read_browse_name().Name
        print(f"Explorando nodo hijo: {browse_name}")
        if browse_name == nombre_nodo:
            return hijo
    raise Exception(f"Nodo '{nombre_nodo}' no encontrado en el objeto.")

# Conexión a los servidores
pluvio_client = Client("opc.tcp://localhost:4841/es/upv/epsa/entornos/bla/pluviometro/")
aforo_client = Client("opc.tcp://localhost:4842/es/upv/epsa/entornos/bla/estacion_aforo/")
temporal_client = Client("opc.tcp://localhost:4840/es/upv/epsa/entornos/bla/temporal/")

pluvio_client.connect()
aforo_client.connect()
temporal_client.connect()

# Crear servidor de integración
server = Server()
server.set_endpoint("opc.tcp://localhost:4850/integracion/")
uri = "http://www.epsa.upv.es/entornos/integracion"
idx = server.register_namespace(uri)

integracion = server.nodes.objects.add_object(idx, "Integracion")
precipitaciones = integracion.add_variable(idx, "Precipitaciones_mm_h", 0.0)
caudal = integracion.add_variable(idx, "Caudal_m3_s", 0.0)
hora_simulada = integracion.add_variable(idx, "HoraSimulada", "")
estado_alerta = integracion.add_variable(idx, "EstadoAlerta", False)

precipitaciones.set_writable()
caudal.set_writable()
hora_simulada.set_writable()
estado_alerta.set_writable()

server.start()
print("Servidor de integración iniciado en opc.tcp://localhost:4850/integracion/")

try:
    while True:
        # Obtener nodo 'Pluviometro' y explorar sus hijos
        pluviometro_obj = pluvio_client.get_node("ns=2;i=1")  # Nodo Pluviometro
        print("Explorando hijos del nodo 'Pluviometro'...")
        nodo_precipitaciones = obtener_nodo_por_nombre(pluviometro_obj, "Precipitaciones_mm_h")
        
        # Leer el valor del nodo de precipitaciones
        prec = nodo_precipitaciones.get_value()
        
        # Obtener caudal desde el servidor de aforo
        aforo_obj = aforo_client.get_node("ns=2;i=1")  # Nodo Estación de Aforo
        print("Explorando hijos del nodo 'Estación de Aforo'...")
        nodo_caudal = obtener_nodo_por_nombre(aforo_obj, "Caudal_m3_s")
        
        # Leer el valor del nodo de caudal
        caudal_valor = nodo_caudal.get_value()
        
        # Obtener hora simulada del servidor temporal
        hora_simulada_node = temporal_client.get_node("ns=2;i=2")  # Ajustar 'ns' e 'i' según el servidor temporal
        hora_simulada_g= hora_simulada_node.get_value()
        hora_simulada_value = hora_simulada_g.strftime('%Y-%m-%d %H:%M:%S')
        # Establecer los valores en el servidor de integración
        precipitaciones.set_value(prec)
        caudal.set_value(caudal_valor)
        hora_simulada.set_value(hora_simulada_value)
        
        print(f"Precipitaciones actuales: {prec} mm/h")
        print(f"Caudal actual: {caudal_valor} m³/s")
        print(f"Hora simulada: {hora_simulada_value}")
        
        # Simulación de cálculo de estado de alerta
        estado_alerta_value = prec > 50 or caudal_valor > 150  # Activar alerta si las precipitaciones son mayores a 50 mm/h
        estado_alerta.set_value(estado_alerta_value)
        print(f"Estado de alerta: {'Activado' if estado_alerta_value else 'Desactivado'}")
        
except KeyboardInterrupt:
    print("Servidor detenido.")
finally:
    # Desconectar clientes y detener servidor
    pluvio_client.disconnect()
    aforo_client.disconnect()
    temporal_client.disconnect()
    server.stop()
