import asyncio
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
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import asynccontextmanager
from utopia.microservice.calculate_exposure_indicator.exposure_indicators_calculation_json import *
from utopia.microservice.calculate_exposure_indicator.emission_fractions_calculation_json import *



if os.getenv("IN_DOCKER"):
    BASE_URL_SOLVE_STEADY = "http://solve-steady-state:8006"
    BASE_URL_ESTIMATE_FLOW = "http://estimate-flow:8007"
    BASE_URL_PROCESS_RESULT = "http://process-result:8008"

else:
    BASE_URL_SOLVE_STEADY = "http://localhost:8006"
    BASE_URL_ESTIMATE_FLOW =  "http://localhost:8007"
    BASE_URL_PROCESS_RESULT = "http://localhost:8008"

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
EXPOSURE_INDICATOR_COLLECTION = "exposure_indicator"

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

solver_executor: ProcessPoolExecutor | None = None
worker_db = None

def init_worker():
    """
    Called once in each worker process.
    Creates a MongoDB connection for that process.
    """
    global worker_db
    client = pymongo.MongoClient(MONGO_URI)
    worker_db = client[DB_NAME]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global solver_executor
    
    solver_executor = ProcessPoolExecutor(
        max_workers=MAX_WORKERS,
        initializer=init_worker
    )
    print(f"[interaction] Started ProcessPoolExecutor with {MAX_WORKERS} workers")
    
    yield
    
    solver_executor.shutdown(wait=True)
    print("[exposure indicator] ProcessPoolExecutor shut down")


app = FastAPI(lifespan=lifespan, title="Exposure Indicator Calculating Service", version="1.0.0")



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

class ExposureIndicatorBatchRequest(BaseModel):
    items: list[ModelRequest]   # reuse your existing ModelRequest


class SingleExposureIndicatorResult(BaseModel):
    model_id: str
    exposure_indicator_id: str | None = None
    status: str


class ExposureIndicatorBatchResponse(BaseModel):
    count: int
    successful: int
    failed: int
    results: list[SingleExposureIndicatorResult]

def run_single_exposure_indicator(req: ModelRequest) -> SingleExposureIndicatorResult:
    try:
        model_id = req.model_id

        # Fetch all documents using worker_db
        model_json = worker_db[MODEL_COLLECTION].find_one({"_id": ObjectId(req.model_id)})
        flow_estimation = worker_db[FLOW_ESTIMATION_COLLECTION].find_one({"_id": ObjectId(req.flow_estimation_id)})
        result_doc = worker_db[PROCESSED_RESULT_COLLECTION].find_one({"_id": ObjectId(req.processed_result_id)})
        rate_constant_doc = worker_db[RATE_CONSTANT_COLLECTION].find_one({"_id": ObjectId(req.rate_constant_id)})
        particle_state_doc = worker_db[PARTICLE_STATE_COLLECTION].find_one({"_id": ObjectId(req.particle_state_id)})

        required_docs = {
            "model_json": model_json,
            "flow_estimation": flow_estimation,
            "result_doc": result_doc,
            "rate_constant_doc": rate_constant_doc,
            "particle_state_doc": particle_state_doc,
        }

        missing_docs = [name for name, doc in required_docs.items() if doc is None]

        if missing_docs:
            return SingleExposureIndicatorResult(
                model_id=model_id,
                status=f"failed: missing documents - {', '.join(missing_docs)}"
            )

        # Pure data transformation - same function works everywhere
        system_particle_object_list_merged = get_system_particle_object_list_merged(
            model_json, rate_constant_doc, particle_state_doc
        )

        result_df = pd.DataFrame(result_doc["processed_result"])
        overall_exposure_indicators, size_fraction_indicators = Exposure_indicators_calculation_json(
            model_json, flow_estimation, result_df, system_particle_object_list_merged
        )

        exposure_doc = {
            "model_id": model_id,
            "overall_exposure_indicators": overall_exposure_indicators.to_dict(orient="records"),
            "size_fraction_indicators": size_fraction_indicators.to_dict(orient="records"),
        }
        insert_res = worker_db[EXPOSURE_INDICATOR_COLLECTION].insert_one(exposure_doc)

        return SingleExposureIndicatorResult(
            model_id=model_id,
            exposure_indicator_id=str(insert_res.inserted_id),
            status="success"
        )

    except Exception as e:
        return SingleExposureIndicatorResult(
            model_id=req.model_id,
            status=f"failed: {str(e)}"
        )


