from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import pymongo
import os
# from utopia.utopia import utopiaModel

app = FastAPI()

# MongoDB settings (could use env vars for production)
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "utopia"
CONFIG_COLLECTION = "configure_data"
INPUT_COLLECTION = "input_data"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
config_collection = db[CONFIG_COLLECTION]
input_collection = db[INPUT_COLLECTION]

class DataInput(BaseModel):
    data: Dict[str, Any]

@app.post("/input")
def submit_input(data: DataInput):
    try:
        inserted = input_collection.insert_one(data.data)
        return {"status": "success", "inserted_id": str(inserted.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config")
def submit_config(data: DataInput):
    try:
        inserted = config_collection.insert_one(data.data)
        return {"status": "success", "inserted_id": str(inserted.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/init_collections")
def initialize():
    # Caution: This will delete all existing documents!
    config_collection.delete_many({})
    input_collection.delete_many({})
    return {"status": "collections initialized"}
