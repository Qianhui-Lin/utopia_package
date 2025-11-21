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
from utopia.microservice.calculate_exposure_indicator.emission_fractions_calculation_json import *


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

class ModelRequest_emission_fraction(BaseModel):
    base_model_id: str
    rate_constant_id: str
    interaction_matrix_id: str
    processed_result_id :str

class ModelResponse_emission_fraction(BaseModel):
    base_model_id: str
    new_model_id: dict
    emission_fraction_id :str
    status: str = "emission fraction calculated and saved to MongoDB"

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
def calcuate_exposure_inidicator(request: ModelRequest):
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
    
@app.post("/calculate_emssison_fraction",response_model = ModelResponse_emission_fraction)
def calculate_emssison_fraction(request: ModelRequest_emission_fraction):
    try:
        dispersing_comp_list = ["Air", "Ocean_Mixed_Water", "Ocean_Surface_Water"]
        base_model_id = request.base_model_id
        rate_constant_id = request.rate_constant_id
        interaction_matrix_id = request.interaction_matrix_id
        base_model_json = model_json_collection.find_one({"_id":ObjectId(request.base_model_id)})
        processed_result = processed_result_collection.find_one({"_id":ObjectId(request.processed_result_id)})
        """Estimate emission fractions"""
        # For estimating the emission fractions we need to make emissions to targeted compartments.

        # Run model with emissions to specific compartments that can cause emissions to remote regions (dispersing compartments) to estimate the emission fractions

        model_results = {}
        new_model_id_dict = {}
        model_json_new_models = {}
        processed_result_new_models = {}
        flow_estimation_new_models = {}

        # run the model with new data (just modifying the recieving compartment)

        # Reasign emissions to the dispersing compartments
        # Identify where the emission is
        base_emiss_dict = base_model_json["emiss_dict_g_s"]
        for compartment, values in base_emiss_dict.items():
            if any(v != 0 for v in values.values()):
                emission_pattern = values
                source_compartment = compartment
                break
        for dispersing_comp in dispersing_comp_list:
            new_dict = copy.deepcopy(base_emiss_dict)

            # Clear all emissions
            for comp in new_dict:
                for k in new_dict[comp]:
                    new_dict[comp][k] = 0

            # Apply the emission pattern to the target compartment
            new_dict[dispersing_comp] = copy.deepcopy(emission_pattern)

            # Create a copy of the model and asign the new emissions dictionary
            new_model_json = copy.deepcopy(base_model_json)
            new_model_json["emiss_dict_g_s"] = new_dict
            # run the new model objet to use new results

            if '_id' in new_model_json:
                del new_model_json['_id']
            inserted_new_model_json = model_json_collection.insert_one(new_model_json)
            new_model_id = str(inserted_new_model_json.inserted_id)
            # Generate new dictionaries moving emission to each dispersing compartment and run the model
            new_model_id_dict[dispersing_comp] = new_model_id

            solve_steady_state_res = requests.post(
                "http://localhost:8006/solve_steady_state",
                json = {
                    "model_id": str(new_model_id),
                    "interaction_matrix_id": interaction_matrix_id
                }
            )
            if solve_steady_state_res.ok:
                print("Response:", solve_steady_state_res.json())
            else:
                print("Error:", solve_steady_state_res.status_code, solve_steady_state_res.text)    
            flow_estimation_res = requests.post(
                "http://localhost:8007/estimate_flow",
                json = {
                    "model_id": str(new_model_id),
                    "rate_constant_id": rate_constant_id,
                    "particle_state_id":solve_steady_state_res.json()["particle_state_id"],
                    "flow_id": solve_steady_state_res.json()["flow_id"]
                }
            )
            if flow_estimation_res.ok:
                print("Response:", flow_estimation_res.json())
            else:
                print("Error:", flow_estimation_res.status_code, flow_estimation_res.text)

            process_result_res = requests.post(
                "http://localhost:8008/process_result",
                json = {
                    "model_id": str(new_model_id),
                    "result_id": solve_steady_state_res.json()["result_id"],
                    "rate_constant_id": rate_constant_id,
                    "interaction_matrix_id": interaction_matrix_id,
                    "particle_state_id":solve_steady_state_res.json()["particle_state_id"],
                    "flow_estimation_id": flow_estimation_res.json()["flow_estimation_id"]
                }
            )
            if process_result_res.ok:
                print("Response:", process_result_res.json())
            else:
                print("Error:", process_result_res.status_code, process_result_res.text)
            
            model_json_new_models[dispersing_comp] = new_model_json
            new_processed_result_id = process_result_res.json()["processed_result_id"]
            new_processed_result_doc = processed_result_collection.find_one({"_id":ObjectId(new_processed_result_id)})
            processed_result_new_models[dispersing_comp] = new_processed_result_doc

            new_flow_estimation_id = flow_estimation_res.json()["flow_estimation_id"]
            new_flow_estimation_doc = flow_estimation_collection.find_one({"_id":ObjectId(new_flow_estimation_id)})
            flow_estimation_new_models[dispersing_comp] = new_flow_estimation_doc

        
        emission_fractions_mass_data = emission_fractions_calculations_json(base_model_json,processed_result, processed_result_new_models,model_json_new_models,flow_estimation_new_models)

        exposure_indicator_doc = exposure_indicator_collection.find_one({"model_id": request.base_model_id})

        if exposure_indicator_doc is None:
            emission_fraction_mass_doc = exposure_indicator_collection.insert_one(
                {"model_id": base_model_id,
                "emission_fraction_mass": emission_fractions_mass_data}
            )
            emission_fraction_id = str(emission_fraction_mass_doc.inserted_id)
        else:
            emission_fraction_id = str(exposure_indicator_doc["_id"])


            exposure_indicator_collection.update_one(
                {"_id": exposure_indicator_doc["_id"]},
                {"$set": {"emission_fraction_mass": emission_fractions_mass_data}}
            )
        

        return ModelResponse_emission_fraction(
            base_model_id = base_model_id,
            new_model_id = new_model_id_dict,
            emission_fraction_id = emission_fraction_id
        )
    


    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")