@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Exposure Indicator Calculating Service is running", "status": "healthy"}

def get_system_particle_object_list_merged(model_json: dict, rate_constant_doc: dict, particle_state_doc: dict) -> list:
    """
    Merge particle state with rate constants and compartment info.
    
    Args:
        model_json: The model document
        rate_constant_doc: The rate constant document
        particle_state_doc: The particle state document
    
    Returns:
        List of merged particle objects
    """
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
def calculate_exposure_indicator(request: ModelRequest):
    try:
        # Fetch all documents first
        model_json = model_json_collection.find_one({"_id": ObjectId(request.model_id)})
        flow_estimation = flow_estimation_collection.find_one({"_id": ObjectId(request.flow_estimation_id)})
        result_doc = processed_result_collection.find_one({"_id": ObjectId(request.processed_result_id)})
        rate_constant_doc = rate_constant_collection.find_one({"_id": ObjectId(request.rate_constant_id)})
        particle_state_doc = particle_state_collection.find_one({"_id": ObjectId(request.particle_state_id)})

        if not all([model_json, flow_estimation, result_doc, rate_constant_doc, particle_state_doc]):
            raise HTTPException(status_code=404, detail="One or more required documents not found")

        system_particle_object_list_merged = get_system_particle_object_list_merged(
            model_json, rate_constant_doc, particle_state_doc
        )

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
    

@app.post("/calculate_exposure_indicator/batch", response_model=ExposureIndicatorBatchResponse)
async def calculate_exposure_indicator_batch(req: ExposureIndicatorBatchRequest):
    if solver_executor is None:
        raise HTTPException(status_code=500, detail="Executor not initialized")

    # Submit tasks in parallel
    tasks = [
        asyncio.get_running_loop().run_in_executor(
            solver_executor,
            run_single_exposure_indicator,
            item
        )
        for item in req.items
    ]

    # Collect results
    results = await asyncio.gather(*tasks)

    successful = sum(1 for r in results if r.status == "success")
    failed = len(results) - successful

    return ExposureIndicatorBatchResponse(
        count=len(results), 
        successful=successful,
        failed=failed,
        results=results
    )

    
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

            # solve_steady_state_res = requests.post(
            #     "http://localhost:8006/solve_steady_state",
            #     json = {
            #         "model_id": str(new_model_id),
            #         "interaction_matrix_id": interaction_matrix_id
            #     }
            # )
            solve_steady_state_res = requests.post(
                f"{BASE_URL_SOLVE_STEADY}/solve_steady_state",
                json = {
                    "model_id": str(new_model_id),
                    "interaction_matrix_id": interaction_matrix_id
                }
            )
            if solve_steady_state_res.ok:
                print("Response:", solve_steady_state_res.json())
            else:
                print("Error:", solve_steady_state_res.status_code, solve_steady_state_res.text)    
            # flow_estimation_res = requests.post(
            #     "http://localhost:8007/estimate_flow",
            #     json = {
            #         "model_id": str(new_model_id),
            #         "rate_constant_id": rate_constant_id,
            #         "particle_state_id":solve_steady_state_res.json()["particle_state_id"],
            #         "flow_id": solve_steady_state_res.json()["flow_id"]
            #     }
            # )
            flow_estimation_res = requests.post(
                f"{BASE_URL_ESTIMATE_FLOW}/estimate_flow",
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

            # process_result_res = requests.post(
            #     "http://localhost:8008/process_result",
            #     json = {
            #         "model_id": str(new_model_id),
            #         "result_id": solve_steady_state_res.json()["result_id"],
            #         "rate_constant_id": rate_constant_id,
            #         "interaction_matrix_id": interaction_matrix_id,
            #         "particle_state_id":solve_steady_state_res.json()["particle_state_id"],
            #         "flow_estimation_id": flow_estimation_res.json()["flow_estimation_id"]
            #     }
            # )
            process_result_res = requests.post(
                f"{BASE_URL_PROCESS_RESULT}/process_result",
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