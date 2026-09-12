from fastapi import FastAPI, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Saltwater Intrusion API", version="1.0.0")

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

@app.get("/")
def read_root():
    return {"message": "Welcome to Saltwater Intrusion API"}

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
