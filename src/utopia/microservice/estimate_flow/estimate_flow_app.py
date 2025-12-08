import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.colors import LogNorm
import pandas as pd
from utopia.helpers import *
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import pymongo
import os
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from bson import ObjectId

worker_db = None
solver_executor: ProcessPoolExecutor | None = None

def init_worker():
    """
    Called once when each worker process starts.
    Creates a MongoDB connection for that process.
    """
    global worker_db
    
    worker_client = pymongo.MongoClient(MONGO_URI)
    worker_db = worker_client[DB_NAME]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global solver_executor
    
    # Startup: create process pool with initialized workers
    solver_executor = ProcessPoolExecutor(
        max_workers=MAX_WORKERS,
        initializer=init_worker
    )
    print(f"Started ProcessPoolExecutor with {MAX_WORKERS} workers")
    
    yield
    
    # Shutdown: clean up
    solver_executor.shutdown(wait=True)
    print("ProcessPoolExecutor shut down")


app = FastAPI(lifespan=lifespan,title="Flow Estimator Service", version="1.0.0")

#MONGO_URI = "mongodb://utopiauser:utopiapassword@localhost:27018/utopia?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/") 

DB_NAME = os.getenv("DB_NAME", "utopia")
MODEL_COLLECTION = "model_json"
INTERACTION_MATRIX_COLLECTION = "interaction"
RESULT_COLLECTION = "result"
FLOW_COLLECTION = "flow"
RATE_CONSTANT_COLLECTION = "rate_constant"
PARTICLE_STATE_COLLECTION = "particle_state"
FLOW_ESTIMATION_COLLECTION = "flow_estimation"
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
model_json_collection = db[MODEL_COLLECTION]
interaction_collection = db[INTERACTION_MATRIX_COLLECTION]
result_collection = db[RESULT_COLLECTION]
flow_collection = db[FLOW_COLLECTION]
rate_constant_collection = db[RATE_CONSTANT_COLLECTION]
particle_state_collection = db[PARTICLE_STATE_COLLECTION]
flow_estimation_collection = db[FLOW_ESTIMATION_COLLECTION]

class ModelRequest(BaseModel):
    model_id: str
    rate_constant_id: str
    particle_state_id: str
    flow_id: str

class ModelResponse(BaseModel):
    flow_estimation_id: str
    status: str = "updated flow estimation"

class BatchFlowRequest(BaseModel):
    items: List[ModelRequest]

class SingleFlowResult(BaseModel):
    model_id: str
    flow_estimation_id: str | None = None
    status: str

class BatchFlowResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[SingleFlowResult]

def run_flow_estimation_in_process(
    model_id: str,
    rate_constant_id: str, 
    particle_state_id: str,
    flow_id: str
) -> SingleFlowResult:
    """Runs in worker process with its own MongoDB connection"""
    try:
        model_json = worker_db.model_json.find_one({'_id': ObjectId(model_id)})
        if model_json is None:
            return SingleFlowResult(model_id=model_id, status="failed: model not found")

        rate_constant_doc = worker_db.rate_constant.find_one({'_id': ObjectId(rate_constant_id)})
        if rate_constant_doc is None:
            return SingleFlowResult(model_id=model_id, status="failed: rate_constant not found")

        particle_state_doc = worker_db.particle_state.find_one({'_id': ObjectId(particle_state_id)})
        if particle_state_doc is None:
            return SingleFlowResult(model_id=model_id, status="failed: particle_state not found")

        # Pure computation
        flow_estimation_doc = estimate_flows_compute_json(
            model_json=model_json,
            rate_constant_doc=rate_constant_doc,
            particle_state_doc=particle_state_doc,
            flow_id=flow_id,
            model_id=model_id,
            rate_constant_id=rate_constant_id,
            particle_state_id=particle_state_id
        )

        flow_estimation_doc_updated = generate_flows_dict_json(model_json, flow_estimation_doc)
        flow_estimation_doc_to_insert = convert_dfs_in_flow(flow_estimation_doc_updated)

        insert_result = worker_db.flow_estimation.insert_one(flow_estimation_doc_to_insert)

        return SingleFlowResult(
            model_id=model_id,
            flow_estimation_id=str(insert_result.inserted_id),
            status="success"
        )

    except Exception as e:
        return SingleFlowResult(model_id=model_id, status=f"failed: {str(e)}")

def flow_task(args):
    return run_flow_estimation_in_process(*args)

