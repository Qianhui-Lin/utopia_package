import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.colors import LogNorm
import pandas as pd
from utopia.helpers import *
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pymongo
import os
from bson import ObjectId

app = FastAPI(title="Flow Estimator Service", version="1.0.0")

MONGO_URI = "mongodb://utopiauser:utopiapassword@localhost:27018/utopia?authSource=admin"
DB_NAME = os.getenv("DB_NAME", "utopia")
MODEL_COLLECTION = "model_json"
INTERACTION_MATRIX_COLLECTION = "interaction"
RESULT_COLLECTION = "result"
FLOW_COLLECTION = "flow"
RATE_CONSTANT_COLLECTION = "rate_constant"
PARTICLE_STATE_COLLECTION = "particle_state"
FLOW_ESTIMATION_COLLECTION = "flow_estimation"

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

def estimate_flows_json_app(model_id, rate_constant_id, particle_state_id, flow_id):
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
            "tables_outputFlows_mass": tables_outputFlows_mass_dict,
            "tables_outputFlows_number": tables_outputFlows_number_dict,
            "tables_inputFlows_mass": tables_inputFlows_mass_dict,
            "tables_inputFlows_number": tables_inputFlows_number_dict
        }
        
        return flow_estimation_doc


def generate_flows_dict_json(model_json, flow):
        for unit in ["mass", "number"]:
            if unit == "mass":
                tables_inputFlows = flow["tables_inputFlows_mass"]
                tables_outputFlows =flow["tables_outputFlows_mass"]
            elif unit == "number":
                tables_inputFlows = flow["tables_inputFlows_number"]
                tables_outputFlows = flow["tables_outputFlows_number"]
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
                flow["flows_dict_mass"] = flows_dict
            else:
                flow["flows_dict_number"] = flows_dict
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
        flow_doc = estimate_flows_json_app(
            model_id=request.model_id,
            rate_constant_id=request.rate_constant_id,
            particle_state_id=request.particle_state_id,
            flow_id=request.flow_id
        )

        insert_result = flow_estimation_collection.insert_one(flow_doc)

        # Step 3: Return inserted ID
        return ModelResponse(
            flow_estimation_id=str(insert_result.inserted_id)
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
