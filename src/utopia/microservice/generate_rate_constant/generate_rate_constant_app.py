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


client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
config_collection = db[CONFIG_COLLECTION]
input_collection = db[INPUT_COLLECTION]
model_json_collection = db[MODEL_COLLECTION]



class ModelRequest(BaseModel):
    model_id: str

class ModelResponse(BaseModel):
    model_id: str
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
    
    for particle in model_json["system_particle_object_list"]:
        try:
            compartment = get_compartment_for_particle(particle, dict_comp)
            processes = compartment["processess"]
            particle["RateConstants"] = dict.fromkeys([f'k_{p}' for p in processes])
            
            for process in particle["RateConstants"]:
                proc = process[2:]  # Remove 'k_' prefix
                # Check if the process method exists in RC_generator
                if hasattr(RC_generator, proc):
                    particle["RateConstants"][process] = getattr(RC_generator, proc)(
                        particle, model_json
                    )
                else:
                    # Handle missing process method
                    particle["RateConstants"][process] = None
                    print(f"Warning: Process method '{proc}' not found in RC_generator")
        
            
                    
        except Exception as e:
            # raise HTTPException(status_code=400, detail=f"Error processing particle: {str(e)}")
            print(f"Error processing particle {particle.get('Pname', '<unknown>')}: {str(e)}")
        
    model_json_collection.replace_one({'_id': ObjectId(model_id)}, model_json)
    
    return {"model_id": model_id}



@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Rate Constants Generator Service is running", "status": "healthy"}


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
        result = generate_rate_constants_json(request.model_id)
        return ModelResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