def estimate_flows_compute_json(model_json: dict, rate_constant_doc: dict, particle_state_doc: dict,flow_id: str, model_id: str,rate_constant_id: str,particle_state_id: str)-> dict:       
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

        #model_json["surfComp_list"] = [c for c in model_json["dict_comp"] if "Surface" in c]
        surfComp_list = [c for c in model_json["dict_comp"] if "Surface" in c]

        # Initialize system_particle_outflow_list for the output
        system_particle_outflow_list = []

        """Estimate flows corresponding to each mode process based on the model results."""
        # Outflows ( in mass and particle number)
        for p in system_particle_object_list: 
            Pcode = p["Pcode"]
            outFlow_mass_g_s = {}
            outFlow_number_g_s = {}
            # Get particle state values
            pmass_ss = p["Pmass_g_SS"]
            pnum_ss = p["Pnum_SS"]
            for c in p["RateConstants"]:
                rate_constant = p["RateConstants"][c]
                #if type(p["RateConstants"][c]) == list:
                if isinstance(rate_constant, list):
                    outFlow_mass_g_s[c] = [
                        R * pmass_ss for R in rate_constant
                    ]
                    outFlow_number_g_s[c] = [
                        R * pnum_ss for R in rate_constant
                    ]
                else:
                    outFlow_mass_g_s[c] = rate_constant * pmass_ss
                    outFlow_number_g_s[c] = rate_constant * pnum_ss
            # Add to outflow list
            system_particle_outflow_list.append({
                "Pcode": Pcode,
                "outFlow_mass_g_s": outFlow_mass_g_s,
                "outFlow_number_g_s": outFlow_number_g_s
            })

            # Also keep in the particle object for DataFrame creation
            p["outFlow_mass_g_s"] = outFlow_mass_g_s
            p["outFlow_number_g_s"] = outFlow_number_g_s

        # Tables of output flows per compartmet
        tables_outputFlows_mass = {}
        tables_outputFlows_number = {}
        for c in list(model_json["dict_comp"].keys()):
            part_dic_mass = {}
            part_dic_number = {}
            for p in system_particle_object_list:
                if p["Pcompartment_Cname"] == c:
                    part_dic_mass[p["Pcode"]] = pd.DataFrame.from_dict(
                        p["outFlow_mass_g_s"], orient="index"
                    )
                    part_dic_number[p["Pcode"]] = pd.DataFrame.from_dict(
                        p["outFlow_number_g_s"], orient="index"
                    )
            tables_outputFlows_mass[c] = pd.concat(part_dic_mass, axis=1).transpose()
            tables_outputFlows_number[c] = pd.concat(
                part_dic_number, axis=1
            ).transpose()

        for k in tables_outputFlows_mass:
            tables_outputFlows_mass[k] = (
                tables_outputFlows_mass[k].reset_index(level=1).drop("level_1", axis=1)
            )
            tables_outputFlows_number[k] = (
                tables_outputFlows_number[k]
                .reset_index(level=1)
                .drop("level_1", axis=1)
            )
        # flow data collection 用于存放 各种input flows 和 output flows
        #flow["tables_outputFlows_mass"] = tables_outputFlows_mass
        #flow["tables_outputFlows_number"] = tables_outputFlows_number

        # Inflows: Tables of recieving flows through transport from other compartments
        tables_inputFlows_mass = {}
        tables_inputFlows_number = {}
        for comp in list(model_json["dict_comp"].keys()):
            comp_input_flows_mass = []
            comp_input_flows_num = []
            for e_comp in model_json["dict_comp"]:
                if comp in model_json["dict_comp"][e_comp]["connexions"]:
                    inpProc = model_json["dict_comp"][e_comp]["connexions"][comp]
                    if (
                        type(inpProc) == list
                    ):  # When there is more than one process of inflow into the compartment
                        df_inflows = tables_outputFlows_mass[e_comp].loc[
                            :, ["k_" + ele for ele in inpProc]
                        ]
                        df_inflows_num = tables_outputFlows_number[e_comp].loc[
                            :, ["k_" + ele for ele in inpProc]
                        ]

                        for proc in inpProc:
                            if proc == "dry_deposition" or proc == "wet_deposition":
                                position = surfComp_list.index(comp)
                                df_inflows["k_" + proc] = df_inflows["k_" + proc].apply(
                                    lambda x: x[position] if isinstance(x, list) else x
                                )
                                df_inflows_num["k_" + proc] = df_inflows_num[
                                    "k_" + proc
                                ].apply(
                                    lambda x: x[position] if isinstance(x, list) else x
                                )

                            elif proc == "mixing":

                                if (
                                    e_comp == "Ocean_Mixed_Water"
                                    and comp == "Ocean_Surface_Water"
                                ):
                                    df_inflows["k_" + proc] = df_inflows[
                                        "k_" + proc
                                    ].apply(
                                        lambda x: x[0] if isinstance(x, list) else x
                                    )
                                    df_inflows_num["k_" + proc] = df_inflows_num[
                                        "k_" + proc
                                    ].apply(
                                        lambda x: x[0] if isinstance(x, list) else x
                                    )

                                elif (
                                    e_comp == "Ocean_Mixed_Water"
                                    and comp == "Ocean_Column_Water"
                                ):
                                    df_inflows["k_" + proc] = df_inflows[
                                        "k_" + proc
                                    ].apply(
                                        lambda x: x[1] if isinstance(x, list) else x
                                    )
                                    df_inflows_num["k_" + proc] = df_inflows_num[
                                        "k_" + proc
                                    ].apply(
                                        lambda x: x[1] if isinstance(x, list) else x
                                    )
                                else:
                                    pass
                                # Revisit for percollation and tillage
                            else:
                                pass
                        comp_input_flows_mass.append(df_inflows)
                        comp_input_flows_num.append(df_inflows_num)

                    else:
                        df_inflows = (
                            tables_outputFlows_mass[e_comp]
                            .loc[:, "k_" + inpProc]
                            .to_frame()
                        )
                        df_inflows_num = (
                            tables_outputFlows_number[e_comp]
                            .loc[:, "k_" + inpProc]
                            .to_frame()
                        )
                        for ele in df_inflows["k_" + inpProc]:
                            if type(ele) == list:
                                connecting_comp = {
                                    key: value
                                    for key, value in model_json["dict_comp"][
                                        e_comp
                                    ]["connexions"].items()
                                    if value == inpProc
                                }
                                poss_dict = {
                                    key: index
                                    for index, key in enumerate(connecting_comp.keys())
                                }
                                possition = poss_dict[comp]
                                df_inflows["k_" + inpProc] = df_inflows[
                                    "k_" + inpProc
                                ].apply(
                                    lambda x: x[possition] if isinstance(x, list) else x
                                )
                                df_inflows_num["k_" + inpProc] = df_inflows_num[
                                    "k_" + inpProc
                                ].apply(
                                    lambda x: x[possition] if isinstance(x, list) else x
                                )

                            else:
                                pass
                        comp_input_flows_mass.append(df_inflows)
                        comp_input_flows_num.append(df_inflows_num)
                else:
                    pass

            tables_inputFlows_mass[comp] = pd.concat(comp_input_flows_mass).fillna(0)
            tables_inputFlows_number[comp] = pd.concat(comp_input_flows_num).fillna(0)

    # Convert DataFrames to dictionaries for MongoDB storage
        tables_outputFlows_mass_dict = {
            k: v.to_dict() if not v.empty else {} 
            for k, v in tables_outputFlows_mass.items()
        }
        tables_outputFlows_number_dict = {
            k: v.to_dict() if not v.empty else {} 
            for k, v in tables_outputFlows_number.items()
        }
        tables_inputFlows_mass_dict = {
            k: v.to_dict() if not v.empty else {} 
            for k, v in tables_inputFlows_mass.items()
        }
        tables_inputFlows_number_dict = {
            k: v.to_dict() if not v.empty else {} 
            for k, v in tables_inputFlows_number.items()
        }
        
        # Prepare the document for flow_estimation collection
        flow_estimation_doc = {
            "flow_id": str(flow_id), 
            "rate_constant_id": str(rate_constant_id),
            "particle_state_id": str(particle_state_id),
            "model_id": str(model_id),
            "system_particle_outflow_list": system_particle_outflow_list,
            "tables_outputFlows_mass": tables_outputFlows_mass,
            "tables_outputFlows_number": tables_outputFlows_number,
            "tables_inputFlows_mass": tables_inputFlows_mass,
            "tables_inputFlows_number": tables_inputFlows_number
        }
        
        return flow_estimation_doc


