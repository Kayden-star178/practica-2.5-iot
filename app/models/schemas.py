from pydantic import BaseModel

class MovimientoRequest(BaseModel):
    vehiculo_id: int
    comando_id: int

class DemoRequest(BaseModel):
    vehiculo_id: int