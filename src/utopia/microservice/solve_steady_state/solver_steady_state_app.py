# This file contains the function that solves the steady state ODEs for the system of particles

from utopia.helpers import mass_to_num, num_to_mass, get_compartment_for_particle_model
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pymongo
import os
from typing import Dict, List, Any, Optional
from bson import ObjectId
# from utopia.preprocessing.RC_generator_json import get_compartment_for_particle
from concurrent.futures import ProcessPoolExecutor

app = FastAPI(title="Steady State Solver Service", version="1.0.0")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
# testing locally
#MONGO_URI = "mongodb://utopiauser:utopiapassword@localhost:27018/utopia?authSource=admin"
DB_NAME = os.getenv("DB_NAME", "utopia")
MODEL_COLLECTION = "model_json"
INTERACTION_MATRIX_COLLECTION = "interaction"
RESULT_COLLECTION = "result"
FLOW_COLLECTION = "flow"
RATE_CONSTANT_COLLECTION = "rate_constant"
PARTICLE_STATE_COLLECTION = "particle_state"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
model_json_collection = db[MODEL_COLLECTION]
interaction_collection = db[INTERACTION_MATRIX_COLLECTION]
result_collection = db[RESULT_COLLECTION]
flow_collection = db[FLOW_COLLECTION]
rate_constant_collection = db[RATE_CONSTANT_COLLECTION]
particle_state_collection = db[PARTICLE_STATE_COLLECTION]

class ModelRequest(BaseModel):
    model_id: str
    interaction_matrix_id: str

class ModelResponse(BaseModel):
    model_id: str
    result_id :str
    flow_id: str
    particle_state_id: str
    status: str = "result, flow, and particle states generated and saved to mongodb"


class BatchModelRequest(BaseModel):
    items: List[ModelRequest]

class SingleResult(BaseModel):
    model_id: str
    result_id: str | None = None
    flow_id: str | None = None
    particle_state_id: str | None = None
    status: str

class BatchModelResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[SingleResult]

def init_worker():
    """Initialize MongoDB connection for this worker process"""
    global worker_db
    client = pymongo.MongoClient(MONGO_URI)
    worker_db = client[DB_NAME]

def solver_SS_json_app(model_json,interaction_documentation):

    # read the emissions dictionary to generate the list of emissions for the ODES (input_flows_g_s)
    sp_imputs = []
    q_mass_g_s = []
    for compartment in model_json["emiss_dict_g_s"].keys():
        for size_bin in model_json["emiss_dict_g_s"][compartment].keys():

            sp_imputs.append(
                size_bin
                + model_json["particle_forms_coding"][model_json["MP_form"]]
                + str(model_json["particle_compartmentCoding"][compartment])
                + "_"
                + model_json["boxName"]
            )
            q_mass_g_s.append(model_json["emiss_dict_g_s"][compartment][size_bin])

    input_flows_g_s = dict(zip(sp_imputs, q_mass_g_s))

    q_num_s = [
        mass_to_num(v, p["Pvolume_m3"], p["Pdensity_kg_m3"]) if v != 0 else 0
        for k, v in zip(input_flows_g_s.keys(), input_flows_g_s.values())
        for p in model_json["system_particle_object_list"]
        if k == p["Pcode"]
    ]

    input_flows_num_s = dict(zip(sp_imputs, q_num_s))

    R, PartMass_t0,system_particle_object_list_updated = solve_ODES_SS_app(
        system_particle_object_list=model_json["system_particle_object_list"],
        q_num_s=0,
        input_flows_g_s=input_flows_g_s,
        interactions_df=interaction_documentation["interaction_df"],
        model_json = model_json,
    )
    return R, PartMass_t0, input_flows_g_s, input_flows_num_s, system_particle_object_list_updated


