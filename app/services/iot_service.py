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
            return res
        finally:
            conn.close()

    async def procesar_movimiento_individual(self, vehiculo_id: int, comando_id: int):
        # 1. Validar que el vehículo exista y esté activo[cite: 7]
        vehiculos = self.ejecutar_sp("sp_obtener_vehiculo", (vehiculo_id,))
        if not vehiculos or not vehiculos[0].get("activo", True):
            raise HTTPException(status_code=400, detail="El vehículo no existe o está inactivo")

        # 2. Validar que el comando pertenezca a ese vehículo y esté activo[cite: 7]
        comandos = self.ejecutar_sp("sp_obtener_comandos_vehiculo", (vehiculo_id,))
        comando_valido = any(c.get("id_comando") == comando_id and c.get("activo", True) for c in comandos)
        if not comando_valido:
            raise HTTPException(status_code=400, detail="El comando no pertenece al vehículo o está inactivo")

        # 3. Transacción atómica en RDS: Actualizar estado y registrar en historial[cite: 7, 9]
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.callproc("sp_actualizar_estado", (vehiculo_id, comando_id))
                cursor.callproc("sp_registrar_historial", (vehiculo_id, comando_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Error en transacción RDS: {str(e)}")
        finally:
            conn.close()

        # 4. Notificar movimiento por WebSocket solo a los monitores del vehículo[cite: 7, 8]
        payload = {
            "evento": "movimiento_individual",
            "vehiculo_id": vehiculo_id,
            "comando_id": comando_id,
            "estado": "ejecutado"
        }
        await manager.broadcast_to_vehicle(vehiculo_id, payload)

        return {"status": "ok", "mensaje": "Movimiento registrado con éxito", "datos": payload}

    def obtener_historial_limitado(self, vehiculo_id: int):
        """Devuelve como MÁXIMO los 10 movimientos más recientes."""
        historial = self.ejecutar_sp("sp_obtener_historial", (vehiculo_id,))
        return historial[:10] if historial else []

    async def ejecutar_demo(self, vehiculo_id: int, demo_id: int):
        movimientos = self.ejecutar_sp("sp_obtener_movimientos_demo", (demo_id,))
        if not movimientos:
            raise HTTPException(status_code=404, detail="No se encontraron movimientos para esta DEMO")

        # Evento de INICIO por WebSocket[cite: 8]
        await manager.broadcast_to_vehicle(vehiculo_id, {"evento": "demo_inicio", "vehiculo_id": vehiculo_id})

        ultimo_comando = None
        for mov in movimientos:
            comando = mov.get("comando_id") or mov.get("id_comando")
            orden = mov.get("orden")
            duracion_ms = mov.get("duracion_ms", mov.get("duracion", 1000))
            pausa_ms = mov.get("pausa_ms", mov.get("pausa", 0))

            ultimo_comando = comando

            # Evento por MOVIMIENTO[cite: 8]
            await manager.broadcast_to_vehicle(vehiculo_id, {
                "evento": "demo_movimiento",
                "vehiculo_id": vehiculo_id,
                "comando_id": comando,
                "orden": orden,
                "duracion_ms": duracion_ms,
                "pausa_ms": pausa_ms
            })

            # Respetar duracion_ms + pausa_ms sin bloquear el hilo asíncrono[cite: 8, 9]
            tiempo_espera_sec = (duracion_ms + pausa_ms) / 1000.0
            await asyncio.sleep(tiempo_espera_sec)

            # Actualiza último estado en RDS[cite: 8]
            self.ejecutar_sp("sp_actualizar_estado", (vehiculo_id, comando))

        # Evento de FINALIZACIÓN[cite: 8]
        await manager.broadcast_to_vehicle(vehiculo_id, {"evento": "demo_fin", "vehiculo_id": vehiculo_id})

        # NOTA: NO se ejecuta sp_registrar_historial durante la DEMO (no se inserta en historial)[cite: 6, 8]
        return {"status": "ok", "mensaje": "DEMO transmitida por WebSocket sin guardar en historial"}

iot_service = IoTService()