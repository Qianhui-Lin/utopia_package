from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
import pymongo
import os
# from utopia.utopia import utopiaModel

app = FastAPI()

# MongoDB settings - using environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

 #use this when mongodb runnning in container #use this when mongodb runnning in container

DB_NAME = os.getenv("DB_NAME", "utopia")
CONFIG_COLLECTION = "configure_data"
INPUT_COLLECTION = "input_data"
MODEL_COLLECTION = "model_json"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
config_collection = db[CONFIG_COLLECTION]
input_collection = db[INPUT_COLLECTION]

class DataInput(BaseModel):
    data: Dict[str, Any]

class BatchInput(BaseModel):
    data_list: List[Dict[str, Any]]

@app.post("/input")
def submit_input(data: DataInput):
    try:
        inserted = input_collection.insert_one(data.data)
        return {"status": "success", "input_id": str(inserted.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/input/batch")
def submit_input_batch(payload: BatchInput):
    try:
        # Bulk insert many documents
        result = input_collection.insert_many(payload.data_list)
        input_ids = [str(_id) for _id in result.inserted_ids]

        return {
            "status": "success",
            "count": len(input_ids),
            "input_ids": input_ids
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/config")
def submit_config(data: DataInput):
    try:
        inserted = config_collection.insert_one(data.data)
        return {"status": "success", "config_id": str(inserted.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/init_collections")
def initialize():
    # Caution: This will delete all existing documents!
    config_collection.delete_many({})
    input_collection.delete_many({})
    return {"status": "collections initialized"}