def solve_ODES_SS_app(
    system_particle_object_list, q_num_s, input_flows_g_s, interactions_df,model_json
):
    SpeciesList = [p["Pcode"] for p in system_particle_object_list]
    if isinstance(interactions_df, dict):
        interactions_df = pd.DataFrame(interactions_df)

    # Set initial mass of particles to 0
    # Set SS mass of particles to =???
    if sum(input_flows_g_s.values()) != 0:
        # set mass of particles for all particles in the system as zero
        m_t0 = []
        for p in system_particle_object_list:
            p["Pmass_g_t0"] = 0
            m_t0.append(p["Pmass_g_t0"])

        # dataframe of mass of particles at time 0
        PartMass_t0 = pd.DataFrame({"species": SpeciesList, "mass_g": m_t0})
        PartMass_t0 = PartMass_t0.set_index("species")

        # Set emissions
        for sp_imput in input_flows_g_s.keys():
            PartMass_t0.at[sp_imput, "mass_g"] = -input_flows_g_s[sp_imput]

        # Input vector
        inputVector = PartMass_t0["mass_g"].to_list()

        matrix = interactions_df.to_numpy()

        SteadyStateResults = np.linalg.solve(matrix, inputVector)

        Results = pd.DataFrame({"species": SpeciesList, "mass_g": SteadyStateResults})

        R = Results.set_index("species")
        for p in system_particle_object_list:
            p["Pmass_g_SS"] = R.loc[p["Pcode"]]["mass_g"]
        # Convert results in mass to particle number and add to the particle objects
        for p in system_particle_object_list:
            if "SPM" in p["Pname"]:
                if "BF" in p["Pname"]:
                    p["Pnum_SS"] = mass_to_num(
                        mass_g=p["Pmass_g_SS"],
                        volume_m3=p["parentMP"]["parentMP"]["Pvolume_m3"],
                        density_kg_m3=p["parentMP"]["parentMP"]["Pdensity_kg_m3"],
                    )
                else:
                    p["Pnum_SS"] = mass_to_num(
                        mass_g=p["Pmass_g_SS"],
                        volume_m3=p["parentMP"]["Pvolume_m3"],
                        density_kg_m3=p["parentMP"]["Pdensity_kg_m3"],
                    )
            else:
                p["Pnum_SS"] = mass_to_num(
                    mass_g=p["Pmass_g_SS"],
                    volume_m3=p["Pvolume_m3"],
                    density_kg_m3=p["Pdensity_kg_m3"],
                )

        # Add to Results dataframe
        for p in system_particle_object_list:
            R.loc[p["Pcode"], "number_of_particles"] = p["Pnum_SS"]
        ### Estimate SS concentration and add to particles
        for p in system_particle_object_list:
            comp = get_compartment_for_particle_model(p, model_json)
            Pcompartment_Cvolume_m3 = comp["Cvolume_m3"]
            p["C_g_m3_SS"] = p["Pmass_g_SS"] / float(Pcompartment_Cvolume_m3)
            R.loc[p["Pcode"], "concentration_g_m3"] = p["C_g_m3_SS"]
            p["C_num_m3_SS"] = p["Pnum_SS"] / float(Pcompartment_Cvolume_m3)
            R.loc[p["Pcode"], "concentration_num_m3"] = p["C_num_m3_SS"]

    elif (
        q_num_s != 0
    ):  # By default the inputs are always given in mass this piece of code only needed if inputs given in particle numbers but this is has to be included in the imputs sections and updated to reflect the same structure as the mass inputs (list of inputs and not a single value)
        # Set number of particles for all particles in the system as zero
        N_t0 = []
        for p in system_particle_object_list:
            p["Pnumber"] = 0
            N_t0.append(p["Pnumber"])

        # dataframe of number of particles at time 0
        PartNum_t0 = pd.DataFrame({"species": SpeciesList, "number_of_particles": N_t0})
        PartNum_t0 = PartNum_t0.set_index("species")

        # Set emissions
        PartNum_t0.at[sp_imput, "number_of_particles"] = -q_num_s

        # Input vector
        inputVector = PartNum_t0["number_of_particles"].to_list()
        matrix = interactions_df.to_numpy()

        SteadyStateResults = np.linalg.solve(matrix, inputVector)

        Results = pd.DataFrame(
            {"species": SpeciesList, "number_of_particles": SteadyStateResults}
        )

        # Assign steady state (SS) results to paticles in particle number

        R = Results.set_index("species")
        for p in system_particle_object_list:
            p["Pnum_SS"] = R.loc[p["Pcode"]]["number_of_particles"]

        # Convert results in particle number to mass and add to the particle objects
        for p in system_particle_object_list:
            if "SPM" in p["Pname"]:
                if "BF" in p["Pname"]:
                    p["Pmass_g_SS"] = num_to_mass(
                        number=p["Pnum_SS"],
                        volume_m3=p["parentMP"]["parentMP"]["Pvolume_m3"],
                        density_kg_m3=p["parentMP"]["parentMP"]["Pdensity_kg_m3"],
                    )
                else:
                    p["Pmass_g_SS"] = num_to_mass(
                        number=p["Pnum_SS"],
                        volume_m3=p["parentMP"]["Pvolume_m3"],
                        density_kg_m3=p["parentMP"]["Pdensity_kg_m3"],
                    )
            else:
                p["Pmass_g_SS"] = num_to_mass(
                    number=p["Pnum_SS"],
                    volume_m3=p["Pvolume_m3"],
                    density_kg_m3=p["Pdensity_kg_m3"],
                )

        # Add to Results dataframe
        for p in system_particle_object_list:
            R.loc[p["Pcode"], "mass_g"] = p["Pmass_g_SS"]

        ### Estimate SS concentration and add to particles
        for p in system_particle_object_list:
            comp = get_compartment_for_particle_model(p, model_json)
            Pcompartment_Cvolume_m3 = comp["Cvolume_m3"]
            p["C_g_m3_SS"] = p["Pmass_g_SS"] / float(Pcompartment_Cvolume_m3)
            R.loc[p["Pcode"], "concentration_g_m3"] = p["C_g_m3_SS"]
            p["C_num_m3_SS"] = p["Pnum_SS"] / float(Pcompartment_Cvolume_m3)
            R.loc[p["Pcode"], "concentration_num_m3"] = p["C_num_m3_SS"]

    else:
        print("ERROR: No particles have been input to the system")

    return R, PartMass_t0, system_particle_object_list