def generate_flows_dict_json(model_json, flow_estimation):
        for unit in ["mass", "number"]:
            if unit == "mass":
                tables_inputFlows = flow_estimation["tables_inputFlows_mass"]
                tables_outputFlows =flow_estimation["tables_outputFlows_mass"]
            elif unit == "number":
                tables_inputFlows = flow_estimation["tables_inputFlows_number"]
                tables_outputFlows = flow_estimation["tables_outputFlows_number"]
            else:
                raise ValueError("Unit must be 'mass' or 'number'.")
            flows_dict = dict()
            flows_dict["input_flows"] = {}
            flows_dict["output_flows"] = {}

            # Decode index in input and output flow tables
            for comp in tables_outputFlows.keys():
                df1 = tables_outputFlows[comp].copy()
                MP_size_df1 = []
                MP_form_df1 = []
                for x in df1.index:
                    MP_size_df1.append(model_json["size_dict"][x[0]])
                    MP_form_df1.append(model_json["MP_form_dict_reverse"][x[1:2]])

                df1.insert(0, "MP_size", MP_size_df1)
                df1.insert(1, "MP_form", MP_form_df1)
                flows_dict["output_flows"][comp] = df1

            for comp in tables_inputFlows:
                df2 = tables_inputFlows[comp].copy()
                MP_size_df2 = []
                MP_form_df2 = []
                for y in df2.index:
                    MP_size_df2.append(model_json["size_dict"][y[0]])
                    MP_form_df2.append(model_json["MP_form_dict_reverse"][y[1:2]])
                df2.insert(0, "MP_size", MP_size_df2)
                df2.insert(1, "MP_form", MP_form_df2)
                flows_dict["input_flows"][comp] = df2
            if unit == "mass":
                flow_estimation["flows_dict_mass"] = flows_dict
            else:
                flow_estimation["flows_dict_number"] = flows_dict
        return flow_estimation

