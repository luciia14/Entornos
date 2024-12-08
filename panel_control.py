import tkinter as tk
from tkinter import ttk
import asyncio
from asyncua import Client
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Conexión con el servidor de integración OPC UA
async def obtener_datos_opcua():
    """Conectar al servidor OPC UA de integración y obtener datos de precipitaciones, caudal, hora simulada y estado de alerta."""
    # Dirección del servidor de integración
    url_integracion = "opc.tcp://localhost:4850/integracion"

    async with Client(url_integracion) as client_integracion:
        
        # Obtener nodos del servidor de integración
        nodo_precipitaciones = client_integracion.get_node("ns=2;i=2")  # Ajustar 'ns' e 'i' según tu servidor
        nodo_caudal = client_integracion.get_node("ns=2;i=3")  # Ajustar 'ns' e 'i' según tu servidor
        nodo_hora_simulada = client_integracion.get_node("ns=2;i=4")  # Ajustar 'ns' e 'i' según tu servidor
        nodo_estado_alerta = client_integracion.get_node("ns=2;i=5")  # Ajustar 'ns' e 'i' según tu servidor

        while True:
            # Leer los valores de precipitaciones, caudal, hora simulada y estado de alerta
            precipitacion = await nodo_precipitaciones.read_value()
            caudal = await nodo_caudal.read_value()
            hora_simulada = await nodo_hora_simulada.read_value()
            estado_alerta = await nodo_estado_alerta.read_value()

            # Actualizar la interfaz con los datos obtenidos
            actualizar_interfaz(precipitacion, caudal, hora_simulada, estado_alerta)
            
            # Esperar antes de la siguiente actualización
            await asyncio.sleep(2)

# Función para actualizar la interfaz de usuario con los datos de los sensores
def actualizar_interfaz(precipitacion, caudal, hora_simulada, estado_alerta):
    """Actualiza los widgets de la interfaz con los datos de los sensores."""
    label_precipitacion.config(text=f"Precipitaciones: {precipitacion} mm/h")
    label_caudal.config(text=f"Caudal: {caudal} m\u00b3/s")
    label_hora_simulada.config(text=f"Hora Simulada: {hora_simulada}")
    
    # Mostrar el estado de alerta directamente desde el nodo
    estado_alerta_str = "Alerta" if estado_alerta else "No Alerta"
    label_estado_alerta.config(text=f"Estado de Alerta: {estado_alerta_str}")

    # Cambiar el color del círculo de estado de alerta
    alerta_color = "red" if estado_alerta else "green"
    canvas_alerta.itemconfig(circle_alerta, fill=alerta_color)

    # Actualizar los gráficos con los datos
    update_realtime_graph(precipitacion, caudal)
    update_historical_graph(precipitacion, caudal)

# Función para actualizar el gráfico en tiempo real
def update_realtime_graph(precipitacion, caudal):
    """Actualiza el gráfico en tiempo real con los nuevos valores."""
    x_data.append(len(x_data))  # Incrementar el tiempo
    y_precipitacion_data.append(precipitacion)
    y_caudal_data.append(caudal)

    # Limitar el tamaño de los datos del gráfico
    if len(x_data) > 10:
        x_data.pop(0)
        y_precipitacion_data.pop(0)
        y_caudal_data.pop(0)

    # Actualizar el gráfico en tiempo real
    ax_realtime.clear()
    ax_realtime.plot(x_data, y_precipitacion_data, label="Precipitaciones")
    ax_realtime.plot(x_data, y_caudal_data, label="Caudal", linestyle="--")
    ax_realtime.legend(loc="upper left")
    ax_realtime.set_title("Datos en Tiempo Real")
    ax_realtime.set_xlabel("Tiempo (s)")
    ax_realtime.set_ylabel("Valor")
    
    # Redibujar el gráfico
    canvas_realtime.draw()

# Función para actualizar el gráfico histórico
def update_historical_graph(precipitacion, caudal):
    """Actualiza el gráfico histórico con los nuevos valores."""
    historical_precipitacion.append(precipitacion)
    historical_caudal.append(caudal)

    # Actualizar el gráfico histórico
    ax_historical.clear()
    ax_historical.plot(range(len(historical_precipitacion)), historical_precipitacion, label="Precipitaciones")
    ax_historical.plot(range(len(historical_caudal)), historical_caudal, label="Caudal", linestyle="--")
    ax_historical.legend(loc="upper left")
    ax_historical.set_title("Datos Históricos")
    ax_historical.set_xlabel("Tiempo (mediciones)")
    ax_historical.set_ylabel("Valor")
    
    # Redibujar el gráfico
    canvas_historical.draw()

# Crear la ventana principal de Tkinter
root = tk.Tk()
root.title("Panel de Control")

# Crear un marco para contener los widgets
frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky="nsew")

# Etiquetas para mostrar los datos de precipitaciones, caudal, hora simulada y estado de alerta
label_precipitacion = ttk.Label(frame, text="Precipitaciones: 0.0 mm/h", font=("Arial", 14))
label_precipitacion.grid(row=0, column=0, padx=10, pady=10)

label_caudal = ttk.Label(frame, text="Caudal: 0.0 m\u00b3/s", font=("Arial", 14))
label_caudal.grid(row=1, column=0, padx=10, pady=10)

label_hora_simulada = ttk.Label(frame, text="Hora Simulada: ", font=("Arial", 14))
label_hora_simulada.grid(row=2, column=0, padx=10, pady=10)

label_estado_alerta = ttk.Label(frame, text="Estado de Alerta: No Alerta", font=("Arial", 14))
label_estado_alerta.grid(row=3, column=0, padx=10, pady=10)

# Crear un lienzo para mostrar el círculo de estado de alerta
canvas_alerta = tk.Canvas(frame, width=50, height=50)
canvas_alerta.grid(row=4, column=0, padx=10, pady=10)
circle_alerta = canvas_alerta.create_oval(10, 10, 40, 40, fill="green")

# Crear gráficos usando Matplotlib
fig_realtime, ax_realtime = plt.subplots(figsize=(5, 3))
fig_historical, ax_historical = plt.subplots(figsize=(5, 3))

x_data = []
y_precipitacion_data = []
y_caudal_data = []

historical_precipitacion = []
historical_caudal = []

# Canvas para el gráfico en tiempo real
canvas_realtime = FigureCanvasTkAgg(fig_realtime, master=root)
canvas_realtime.get_tk_widget().grid(row=5, column=0, padx=10, pady=10)

# Canvas para el gráfico histórico
canvas_historical = FigureCanvasTkAgg(fig_historical, master=root)
canvas_historical.get_tk_widget().grid(row=6, column=0, padx=10, pady=10)

# Ejecutar el cliente OPC UA de forma asincrónica
async def start_opcua():
    await obtener_datos_opcua()

# Ejecutar la función de cliente en un hilo aparte
import threading
threading.Thread(target=lambda: asyncio.run(start_opcua())).start()

# Ejecutar el loop de Tkinter
root.mainloop()
