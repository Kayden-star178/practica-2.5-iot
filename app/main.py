from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.models.schemas import MovimientoRequest, DemoRequest
from app.services.iot_service import iot_service
from app.websocket.manager import manager

app = FastAPI(
    title="API Vehículo IoT - Práctica 2.5",
    description="Integración de los 21 Stored Procedures de RDS en entorno Dev",
    version="1.0.0"
)

# --- SERVICIOS GET ---
@app.get("/api/vehiculos", tags=["Vehículos"])
def obtener_vehiculos():
    return iot_service.ejecutar_sp("sp_obtener_vehiculos")

@app.get("/api/vehiculos/{vehiculo_id}", tags=["Vehículos"])
def obtener_vehiculo(vehiculo_id: int):
    return iot_service.ejecutar_sp("sp_obtener_vehiculo", (vehiculo_id,))

@app.get("/api/comandos/{vehiculo_id}", tags=["Comandos"])
def obtener_comandos(vehiculo_id: int):
    return iot_service.ejecutar_sp("sp_obtener_comandos_vehiculo", (vehiculo_id,))

@app.get("/api/estado/{vehiculo_id}", tags=["Estado"])
def obtener_estado(vehiculo_id: int):
    return iot_service.ejecutar_sp("sp_obtener_estado", (vehiculo_id,))

@app.get("/api/historial/{vehiculo_id}", tags=["Historial"])
def obtener_historial(vehiculo_id: int):
    return iot_service.obtener_historial_limitado(vehiculo_id)

# --- SERVICIOS POST ---
@app.post("/api/movimiento", tags=["Movimientos"])
async def movimiento_individual(req: MovimientoRequest):
    return await iot_service.procesar_movimiento_individual(req.vehiculo_id, req.comando_id)

@app.post("/api/demo", tags=["DEMO"])
async def ejecutar_demo(req: DemoRequest):
    return await iot_service.ejecutar_demo(req.vehiculo_id, req.demo_id)

@app.post("/api/crear-comando-test/{vehiculo_id}", tags=["Comandos"])
def crear_comando_test(vehiculo_id: int):
    return iot_service.crear_comando_prueba(vehiculo_id, "Avanzar", "FORWARD")

@app.post("/api/comandos/{vehiculo_id}", tags=["Comandos"])
def crear_comando_directo(vehiculo_id: int):
    # Pasa exactamente 4 argumentos: vehiculo_id, nombre, codigo, descripcion
    return iot_service.ejecutar_sp("sp_crear_comando", (vehiculo_id, "Avanzar", "FORWARD", "Movimiento de prueba"))
# --- WEBSOCKET POR VEHÍCULO ---
@app.websocket("/ws/{vehiculo_id}")
async def websocket_endpoint(websocket: WebSocket, vehiculo_id: int):
    await manager.connect(websocket, vehiculo_id)
    try:
        await websocket.send_json({"evento": "conexion_exitosa", "vehiculo_id": vehiculo_id})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, vehiculo_id)