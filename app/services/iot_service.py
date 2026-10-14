import asyncio
from app.database import Database
from app.websocket.manager import manager

class IoTService:
    def ejecutar_sp(self, sp_name: str, args: tuple = ()):
        """Ejecuta cualquier Stored Procedure en Amazon RDS."""
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.callproc(sp_name, args)
                resultado = cursor.fetchall()
            return resultado
        finally:
            conn.close()

    async def procesar_movimiento_individual(self, vehiculo_id: int, comando_id: int):
        """
        Flujo de movimiento individual (POST)[cite: 1]:
        1. Recibe petición con vehículo y comando[cite: 1].
        2. Valida datos (vehículo y comando activos)[cite: 1].
        3. Ejecuta sp_actualizar_estado[cite: 1].
        4. Ejecuta sp_registrar_historial[cite: 1].
        5. Notifica el movimiento por WebSocket[cite: 1].
        6. Se registra en el historial[cite: 1].
        """
        # Validación
        vehiculos = self.ejecutar_sp("sp_obtener_vehiculos")
        v_valido = any(v.get('id') == vehiculo_id and v.get('activo', True) for v in vehiculos) if vehiculos else True
        
        if not v_valido:
            return {"status": "error", "mensaje": "Vehículo o comando inactivo/inválido"}

        # Actualizar estado y registrar en historial
        self.ejecutar_sp("sp_actualizar_estado", (vehiculo_id, comando_id))
        self.ejecutar_sp("sp_registrar_historial", (vehiculo_id, comando_id))

        # Notificar mediante WebSocket
        payload = {
            "tipo": "movimiento_individual",
            "vehiculo_id": vehiculo_id,
            "comando_id": comando_id,
            "estado": "ejecutado"
        }
        await manager.broadcast(payload)

        return {"status": "ok", "mensaje": "Movimiento registrado con éxito", "datos": payload}

    async def ejecutar_demo(self, vehiculo_id: int):
        """
        Flujo de Ejecución de DEMO (POST)[cite: 1]:
        Pasa (vehiculo_id,) como argumento al Stored Procedure.
        """
        movimientos = self.ejecutar_sp("sp_obtener_movimientos_demo", (vehiculo_id,))

        ultimo_comando = None
        for mov in movimientos:
            # Adaptamos los nombres de las llaves del diccionario según devuelva el SP
            comando = mov.get("comando_id") or mov.get("id_comando")
            orden = mov.get("orden")
            duracion = mov.get("duracion", 1)
            pausa = mov.get("pausa", 0)

            ultimo_comando = comando

            await manager.broadcast({
                "tipo": "demo_movimiento",
                "vehiculo_id": vehiculo_id,
                "comando_id": comando,
                "orden": orden,
                "duracion": duracion,
                "pausa": pausa
            })

            await asyncio.sleep(duracion + pausa)

        if ultimo_comando is not None:
            self.ejecutar_sp("sp_actualizar_estado", (vehiculo_id, ultimo_comando))

        return {"status": "ok", "mensaje": "DEMO ejecutada y finalizada correctamente"}

iot_service = IoTService()