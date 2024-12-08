import tkinter as tk
from tkinter import ttk
import asyncio
from asyncua import Client
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Conexión con el servidor de integración OPC UA
async def obtener_datos_opcua():
    """Conectar al servidor OPC UA de integración y obtener datos de precipitaciones, caudal, hora simulada y estado de alerta."""
    url_integracion = "opc.tcp://localhost:4850/integracion"

    async with Client(url_integracion) as client_integracion:
        
        nodo_precipitaciones = client_integracion.get_node("ns=2;i=2")
        nodo_caudal = client_integracion.get_node("ns=2;i=3")
        nodo_hora_simulada = client_integracion.get_node("ns=2;i=4")
        nodo_estado_alerta = client_integracion.get_node("ns=2;i=5")

        while True:
            precipitacion = await nodo_precipitaciones.read_value()
            caudal = await nodo_caudal.read_value()
            hora_simulada = await nodo_hora_simulada.read_value()
            estado_alerta = await nodo_estado_alerta.read_value()

            actualizar_interfaz(precipitacion, caudal, hora_simulada, estado_alerta)
            await asyncio.sleep(2)

def actualizar_interfaz(precipitacion, caudal, hora_simulada, estado_alerta):
    """Actualiza los widgets de la interfaz con los datos de los sensores."""
    label_precipitacion.config(text=f"Precipitaciones: {precipitacion} mm/h")
    label_caudal.config(text=f"Caudal: {caudal} m³/s")
    label_hora_simulada.config(text=f"Hora Simulada: {hora_simulada}")
    
    estado_alerta_str = "Alerta" if estado_alerta else "No Alerta"
    label_estado_alerta.config(text=f"Estado de Alerta: {estado_alerta_str}")

    # Cambiar el color del círculo en función del estado de alerta
    color_circulo = "red" if estado_alerta else "green"
    canvas_alerta.itemconfig(circulo, fill=color_circulo)

    # Actualizar los gráficos
    update_realtime_graph(precipitacion, caudal)

def update_realtime_graph(precipitacion, caudal):
    """Actualiza el gráfico en tiempo real con los nuevos valores."""
    x_data.append(len(x_data))
    y_precipitacion_data.append(precipitacion)
    y_caudal_data.append(caudal)

    if len(x_data) > 10:
        x_data.pop(0)
        y_precipitacion_data.pop(0)
        y_caudal_data.pop(0)

    ax_realtime.clear()
    ax_realtime.plot(x_data, y_precipitacion_data, label="Precipitaciones")
    ax_realtime.plot(x_data, y_caudal_data, label="Caudal", linestyle="--")
    ax_realtime.legend(loc="upper left")
    ax_realtime.set_title("Datos en Tiempo Real")
    ax_realtime.set_xlabel("Tiempo (s)")
    ax_realtime.set_ylabel("Valor")
    canvas_realtime.draw()

# Crear la ventana principal
root = tk.Tk()
root.title("Panel de Control")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky="nsew")

# Etiquetas
label_precipitacion = ttk.Label(frame, text="Precipitaciones: 0.0 mm/h", font=("Arial", 14))
label_precipitacion.grid(row=0, column=0, padx=10, pady=10)

label_caudal = ttk.Label(frame, text="Caudal: 0.0 m³/s", font=("Arial", 14))
label_caudal.grid(row=1, column=0, padx=10, pady=10)

label_hora_simulada = ttk.Label(frame, text="Hora Simulada: ", font=("Arial", 14))
label_hora_simulada.grid(row=2, column=0, padx=10, pady=10)

label_estado_alerta = ttk.Label(frame, text="Estado de Alerta: No Alerta", font=("Arial", 14))
label_estado_alerta.grid(row=3, column=0, padx=10, pady=10)

# Canvas para el indicador de alerta
canvas_alerta = tk.Canvas(frame, width=50, height=50)
canvas_alerta.grid(row=4, column=0, pady=10)

# Dibujar el círculo inicial (verde para No Alerta)
circulo = canvas_alerta.create_oval(10, 10, 40, 40, fill="green")

# Gráficos con Matplotlib
fig_realtime, ax_realtime = plt.subplots(figsize=(5, 3))
canvas_realtime = FigureCanvasTkAgg(fig_realtime, master=root)
canvas_realtime.get_tk_widget().grid(row=5, column=0, padx=10, pady=10)

x_data = []
y_precipitacion_data = []
y_caudal_data = []

# Ejecutar el cliente OPC UA
async def start_opcua():
    await obtener_datos_opcua()

import threading
threading.Thread(target=lambda: asyncio.run(start_opcua())).start()

root.mainloop()

