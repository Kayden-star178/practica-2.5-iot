from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Mantiene conexiones aisladas por vehículo
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, vehiculo_id: int):
        await websocket.accept()
        if vehiculo_id not in self.active_connections:
            self.active_connections[vehiculo_id] = []
        self.active_connections[vehiculo_id].append(websocket)

    def disconnect(self, websocket: WebSocket, vehiculo_id: int):
        if vehiculo_id in self.active_connections:
            if websocket in self.active_connections[vehiculo_id]:
                self.active_connections[vehiculo_id].remove(websocket)
            if not self.active_connections[vehiculo_id]:
                del self.active_connections[vehiculo_id]

    async def broadcast_to_vehicle(self, vehiculo_id: int, message: dict):
        """Notifica exclusivamente a los clientes que monitorean dicho vehículo"""
        if vehiculo_id in self.active_connections:
            for connection in self.active_connections[vehiculo_id]:
                await connection.send_json(message)

manager = ConnectionManager()