def convert_dfs_in_flow(flow_estimation_to_convert):
    flow = flow_estimation_to_convert #保留了原来的
    # Keys with dicts of DataFrames
    keys_with_dfs = [
        "tables_outputFlows_mass",
        "tables_outputFlows_number",
        "tables_inputFlows_mass",
        "tables_inputFlows_number"
    ]
    for key in keys_with_dfs:
        if key in flow and isinstance(flow[key], dict):
            for subkey, value in flow[key].items():
                if isinstance(value, pd.DataFrame):
                    flow[key][subkey] = value.reset_index().to_dict(orient='records')
                    
                    
    # Check flows_dict_mass and flows_dict_number if they exist
    for main_key in ["flows_dict_mass", "flows_dict_number"]:
        if main_key in flow and isinstance(flow[main_key], dict):
            for direction in ["input_flows", "output_flows"]:
                if direction in flow[main_key] and isinstance(flow[main_key][direction], dict):
                    for comp, value in flow[main_key][direction].items():
                        if isinstance(value, pd.DataFrame):
                            flow[main_key][direction][comp] = value.reset_index().to_dict(orient='records')
    return flow


@app.post("/init_flow_estimation_collection")
def init_flow_estimation_collection():
    try:
        result = flow_estimation_collection.delete_many({})
        return {
            "status": "success",
            "message": f"All {result.deleted_count} particle state records have been deleted."
        }
    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

@app.post("/estimate_flow",response_model = ModelResponse)
def flow_estimation(request: ModelRequest):
    try:
        model_json = model_json_collection.find_one({'_id': ObjectId(request.model_id)})
        if model_json is None:
            raise HTTPException(status_code=404, detail=f"model_id {request.model_id} not found")

        rate_constant_doc = rate_constant_collection.find_one({'_id': ObjectId(request.rate_constant_id)})
        if rate_constant_doc is None:
            raise HTTPException(status_code=404, detail=f"rate_constant_id not found")

        particle_state_doc = particle_state_collection.find_one({'_id': ObjectId(request.particle_state_id)})
        if particle_state_doc is None:
            raise HTTPException(status_code=404, detail=f"particle_state_id not found")
                
        flow_estimation_doc = estimate_flows_compute_json(
            model_json=model_json,
            rate_constant_doc=rate_constant_doc,
            particle_state_doc=particle_state_doc,
            flow_id=request.flow_id,
            model_id=request.model_id,
            rate_constant_id=request.rate_constant_id,
            particle_state_id=request.particle_state_id
        )

        flow_estimation_doc_updated = generate_flows_dict_json(model_json,flow_estimation_doc)
        flow_estimation_doc_to_insert = convert_dfs_in_flow(flow_estimation_doc_updated)
        insert_result = flow_estimation_collection.insert_one(flow_estimation_doc_to_insert)

        # Step 3: Return inserted ID
        return ModelResponse(
            flow_estimation_id=str(insert_result.inserted_id)
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@app.post("/estimate_flow/batch", response_model=BatchFlowResponse)
def flow_estimation_batch(req: BatchFlowRequest):
    """Batch request - distributes to worker processes"""
    tasks = [
        (item.model_id, item.rate_constant_id, item.particle_state_id, item.flow_id)
        for item in req.items
    ]

    results = list(solver_executor.map(flow_task, tasks))

    successful = sum(1 for r in results if r.status == "success")

    return BatchFlowResponse(
        total=len(results),
        successful=successful,
        failed=len(results) - successful,
        results=results
    )