def run_single_model(model_id: str, interaction_id: str) -> SingleResult:
    try:
        model_json = worker_db["model_json"].find_one({'_id': ObjectId(model_id)})
        if model_json is None:
            return SingleResult(
                model_id=model_id,
                status=f"failed: model_id {model_id} not found"
            )

        interaction_documentation = worker_db["interaction"].find_one({'_id': ObjectId(interaction_id)})
        if interaction_documentation is None:
            return SingleResult(
                model_id=model_id,
                status=f"failed: interaction_matrix_id {interaction_id} not found"
            )

        (R, PartMass_t0, input_flows_g_s, input_flows_num_s,
         system_particle_object_list_updated) = solver_SS_json_app(model_json, interaction_documentation)

        # Negative value warning (unchanged from your logic)
        for i, idx in zip(R["mass_g"], R.index):
            if i < 0:
                print("negative values in the solution for " + idx)

        # Build particle state list
        system_particle_state_list = []
        for p in system_particle_object_list_updated:
            system_particle_state_list.append({
                'Pcode': p['Pcode'],
                'Pmass_g_t0': p['Pmass_g_t0'],
                'Pmass_g_SS': p['Pmass_g_SS'],
                'Pnum_SS': p['Pnum_SS'],
                'C_g_m3_SS': p['C_g_m3_SS'],
                'C_num_m3_SS': p['C_num_m3_SS']
            })

        particle_state_doc = {
            'model_id': model_id,
            'interaction_matrix_id': interaction_id,
            'system_particle_state_list': system_particle_state_list,
        }
        particle_state_insert = worker_db["particle_state"].insert_one(particle_state_doc)

        # Save result
        result_insert = worker_db["result"].insert_one({
            'model_id': model_id,
            'result': R.to_dict('list'),
            'index': list(R.index)
        })

        flow_insert = worker_db['flow'].insert_one({
            'model_id': model_id,
            'input_flows_g_s': input_flows_g_s,
            'input_flows_num_s': input_flows_num_s
        })

        return SingleResult(
            model_id=model_id,
            result_id=str(result_insert.inserted_id),
            flow_id=str(flow_insert.inserted_id),
            particle_state_id=str(particle_state_insert.inserted_id),
            status="success"
        )

    except Exception as e:
        return SingleResult(
            model_id=model_id,
            status=f"failed: {str(e)}"
        )

