from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.models.schemas import MovimientoRequest, DemoRequest
from app.services.iot_service import iot_service
from app.websocket.manager import manager

app = FastAPI(
    title="API IoT - Vehículo Control - Práctica 2.5",
    description="API desarrollada en Python con FastAPI y POO que consulta Stored Procedures en Amazon RDS.",
    version="1.0.0"
)

# -------------------------------------------------------------
# Servicios GET (Consulta de datos a la BD)
# -------------------------------------------------------------

@app.get("/api/vehiculos", tags=["Vehículos"])
def obtener_vehiculos():
    """Consulta sp_obtener_vehiculos"""
    return iot_service.ejecutar_sp("sp_obtener_vehiculos")

@app.get("/api/comandos", tags=["Comandos"])
def obtener_comandos():
    """Consulta sp_obtener_comandos"""
    return iot_service.ejecutar_sp("sp_obtener_comandos")

@app.get("/api/estado/{vehiculo_id}", tags=["Estado"])
def obtener_estado(vehiculo_id: int):
    """Consulta sp_obtener_estado"""
    return iot_service.ejecutar_sp("sp_obtener_estado", (vehiculo_id,))

@app.get("/api/historial/{vehiculo_id}", tags=["Historial"])
def obtener_historial(vehiculo_id: int):
    """Consulta sp_obtener_historial"""
    return iot_service.ejecutar_sp("sp_obtener_historial", (vehiculo_id,))

# -------------------------------------------------------------
# Servicios POST (Acciones / Operaciones)
# -------------------------------------------------------------

@app.post("/api/movimiento", tags=["Movimientos"])
async def movimiento_individual(req: MovimientoRequest):
    """Ejecuta el flujo de Movimiento Individual"""
    return await iot_service.procesar_movimiento_individual(req.vehiculo_id, req.comando_id)

@app.post("/api/demo", tags=["DEMO"])
async def ejecutar_demo(req: DemoRequest):
    """Ejecuta el flujo de la DEMO"""
    return await iot_service.ejecutar_demo(req.vehiculo_id)

# -------------------------------------------------------------
# Servicio WebSocket (Monitoreo en tiempo real)
# -------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)