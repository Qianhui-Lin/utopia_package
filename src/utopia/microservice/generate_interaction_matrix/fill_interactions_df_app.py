# Fuction to genarate the interactions matrix fot the UTOPIA model


import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import pymongo
import os
from bson import ObjectId
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import asynccontextmanager

from utopia.microservice.generate_interaction_matrix.fillInteractions_fun_OOP_json_function import *
from utopia.microservice.generate_interaction_matrix.fillInteractions_fun_OOP_json_dict_function import *

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
# testing locally
# MONGO_URI = "mongodb://utopiauser:utopiapassword@localhost:27018/utopia?authSource=admin"
DB_NAME = os.getenv("DB_NAME", "utopia")
MODEL_COLLECTION = "model_json"
INTERACTION_MATRIX_COLLECTION = "interaction"
RATE_CONSTANT_COLLECTION = "rate_constant"
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
    print("[interaction] ProcessPoolExecutor shut down")


app = FastAPI(lifespan=lifespan, title="Interaction Matrix Generator Service", version="1.0.0")


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
    interaction_matrix_id: Optional[str] = None
    status: str = "interaction matrix generated and saved to mongodb"

class ModelRequest_dict(BaseModel):
    model_id: str
    rate_constant_id: str
    interaction_matrix_id: str

class ModelResponse_dict(BaseModel):
    model_id: str
    interaction_matrix_id: str
    status: str = "interaction matrix_dict generated and saved to mongodb"


class InteractionMatrixBatchRequest(BaseModel):
    items: List[ModelRequest]   # each item needs model_id + rate_constant_id

class InteractionMatrixBatchResponse(BaseModel):
    status: str = "success"
    count: int
    successful: int
    failed: int
    results: List[ModelResponse]


class InteractionMatrixDictBatchRequest(BaseModel):
    items: List[ModelRequest_dict]

class InteractionMatrixDictBatchResponse(BaseModel):
    status: str = "success"
    count: int
    successful: int
    failed: int
    results: List[ModelResponse_dict]


def compute_interaction_matrix_worker(model_json: dict, rate_constant: dict, model_id: str):
    # pure-python version that does not interact with MongoDB
    interaction_matrix = fillInteractions_fun_OOP_json(model_json, rate_constant)
    return interaction_matrix

def compute_interaction_dict_worker(model_json: dict, rate_constant: dict, model_id: str, interaction_matrix_id: str):
    """Compute interaction_matrix_dict in a separate process."""
    interaction_matrix_dict = fillInteractions_fun_OOP_dict_json(model_json, rate_constant)
    return interaction_matrix_dict


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
def generate_interaction_matrix_dict(request: ModelRequest_dict):
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
    

@app.post("/generate_interaction_matrix/batch", response_model=InteractionMatrixBatchResponse)
def generate_interaction_matrix_batch(req: InteractionMatrixBatchRequest):
    """Batch endpoint using the shared solver_executor"""
    
    if solver_executor is None:
        raise HTTPException(status_code=503, detail="ProcessPoolExecutor not initialized")

    # 1. Pre-fetch MongoDB objects (must happen in main process)
    jobs = []
    results: List[ModelResponse] = []
    
    for item in req.items:
        m = model_json_collection.find_one({'_id': ObjectId(item.model_id)})
        r = rate_constant_collection.find_one({'_id': ObjectId(item.rate_constant_id)})
        
        if not m:
            results.append(ModelResponse(
                model_id=item.model_id,
                status="failed: model not found"
            ))
            continue
        if not r:
            results.append(ModelResponse(
                model_id=item.model_id,
                status="failed: rate constant not found"
            ))
            continue

        jobs.append((m, r, item.model_id))

    if jobs:
        # 2. Submit jobs to the shared executor
        futures = {
            solver_executor.submit(compute_interaction_matrix_worker, m, r, model_id): model_id
            for (m, r, model_id) in jobs
        }

        # 3. Gather results
        for future in as_completed(futures):
            model_id = futures[future]
            try:
                interaction_matrix = future.result()

                result = interaction_collection.insert_one({
                    "model_id": model_id,
                    "interaction_df": interaction_matrix
                })

                results.append(ModelResponse(
                    model_id=model_id,
                    interaction_matrix_id=str(result.inserted_id),
                    status="interaction matrix generated and saved to mongodb"
                ))

            except Exception as e:
                results.append(ModelResponse(
                    model_id=model_id,
                    interaction_matrix_id=None,
                    status=f"failed: {e}"
                ))

    successful = sum(1 for r in results if r.interaction_matrix_id is not None)

    return InteractionMatrixBatchResponse(
        status="success" if successful > 0 else "all_failed",
        count=len(results),
        successful=successful,
        failed=len(results) - successful,
        results=results
    )


@app.post("/generate_interaction_matrix_dict/batch", response_model=InteractionMatrixDictBatchResponse)
def generate_interaction_matrix_dict_batch(req: InteractionMatrixDictBatchRequest):
    """Batch endpoint using the shared solver_executor"""
    
    if solver_executor is None:
        raise HTTPException(status_code=503, detail="ProcessPoolExecutor not initialized")

    jobs = []
    results: List[ModelResponse_dict] = []

    # 1. Pre-fetch MongoDB data (must stay in the main process)
    for item in req.items:
        try:
            m_json = model_json_collection.find_one({"_id": ObjectId(item.model_id)})
            rc_json = rate_constant_collection.find_one({"_id": ObjectId(item.rate_constant_id)})

            if not m_json:
                raise ValueError(f"model_json not found for {item.model_id}")
            if not rc_json:
                raise ValueError(f"rate_constant not found for {item.rate_constant_id}")

            jobs.append((m_json, rc_json, item.model_id, item.interaction_matrix_id))

        except Exception as e:
            results.append(
                ModelResponse_dict(
                    model_id=item.model_id,
                    interaction_matrix_id=item.interaction_matrix_id,
                    status=f"failed before multiprocessing: {str(e)}"
                )
            )

    if jobs:
        # 2. Submit jobs to the shared executor
        futures = {
            solver_executor.submit(
                compute_interaction_dict_worker,
                m_json, rc_json, model_id, im_id
            ): (model_id, im_id)
            for (m_json, rc_json, model_id, im_id) in jobs
        }

        # 3. Gather worker results
        for future in as_completed(futures):
            model_id, im_id = futures[future]
            try:
                interaction_dict = future.result()

                # 4. Write back to MongoDB (main process)
                interaction_collection.update_one(
                    {"_id": ObjectId(im_id)},
                    {"$set": {"interaction_dict": interaction_dict}}
                )

                results.append(
                    ModelResponse_dict(
                        model_id=model_id,
                        interaction_matrix_id=im_id,
                        status="interaction matrix_dict generated (parallel)"
                    )
                )

            except Exception as e:
                results.append(
                    ModelResponse_dict(
                        model_id=model_id,
                        interaction_matrix_id=im_id,  # Keep the original im_id even on failure
                        status=f"failed: {e}"
                    )
                )

    successful = sum(1 for r in results if "failed" not in r.status)
    return InteractionMatrixDictBatchResponse(
        status="success" if successful > 0 else "all_failed",
        count=len(results),
        successful=successful,
        failed=len(results) - successful,
        results=results
    )


#sp1.
#sp2.