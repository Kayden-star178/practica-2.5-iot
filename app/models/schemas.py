from pydantic import BaseModel, Field

class MovimientoRequest(BaseModel):
    vehiculo_id: int = Field(..., gt=0, description="ID del vehículo")
    comando_id: int = Field(..., gt=0, description="ID del comando a ejecutar")

class DemoRequest(BaseModel):
    vehiculo_id: int = Field(..., gt=0, description="ID del vehículo")
    demo_id: int = Field(..., gt=0, description="ID de la DEMO registrada en RDS")