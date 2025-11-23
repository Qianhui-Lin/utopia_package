from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import pymongo
import os
from bson import ObjectId
from utopia.globalConstants import *
import utopia.microservice.generate_rate_constant.RC_generator_json_ms as RC_generator

app = FastAPI(title="Rate Constants Generator Service", version="1.0.0")

# MongoDB settings - using environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

 #use this when mongodb runnning in container

DB_NAME = os.getenv("DB_NAME", "utopia")
CONFIG_COLLECTION = "configure_data"
INPUT_COLLECTION = "input_data"
MODEL_COLLECTION = "model_json"
RATE_CONSTANT_COLLECTION = "rate_constant"


client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
config_collection = db[CONFIG_COLLECTION]
input_collection = db[INPUT_COLLECTION]
model_json_collection = db[MODEL_COLLECTION]
rate_constant_collection = db[RATE_CONSTANT_COLLECTION]


class ModelRequest(BaseModel):
    model_id: str

class ModelResponse(BaseModel):
    model_id: str
    rate_constant_id: str
    status: str = "updated"


def get_compartment_for_particle(particle, dict_comp):
    """
    Returns the compartment dictionary from dict_comp corresponding to the particle's Pcompartment_Cname.
    """
    cname = particle.get("Pcompartment_Cname")
    if cname is None:
        raise ValueError("Particle does not have 'Pcompartment_Cname'")
    if cname not in dict_comp:
        raise ValueError(f"Compartment name '{cname}' not found in dict_comp")
    return dict_comp[cname]

def generate_rate_constants_json(model_id):
    """Generate rate constants for all particles in the model."""
    model_json = model_json_collection.find_one({'_id':ObjectId(model_id)})
    dict_comp = model_json["dict_comp"]
    system_particle_rate_constant_list = []
    
    for particle in model_json["system_particle_object_list"]:
        try:
            compartment = get_compartment_for_particle(particle, dict_comp)
            processes = compartment["processess"]
            rate_constants = dict.fromkeys([f'k_{p}' for p in processes])
            # particle["RateConstants"] = dict.fromkeys([f'k_{p}' for p in processes])
            
            #for process in particle["RateConstants"]:
            for process in rate_constants:
                proc = process[2:]  # Remove 'k_' prefix
                if hasattr(RC_generator, proc):
                    rate_constants[process] = getattr(RC_generator, proc)(
                        particle, model_json
                    )
                else:
                    # Handle missing process method
                    #particle["RateConstants"][process] = None
                    rate_constants[process] = None
                    print(f"Warning: Process method '{proc}' not found in RC_generator")
        
            system_particle_rate_constant_list.append({
                "Pcode": particle["Pcode"],
                "RateConstants": rate_constants
            })            
                    
        except Exception as e:
            # raise HTTPException(status_code=400, detail=f"Error processing particle: {str(e)}")
            print(f"Error processing particle {particle.get('Pname', '<unknown>')}: {str(e)}")

    return {
        "model_id": str(model_id),
        "system_particle_rate_constant_list": system_particle_rate_constant_list
    }
    
    # Prepare the document
    doc = {
        "model_id": str(model_id),
        "system_particle_rate_constant_list": system_particle_rate_constant_list
    }
    # Upsert (update if exists, insert if not)
    result = rate_constant_collection.update_one(
        {"model_id": str(model_id)},
        {"$set": doc},
        upsert=True
    )
    # Get the string _id of the document
    if result.upserted_id is not None:
        rate_constant_id = str(result.upserted_id)
    else:
        rc_doc = rate_constant_collection.find_one({"model_id": str(model_id)}, {"_id": 1})
        rate_constant_id = str(rc_doc["_id"])

    print("Rate constant document _id:", rate_constant_id)
    
        
    # model_json_collection.replace_one({'_id': ObjectId(model_id)}, model_json)
    
    return model_id,model_json,rate_constant_id



@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Rate Constants Generator Service is running", "status": "healthy"}


@app.post("/init_rate_constant_collection")
def init_rate_constant_collection():
    try:
        result = rate_constant_collection.delete_many({})
        return {
            "status": "success",
            "message": f"All {result.deleted_count} rate constant records have been deleted."
        }
    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/generate_rate_constants", response_model = ModelResponse)
async def generate_rate_constants(request: ModelRequest):
    """
    Generate rate constants for all particles in the system.
    
    Args:
        model: Model containing system_particle_object_list and dict_comp
        
    Returns:
        Updated model with rate constants generated for each particle
    """
    try:
        rc_data = generate_rate_constants_json(request.model_id)
        # Upsert into the rate_constant_collection
        result = rate_constant_collection.update_one(
            {"model_id": rc_data["model_id"]},
            {"$set": rc_data},
            upsert=True
        )
        # Get _id string
        if result.upserted_id is not None:
            rate_constant_id = str(result.upserted_id)
        else:
            rc_doc = rate_constant_collection.find_one({"model_id": rc_data["model_id"]}, {"_id": 1})
            rate_constant_id = str(rc_doc["_id"])

        return ModelResponse(
            model_id = rc_data["model_id"],
            rate_constant_id = rate_constant_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# trigger workflow