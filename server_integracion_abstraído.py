from asyncua.sync import Client, Server

def obtener_nodo_por_nombre(nodo, nombre_nodo):
    """Busca un nodo por nombre dentro de un nodo dado."""
    for hijo in nodo.get_children():
        browse_name = hijo.read_browse_name().Name
        if browse_name == nombre_nodo:
            return hijo
    raise Exception(f"Nodo '{nombre_nodo}' no encontrado en el objeto.")

def conectar_cliente(endpoint):
    """Crea y conecta un cliente OPC UA a un servidor."""
    cliente = Client(endpoint)
    cliente.connect()
    print(f"Conectado a servidor OPC UA en: {endpoint}")
    return cliente

def configurar_servidor_integracion(endpoint, uri):
    """Configura el servidor de integración OPC UA."""
    servidor = Server()
    servidor.set_endpoint(endpoint)
    idx = servidor.register_namespace(uri)

    integracion = servidor.nodes.objects.add_object(idx, "Integracion")
    precipitaciones = integracion.add_variable(idx, "Precipitaciones_mm_h", 0.0)
    caudal = integracion.add_variable(idx, "Caudal_m3_s", 0.0)
    hora_simulada = integracion.add_variable(idx, "HoraSimulada", "")
    estado_alerta = integracion.add_variable(idx, "EstadoAlerta", False)

    for var in [precipitaciones, caudal, hora_simulada, estado_alerta]:
        var.set_writable()

    servidor.start()
    print(f"Servidor de integración iniciado en: {endpoint}")
    return servidor, precipitaciones, caudal, hora_simulada, estado_alerta

def leer_valores(clientes, nodos):
    """Lee los valores de los nodos desde los clientes OPC UA."""
    precipitaciones = nodos['precipitaciones'].get_value()
    caudal = nodos['caudal'].get_value()
    hora_simulada = nodos['hora_simulada'].get_value().strftime('%Y-%m-%d %H:%M:%S')
    return precipitaciones, caudal, hora_simulada

def calcular_estado_alerta(precipitaciones, caudal):
    """Calcula el estado de alerta basado en precipitaciones y caudal."""
    return precipitaciones > 50 or caudal > 150

def configurar_nodos_clientes(clientes):
    """Configura los nodos relevantes para lectura desde los clientes OPC UA."""
    nodos = {}
    pluviometro = clientes['pluvio'].get_node("ns=2;i=1")
    aforo = clientes['aforo'].get_node("ns=2;i=1")
    nodos['precipitaciones'] = obtener_nodo_por_nombre(pluviometro, "Precipitaciones_mm_h")
    nodos['caudal'] = obtener_nodo_por_nombre(aforo, "Caudal_m3_s")
    nodos['hora_simulada'] = clientes['temporal'].get_node("ns=2;i=2")
    return nodos

def main():
    # Conexión a los servidores
    clientes = {
        'pluvio': conectar_cliente("opc.tcp://localhost:4841/es/upv/epsa/entornos/bla/pluviometro/"),
        'aforo': conectar_cliente("opc.tcp://localhost:4842/es/upv/epsa/entornos/bla/estacion_aforo/"),
        'temporal': conectar_cliente("opc.tcp://localhost:4840/es/upv/epsa/entornos/bla/temporal/"),
    }

    try:
        # Configuración del servidor de integración
        servidor, precipitaciones_var, caudal_var, hora_var, alerta_var = configurar_servidor_integracion(
            "opc.tcp://localhost:4850/integracion/",
            "http://www.epsa.upv.es/entornos/integracion"
        )

        # Configuración de los nodos de lectura en clientes
        nodos = configurar_nodos_clientes(clientes)

        while True:
            # Leer valores desde los servidores
            prec, caudal, hora = leer_valores(clientes, nodos)

            # Actualizar valores en el servidor de integración
            precipitaciones_var.set_value(prec)
            caudal_var.set_value(caudal)
            hora_var.set_value(hora)

            # Calcular y actualizar el estado de alerta
            alerta = calcular_estado_alerta(prec, caudal)
            alerta_var.set_value(alerta)

            # Log de estado
            print(f"Hora: {hora}, Precipitaciones: {prec} mm/h, Caudal: {caudal} m³/s, Alerta: {'Activada' if alerta else 'Desactivada'}")
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario.")
    finally:
        # Desconectar clientes y detener servidor
        for cliente in clientes.values():
            cliente.disconnect()
        servidor.stop()
        print("Conexiones cerradas y servidor detenido.")

if __name__ == "__main__":
    main()
