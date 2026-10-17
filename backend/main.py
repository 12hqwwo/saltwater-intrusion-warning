from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from backend.pilot_spatial import router as pilot_spatial_router

app = FastAPI(title="Saltwater Intrusion API", version="1.0.0")
app.include_router(pilot_spatial_router)

# Mock data
class SalinityRecord(BaseModel):
    station: str
    date: str
    conductivity_mS_per_m: float
    
MOCK_DATA = [
    {"station": "MyTho", "date": "2024-01-01", "conductivity_mS_per_m": 105.2},
    {"station": "MyTho", "date": "2024-02-01", "conductivity_mS_per_m": 110.5},
    {"station": "MyTho", "date": "2024-03-01", "conductivity_mS_per_m": 150.0},
]

@app.get("/", include_in_schema=False)
def read_root():
    return RedirectResponse(url="/pilot/spatial/map")

@app.get("/salinity/history", response_model=List[SalinityRecord])
def get_salinity_history(station: Optional[str] = None):
    """
    Get historical salinity data.
    """
    if station:
        filtered_data = [r for r in MOCK_DATA if r["station"].lower() == station.lower()]
        if not filtered_data:
            raise HTTPException(status_code=404, detail="Station not found")
        return filtered_data
    return MOCK_DATA

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    print("Run API with command: uvicorn main:app --reload")