def solve_single_model_task(args):
    model_id, interaction_id = args
    return run_single_model(model_id, interaction_id)



@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Steady State Solver Service is running", "status": "healthy"}

@app.post("/init_result_collection")
def init_result_collection():
    try:
        result = result_collection.delete_many({})
        return {
            "status": "success",
            "message": f"All {result.deleted_count} result records have been deleted."
        }
    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/init_flow_collection")
def init_flow_collection():
    try:
        result = flow_collection.delete_many({})
        return {
            "status": "success",
            "message": f"All {result.deleted_count} flow records have been deleted."
        }
    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@app.post("/init_particle_state_collection")
def init_particle_state_collection():
    try:
        result = particle_state_collection.delete_many({})
        return {
            "status": "success",
            "message": f"All {result.deleted_count} particle state records have been deleted."
        }
    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/solve_steady_state",response_model = ModelResponse)
def solve_steady_state(request: ModelRequest):
    try:
        model_json = model_json_collection.find_one({'_id': ObjectId(request.model_id)}) 
        interaction_documentation = interaction_collection.find_one({'_id':ObjectId(request.interaction_matrix_id)})
        (R, PartMass_t0, input_flows_g_s, input_flows_num_s,system_particle_object_list_updated) = solver_SS_json_app(model_json,interaction_documentation)
        for i, idx in zip(R["mass_g"], R.index):
            if i < 0:
                print("negative values in the solution for " + idx)
            else:
                pass

        system_particle_state_list = []
        for p in system_particle_object_list_updated:
            particle_state = {
                'Pcode': p['Pcode'],
                'Pmass_g_t0': p['Pmass_g_t0'],
                'Pmass_g_SS': p['Pmass_g_SS'],
                'Pnum_SS': p['Pnum_SS'],
                'C_g_m3_SS': p['C_g_m3_SS'],
                'C_num_m3_SS': p['C_num_m3_SS']
            }
            system_particle_state_list.append(particle_state)

        particle_state_doc = {
            'model_id': request.model_id,
            'interaction_matrix_id': request.interaction_matrix_id,
            'system_particle_state_list': system_particle_state_list,
            
        }

        particle_state_insert = particle_state_collection.insert_one(particle_state_doc)

        result_insert = result_collection.insert_one({
            'model_id': request.model_id,
            'result': R.to_dict('list'),
            'index': list(R.index)}
        )
        
        flow_doc = {
            'model_id': request.model_id,
            'input_flows_g_s': input_flows_g_s,
            'input_flows_num_s': input_flows_num_s
        }

        flow_insert = flow_collection.insert_one(flow_doc)
        return ModelResponse(
            model_id = request.model_id,
            result_id = str(result_insert.inserted_id),
            flow_id = str(flow_insert.inserted_id),
            particle_state_id=str(particle_state_insert.inserted_id)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        

@app.post("/solve_steady_state/batch", response_model=BatchModelResponse)
def solve_steady_state_batch_parallel(req: BatchModelRequest):

    tasks = [(item.model_id, item.interaction_matrix_id) for item in req.items]

    results = []
    # Use all available CPU cores
    with ProcessPoolExecutor(max_workers=8,initializer=init_worker) as executor:
        for result in executor.map(solve_single_model_task, tasks):
            results.append(result)

    successful = sum(1 for r in results if r.status == "success")
    failed = len(results) - successful

    return BatchModelResponse(
        total=len(results),
        successful=successful,
        failed=failed,
        results=results
    )