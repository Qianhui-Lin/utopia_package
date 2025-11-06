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
from utopia.microservice.process_result.process_result_function import *
from utopia.microservice.process_result.extract_results_by_compartment_function import *

app = FastAPI(title="Results Processor Service", version="1.0.0")

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

class ModelRequest(BaseModel):
    model_id: str
    result_id: str
    rate_constant_id: str
    interaction_matrix_id: str
    particle_state_id: str
    flow_estimation_id: str

class ModelResponse(BaseModel):
    model_id: str
    processed_result_id :str
    status: str = "processed results generated and saved to mongodb"


class ModelRequest_comp(BaseModel):
    model_id: str
    processed_result_id: str
    flow_estimation_id: str

class ModelResponse_comp(BaseModel):
    model_id: str
    processed_result_id :str
    status: str = "rusults by compartment extracted and saved to mongodb"


class ModelRequest_balance(BaseModel):
    model_id: str
    processed_result_id: str

class ModelResponse_balance(BaseModel):
    model_id: str
    processed_result_id :str
    status: str = "mass balance results by component generated and saved to mongodb"


@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Processing Result Service is running", "status": "healthy"}

@app.post("/init_processed_result_collection")
def init_processed_result_collection():
    try:
        result = processed_result_collection.delete_many({})
        return {
            "status": "success",
            "message": f"All {result.deleted_count} processed result records have been deleted."
        }
    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/process_result",response_model = ModelResponse)
def process_result(request: ModelRequest):
    try:
        interaction_data = {
                "model_id": request.model_id,
                "rate_constant_id": request.rate_constant_id,
                "interaction_matrix_id":request.interaction_matrix_id
        }
        
        interaction_matrix_dict_res = requests.post("http://localhost:8005/generate_interaction_matrix_dict", json = interaction_data)

        #interaction_matrix_dict_res = requests.post("http://generate-interaction-matrix:8005/generate_interaction_matrix_dict", json = interaction_data)
        
        if interaction_matrix_dict_res.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Downstream error: {interaction_matrix_dict_res.text[:200]}")

        interaction_matrix_dict = interaction_collection.find_one(
            {"_id": ObjectId(request.interaction_matrix_id)},
            {"interaction_dict": 1, "_id": 0}
        )["interaction_dict"]
        model_json = model_json_collection.find_one({"_id":ObjectId(request.model_id)})
        result = result_collection.find_one({"_id":ObjectId(request.result_id)})
        flow_estimation = flow_estimation_collection.find_one({"_id":ObjectId(request.flow_estimation_id)})
        particle_state = particle_state_collection.find_one({"_id":ObjectId(request.particle_state_id)})
        processed_results_df = process_results_json(model_json, result,flow_estimation, particle_state,interaction_matrix_dict)
        processed_results_with_index = processed_results_df.reset_index()
        insert_result = processed_result_collection.insert_one({
            "model_id": request.model_id,
            "processed_result": processed_results_with_index.to_dict('records')
        })
        # Step 3: Return inserted ID
        return ModelResponse(
            model_id = request.model_id,
            processed_result_id = str(insert_result.inserted_id)
            )
            

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    


@app.post("/extract_results_by_compartment",response_model = ModelResponse_comp)
def process_result(request: ModelRequest_comp):
    try:
        interaction_data = {
                "model_id": request.model_id,
                "processed_result_id": request.processed_result_id,
                "flow_estimation_id":request.flow_estimation_id
        }
        
        model_json = model_json_collection.find_one({"_id":ObjectId(request.model_id)})
        processed_results = processed_result_collection.find_one({"_id":ObjectId(request.processed_result_id)})
        flow_estimation = flow_estimation_collection.find_one({"_id":ObjectId(request.flow_estimation_id)})
        # print("processed_results:", processed_results)
        processed_results_df = extract_results_by_compartment_json(processed_results,model_json,flow_estimation)
        processed_results_with_index = processed_results_df.reset_index()
        update_result = processed_result_collection.update_one(
            {
            '_id': ObjectId(request.processed_result_id)
            },
            {
                '$set':{
                    'model_id': request.model_id,
                    'results_by_comp': processed_results_with_index.to_dict('records')
                }

            }
        )
        # Step 3: Return inserted ID
        return ModelResponse_comp(
            model_id = request.model_id,
            processed_result_id = str(request.processed_result_id)
            )
            

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

@app.post("/mass_balance_by_compartment",response_model = ModelResponse_balance)
def process_result(request: ModelRequest_balance):
    try:
        processed_results = processed_result_collection.find_one({"_id": ObjectId(request.processed_result_id)})
        if not processed_results:
            raise HTTPException(status_code=404, detail="processed_result_id not found")
        df = pd.DataFrame(processed_results["results_by_comp"])
        model_json = model_json_collection.find_one({'_id':ObjectId(request.model_id)})
        mass_balances = []
        for i in range(len(df)):
            comp = df['Compartments'].iloc[i]
            inflow = df['Total_inflows_g_s'].iloc[i]
            outflow = df['Total_outflows_g_s'].iloc[i]
            emissions = sum(model_json["emiss_dict_g_s"][comp].values())

            balance = inflow + emissions - outflow

            mass_balances.append({
                "compartment": comp,
                "mass_balance_g_s": balance
            })

        # Save back into processed_result_collection
        processed_result_collection.update_one(
            {"_id": ObjectId(request.processed_result_id)},
            {"$set": {"mass_balance_by_comp": mass_balances}}
        )

        return ModelResponse_balance(
            model_id=request.model_id,
            processed_result_id=request.processed_result_id,
            status="mass balance results by component generated and saved to mongodb"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))