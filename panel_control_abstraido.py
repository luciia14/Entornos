import tkinter as tk
from tkinter import ttk
import asyncio
from asyncua import Client
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

async def obtener_datos_opcua():
    url_integracion = "opc.tcp://localhost:4850/integracion"

    async with Client(url_integracion) as client_integracion:
        nodos = {
            'precipitaciones': client_integracion.get_node("ns=2;i=2"),
            'caudal': client_integracion.get_node("ns=2;i=3"),
            'hora_simulada': client_integracion.get_node("ns=2;i=4"),
            'estado_alerta': client_integracion.get_node("ns=2;i=5")
        }

        while True:
            datos = await leer_datos(nodos)
            actualizar_interfaz(**datos)
            await asyncio.sleep(2)

async def leer_datos(nodos):
    precipitacion = await nodos['precipitaciones'].read_value()
    caudal = await nodos['caudal'].read_value()
    hora_simulada = await nodos['hora_simulada'].read_value()
    estado_alerta = await nodos['estado_alerta'].read_value()

    return {
        'precipitacion': precipitacion,
        'caudal': caudal,
        'hora_simulada': hora_simulada,
        'estado_alerta': estado_alerta
    }

def actualizar_interfaz(precipitacion, caudal, hora_simulada, estado_alerta):
    label_precipitacion.config(text=f"Precipitaciones: {precipitacion} mm/h")
    label_caudal.config(text=f"Caudal: {caudal} m\u00b3/s")
    label_hora_simulada.config(text=f"Hora Simulada: {hora_simulada}")
    
    estado_alerta_str = "Alerta" if estado_alerta else "No Alerta"
    label_estado_alerta.config(text=f"Estado de Alerta: {estado_alerta_str}")

    alerta_color = "red" if estado_alerta else "green"
    canvas_alerta.itemconfig(circle_alerta, fill=alerta_color)

    update_realtime_graph(precipitacion, caudal)
    update_historical_graph(precipitacion, caudal)

def update_realtime_graph(precipitacion, caudal):
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

def update_historical_graph(precipitacion, caudal):
    historical_precipitacion.append(precipitacion)
    historical_caudal.append(caudal)

    ax_historical.clear()
    ax_historical.plot(range(len(historical_precipitacion)), historical_precipitacion, label="Precipitaciones")
    ax_historical.plot(range(len(historical_caudal)), historical_caudal, label="Caudal", linestyle="--")
    ax_historical.legend(loc="upper left")
    ax_historical.set_title("Datos Históricos")
    ax_historical.set_xlabel("Tiempo (mediciones)")
    ax_historical.set_ylabel("Valor")
    
    canvas_historical.draw()

def crear_ventana_principal():
    root = tk.Tk()
    root.title("Panel de Control")

    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky="nsew")

    global label_precipitacion, label_caudal, label_hora_simulada, label_estado_alerta
    label_precipitacion = ttk.Label(frame, text="Precipitaciones: 0.0 mm/h", font=("Arial", 14))
    label_precipitacion.grid(row=0, column=0, padx=10, pady=10)

    label_caudal = ttk.Label(frame, text="Caudal: 0.0 m\u00b3/s", font=("Arial", 14))
    label_caudal.grid(row=1, column=0, padx=10, pady=10)

    label_hora_simulada = ttk.Label(frame, text="Hora Simulada: ", font=("Arial", 14))
    label_hora_simulada.grid(row=2, column=0, padx=10, pady=10)

    label_estado_alerta = ttk.Label(frame, text="Estado de Alerta: No Alerta", font=("Arial", 14))
    label_estado_alerta.grid(row=3, column=0, padx=10, pady=10)

    global canvas_alerta, circle_alerta
    canvas_alerta = tk.Canvas(frame, width=50, height=50)
    canvas_alerta.grid(row=4, column=0, padx=10, pady=10)
    circle_alerta = canvas_alerta.create_oval(10, 10, 40, 40, fill="green")

    global ax_realtime, ax_historical, canvas_realtime, canvas_historical
    fig_realtime, ax_realtime = plt.subplots(figsize=(5, 3))
    fig_historical, ax_historical = plt.subplots(figsize=(5, 3))

    global x_data, y_precipitacion_data, y_caudal_data, historical_precipitacion, historical_caudal
    x_data = []
    y_precipitacion_data = []
    y_caudal_data = []
    historical_precipitacion = []
    historical_caudal = []

    canvas_realtime = FigureCanvasTkAgg(fig_realtime, master=root)
    canvas_realtime.get_tk_widget().grid(row=5, column=0, padx=10, pady=10)

    canvas_historical = FigureCanvasTkAgg(fig_historical, master=root)
    canvas_historical.get_tk_widget().grid(row=6, column=0, padx=10, pady=10)

    return root

def iniciar_cliente_opcua():
    threading.Thread(target=lambda: asyncio.run(obtener_datos_opcua())).start()

def ejecutar_aplicacion():
    root = crear_ventana_principal()
    iniciar_cliente_opcua()
    root.mainloop()

if __name__ == "__main__":
    ejecutar_aplicacion()
