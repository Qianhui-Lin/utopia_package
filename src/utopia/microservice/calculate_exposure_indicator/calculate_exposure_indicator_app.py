import matplotlib.pyplot as plt
import numpy as np
import requests
import seaborn as sns
from matplotlib.colors import LogNorm
import pandas as pd
from utopia.helpers import *
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pymongo
import os
from bson import ObjectId
from utopia.microservice.calculate_exposure_indicator.exposure_indicators_calculation_json import *


app = FastAPI(title="Exposure Indicator Calculating Service", version="1.0.0")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/") 
DB_NAME = os.getenv("DB_NAME", "utopia")
MODEL_COLLECTION = "model_json"
INTERACTION_MATRIX_COLLECTION = "interaction"
RESULT_COLLECTION = "result"
FLOW_COLLECTION = "flow"
RATE_CONSTANT_COLLECTION = "rate_constant"
PARTICLE_STATE_COLLECTION = "particle_state"
FLOW_ESTIMATION_COLLECTION = "flow_estimation"
PROCESSED_RESULT_COLLECTION = "processed_result"
EXPOSURE_INDICATOR_COLLECTION = "exposure_inidcator"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
model_json_collection = db[MODEL_COLLECTION]
interaction_collection = db[INTERACTION_MATRIX_COLLECTION]
result_collection = db[RESULT_COLLECTION]
flow_collection = db[FLOW_COLLECTION]
rate_constant_collection = db[RATE_CONSTANT_COLLECTION]
particle_state_collection = db[PARTICLE_STATE_COLLECTION]
flow_estimation_collection = db[FLOW_ESTIMATION_COLLECTION]
processed_result_collection = db[PROCESSED_RESULT_COLLECTION]
exposure_indicator_collection = db[EXPOSURE_INDICATOR_COLLECTION]

class ModelRequest(BaseModel):
    model_id: str
    flow_estimation_id: str
    processed_result_id :str
    rate_constant_id: str
    particle_state_id: str

class ModelResponse(BaseModel):
    model_id: str
    exposure_indicator_id :str
    status: str = "exposure indicator calculated and saved to MongoDB"

@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Exposure Indicator Calculating Service is running", "status": "healthy"}

def get_system_particle_object_list_merged(model_id, rate_constant_id, particle_state_id):
    model_json = model_json_collection.find_one({'_id':ObjectId(model_id)})
        # Fetch rate constants
    rate_constant_doc = rate_constant_collection.find_one({
            '_id': ObjectId(rate_constant_id)
        })
        # Fetch particle states
    particle_state_doc = particle_state_collection.find_one({
            '_id': ObjectId(particle_state_id)
        })

    if not rate_constant_doc or not particle_state_doc:
            raise ValueError("Required particle data not found in collections")
        
        # Create a mapping of Pcode to rate constants
    rate_constants_map = {
            p['Pcode']: p['RateConstants'] 
            for p in rate_constant_doc.get('system_particle_rate_constant_list', [])
        }

        # Create a mapping of Pcode to Pcompartment_Cname from the original model_json
    pcode_to_compartment = {}
    if 'system_particle_object_list' in model_json:
            for original_particle in model_json['system_particle_object_list']:
                if 'Pcode' in original_particle and 'Pcompartment_Cname' in original_particle:
                    pcode_to_compartment[original_particle['Pcode']] = original_particle['Pcompartment_Cname']

        # Merge particle state with rate constants and compartment info
    system_particle_object_list = []
    for particle_state in particle_state_doc.get('system_particle_state_list', []):
            merged_particle = particle_state.copy()
            pcode = particle_state['Pcode']
            
            # Add rate constants if available
            if pcode in rate_constants_map:
                merged_particle['RateConstants'] = rate_constants_map[pcode]
            else:
                merged_particle['RateConstants'] = {}
            
            # Add Pcompartment_Cname from the original model_json mapping
            if pcode in pcode_to_compartment:
                merged_particle['Pcompartment_Cname'] = pcode_to_compartment[pcode]
            else:
                # If not found in mapping, you might need to handle this case
                # Perhaps log a warning or use a default compartment
                print(f"Warning: No compartment found for particle {pcode}")
            
            system_particle_object_list.append(merged_particle)
    return system_particle_object_list


@app.post("/init_exposure_indicator_collection")
def init_exposure_indicator_collection():
    try:
        result = exposure_indicator_collection.delete_many({})
        return {
            "status": "success",
            "message": f"All {result.deleted_count} exposure indicator records have been deleted."
        }
    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@app.post("/calculate_exposure_indicator",response_model = ModelResponse)
def process_result(request: ModelRequest):
    try:
        model_id = request.model_id
        rate_constant_id = request.rate_constant_id
        particle_state_id = request.particle_state_id
        system_particle_object_list_merged = get_system_particle_object_list_merged(model_id, rate_constant_id, particle_state_id)
        model_json = model_json_collection.find_one({"_id":ObjectId(request.model_id)})
        flow_estimation = flow_estimation_collection.find_one({"_id":ObjectId(request.flow_estimation_id)})
        result_doc = processed_result_collection.find_one({"_id":ObjectId(request.processed_result_id)})
        result = pd.DataFrame(result_doc["processed_result"])
        overall_exposure_indicators, size_fraction_indicators = Exposure_indicators_calculation_json(model_json,flow_estimation,result,system_particle_object_list_merged)

        exposure_doc = {
            "model_id": request.model_id,
            "overall_exposure_indicators": overall_exposure_indicators.to_dict(orient="records"),
            "size_fraction_indicators": size_fraction_indicators.to_dict(orient="records"),
        }
        insert_exposure_result = exposure_indicator_collection.insert_one(exposure_doc)

        # Return response
        return ModelResponse(
            model_id=request.model_id,
            exposure_indicator_id=str(insert_exposure_result.inserted_id)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")