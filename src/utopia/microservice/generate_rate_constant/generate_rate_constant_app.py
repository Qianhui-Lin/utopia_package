from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import pymongo
import os
from bson import ObjectId
from utopia.globalConstants import *
import utopia.microservice.generate_rate_constant.RC_generator_json_ms as RC_generator
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
logger = logging.getLogger(__name__)

MAX_WORKERS = int(os.getenv("RC_MAX_WORKERS", "4"))

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

class RateConstantBatchRequest(BaseModel):
    model_ids: List[str]


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

def compute_rate_constants_for_model(model_id: str) -> dict:
    """
    Generate rate constants for all particles in a single model.
    Returns a dict: {"model_id": ..., "system_particle_rate_constants": [...]}
    Intended to be called from a worker (thread/process).
    """
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    model_json_collection = db["model_json"]
    try:
        model_json = model_json_collection.find_one({"_id": ObjectId(model_id)})
        if model_json is None:
            # Let the caller decide how to handle this
            raise ValueError(f"model_id {model_id} not found")

        dict_comp = model_json["dict_comp"]
        system_particle_rate_constants = []

        for particle in model_json["system_particle_object_list"]:
            try:
                cname = particle["Pcompartment_Cname"]
                compartment = dict_comp[cname]
                processes = compartment["processess"]

                # Initialise RC dict
                rc_dict = {f"k_{p}": None for p in processes}

                for process_key in rc_dict:
                    proc = process_key[2:]   # remove "k_"
                    if hasattr(RC_generator, proc):
                        rc_dict[process_key] = getattr(RC_generator, proc)(
                            particle, model_json
                        )
                    else:
                        rc_dict[process_key] = None

                system_particle_rate_constants.append({
                    "Pcode": particle["Pcode"],
                    "RateConstants": rc_dict
                })

            except Exception as e:
                # Log and continue with next particle
                print(f"[RC ERROR] model={model_id}, particle={particle.get('Pname','<unknown>')}: {e}")
                continue

        # Build the document to save
        rc_data = {
            "model_id": model_id,
            "system_particle_rate_constant_list": system_particle_rate_constants,
        }        
        # Upsert into DB
        result = rate_constant_collection.update_one(
            {"model_id": model_id},
            {"$set": rc_data},
            upsert=True
        )
        if result.upserted_id is not None:
            rate_constant_id = str(result.upserted_id)
        else:
            print("No upserted_id, fetching existing document _id")
        return {
            "model_id": model_id,
            "rate_constant_id": rate_constant_id
        }
    finally:
        client.close()

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


@app.post("/generate_rate_constants/batch")
def generate_rate_constants_batch(req: RateConstantBatchRequest):
    """
    Generate rate constants for a list of model_ids.
    Uses a process pool so models are processed in parallel, not one by one.
    """
    model_ids = req.model_ids
    if not model_ids:
        return {"status": "success", "count": 0, "results": []}

    results = []
    errors = []

    # Run models in parallel
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_mid = {
            executor.submit(compute_rate_constants_for_model, mid): mid
            for mid in model_ids
        }

        for future in as_completed(future_to_mid):
            mid = future_to_mid[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                # Log per-model error but don’t kill the whole batch
                print(f"[RC BATCH ERROR] model_id={mid}: {e}")
                errors.append({"model_id": mid, "error": str(e)})

    response = {
        "status": "success",
        "count": len(results),
        "results": results,
    }

    if errors:
        response["errors"] = errors

    return response