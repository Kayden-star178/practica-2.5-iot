import asyncio
from fastapi import HTTPException
from app.database import Database
from app.websocket.manager import manager

class IoTService:
    
    def ejecutar_sp(self, sp_name: str, args: tuple = ()):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.callproc(sp_name, args)
                res = cursor.fetchall()
            conn.commit()
            return res
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Error al ejecutar SP {sp_name}: {str(e)}")
        finally:
            conn.close()

    async def procesar_movimiento_individual(self, vehiculo_id: int, comando_id: int):
        # 1. Validar que el vehículo exista y esté activo
        vehiculos = self.ejecutar_sp("sp_obtener_vehiculo", (vehiculo_id,))
        if not vehiculos or not vehiculos[0].get("activo", True):
            raise HTTPException(status_code=400, detail="El vehículo no existe o está inactivo")

        # 2. Validar que el comando pertenezca a ese vehículo
        comandos = self.ejecutar_sp("sp_obtener_comandos_vehiculo", (vehiculo_id,))
        comando_valido = any(c.get("id_comando") == comando_id and c.get("activo", True) for c in comandos) if comandos else True
        if not comando_valido:
            raise HTTPException(status_code=400, detail="El comando no pertenece al vehículo o está inactivo")

        # 3. Transacción atómica en RDS
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.callproc("sp_actualizar_estado", (vehiculo_id, comando_id, "API"))
                # Pasa los 3 argumentos requeridos por el SP
                cursor.callproc("sp_registrar_historial", (vehiculo_id, comando_id, "API"))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Error en la transacción RDS: {str(e)}")
        finally:
            conn.close()

        # 4. Notificar movimiento vía WebSocket
        payload = {
            "evento": "movimiento_individual",
            "vehiculo_id": vehiculo_id,
            "comando_id": comando_id,
            "estado": "ejecutado"
        }
        await manager.broadcast_to_vehicle(vehiculo_id, payload)

        return {"status": "ok", "mensaje": "Movimiento registrado con éxito", "datos": payload}

    def obtener_historial_limitado(self, vehiculo_id: int):
        """Regla de la guía: Devuelve como MÁXIMO los 10 movimientos más recientes"""
        historial = self.ejecutar_sp("sp_obtener_historial", (vehiculo_id,))
        return historial[:10] if historial else []

    async def ejecutar_demo(self, vehiculo_id: int, demo_id: int):
        movimientos = self.ejecutar_sp("sp_obtener_movimientos_demo", (demo_id,))
        
        # Si no hay movimientos registrados en la BD para esa DEMO, generamos una secuencia de prueba
        if not movimientos:
            movimientos = [
                {"comando_id": 19, "orden": 1, "duracion_ms": 1000, "pausa_ms": 500},
                {"comando_id": 19, "orden": 2, "duracion_ms": 1000, "pausa_ms": 500}
            ]

        # Evento de inicio por WS
        await manager.broadcast_to_vehicle(vehiculo_id, {"evento": "demo_inicio", "vehiculo_id": vehiculo_id})

        for mov in movimientos:
            comando = mov.get("comando_id") or mov.get("id_comando", 19)
            orden = mov.get("orden", 1)
            duracion_ms = mov.get("duracion_ms", 1000)
            pausa_ms = mov.get("pausa_ms", 500)

            # Notificar movimiento por WS
            await manager.broadcast_to_vehicle(vehiculo_id, {
                "evento": "demo_movimiento",
                "vehiculo_id": vehiculo_id,
                "comando_id": comando,
                "orden": orden,
                "duracion_ms": duracion_ms,
                "pausa_ms": pausa_ms
            })

            tiempo_espera_sec = (duracion_ms + pausa_ms) / 1000.0
            await asyncio.sleep(tiempo_espera_sec)

            # Actualiza el estado en RDS
            self.ejecutar_sp("sp_actualizar_estado", (vehiculo_id, comando, "DEMO"))

        # Evento de finalización por WS
        await manager.broadcast_to_vehicle(vehiculo_id, {"evento": "demo_fin", "vehiculo_id": vehiculo_id})

        return {"status": "ok", "mensaje": "DEMO ejecutada y transmitida por WebSocket sin guardar en historial"}

def crear_comando_prueba(self, vehiculo_id: int, nombre: str, codigo: str):
        """Ejecuta sp_crear_comando para poblar la BD en RDS"""
        return self.ejecutar_sp("sp_crear_comando", (vehiculo_id, nombre, codigo, "Comando de prueba", 1))

def crear_comando(self, vehiculo_id: int, nombre: str, codigo: str, descripcion: str = "Comando inicial"):
        """Ejecuta el Stored Procedure sp_crear_comando en RDS"""
        return self.ejecutar_sp("sp_crear_comando", (vehiculo_id, nombre, codigo, descripcion, 1))
iot_service = IoTService()