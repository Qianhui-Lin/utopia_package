# Fuction to genarate the interactions matrix fot the UTOPIA model


import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import pymongo
import os
from bson import ObjectId

from utopia.microservice.generate_interaction_matrix.fillInteractions_fun_OOP_json_function import *
from utopia.microservice.generate_interaction_matrix.fillInteractions_fun_OOP_json_dict_function import *


app = FastAPI(title="Interaction Matrix Generator Service", version="1.0.0")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
# testing locally
# MONGO_URI = "mongodb://utopiauser:utopiapassword@localhost:27018/utopia?authSource=admin"
DB_NAME = os.getenv("DB_NAME", "utopia")
MODEL_COLLECTION = "model_json"
INTERACTION_MATRIX_COLLECTION = "interaction"
RATE_CONSTANT_COLLECTION = "rate_constant"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
model_json_collection = db[MODEL_COLLECTION]
interaction_collection = db[INTERACTION_MATRIX_COLLECTION]
rate_constant_collection = db[RATE_CONSTANT_COLLECTION]

class ModelRequest(BaseModel):
    model_id: str
    rate_constant_id: str

class ModelResponse(BaseModel):
    model_id: str
    interaction_matrix_id: str
    status: str = "interaction matrix generated and saved to mongodb"

class ModelRequest_dict(BaseModel):
    model_id: str
    rate_constant_id: str
    interaction_matrix_id: str

class ModelResponse_dict(BaseModel):
    model_id: str
    interaction_matrix_id: str
    status: str = "interaction matrix_dict generated and saved to mongodb"


@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Interaction Matrix Generator Generator Service is running", "status": "healthy"}

@app.post("/init_interaction_matrix_collection")
def init_interaction_matrix_collection():
    try:
        result = interaction_collection.delete_many({})
        return {
            "status": "success",
            "message": f"All {result.deleted_count} interaction matrix records have been deleted."
        }
    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/generate_interaction_matrix",response_model = ModelResponse)
def generate_interaction_matrix(request: ModelRequest):
    try:
        model_id = ObjectId(request.model_id)
        rate_constant_id = ObjectId(request.rate_constant_id)
        model_json = model_json_collection.find_one({'_id': model_id})
        rate_constant = rate_constant_collection.find_one({'_id': rate_constant_id})
        interaction_matrix = fillInteractions_fun_OOP_json(model_json,rate_constant)
        result = interaction_collection.insert_one({
            "model_id": request.model_id,
            "interaction_df": interaction_matrix
        })
        interaction_matrix_id = str(result.inserted_id)
        return ModelResponse(
            model_id=request.model_id,
            interaction_matrix_id=str(result.inserted_id),
            status="interaction matrix generated and saved to MongoDB"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/generate_interaction_matrix_dict",response_model = ModelResponse_dict)
def generate_interaction_matrix(request: ModelRequest_dict):
    try:
        model_id = ObjectId(request.model_id)
        rate_constant_id = ObjectId(request.rate_constant_id)
        model_json = model_json_collection.find_one({'_id': model_id})
        rate_constant = rate_constant_collection.find_one({'_id': rate_constant_id})
        interaction_matrix_dict = fillInteractions_fun_OOP_dict_json(model_json,rate_constant)
        # Update the document to add interaction_dict
        interaction_collection.update_one(
            {"_id": ObjectId(request.interaction_matrix_id)},
            {"$set": {"interaction_dict": interaction_matrix_dict}}
        )
        interaction_matrix_id = request.interaction_matrix_id
        return ModelResponse(
            model_id=request.model_id,
            interaction_matrix_id= interaction_matrix_id,
            status="interaction matrix_dict generated and saved to MongoDB"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

        
        



#sp1.
#sp2.