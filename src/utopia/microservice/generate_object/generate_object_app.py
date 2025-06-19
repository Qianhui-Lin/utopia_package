import pymongo
import math
import pandas as pd
import string
import os
import sys
from pathlib import Path

def mongo_connect():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client['utopia']
    config_collection = db['configure_data']
    input_collection = db['input_data']

    config_doc = config_collection.find_one()
    config_doc_id = config_doc['_id']
    input_doc = input_collection.find_one()
    input_doc_id = input_doc['_id']
    return client, db, config_collection, input_collection, config_doc, input_doc, config_doc_id, input_doc_id

def initialize_mongo_collections():
    client, db, config_collection, input_collection, _, _, _, _ = mongo_connect()
    config_collection.delete_many({})
    input_collection.delete_many({})

def load_csv_column(filename, column_name):
    """Load a column from input CSV file: Reads a single column from a CSV file and returns it as a list"""
    # The data folder is two levels up from this script's directory
    base_path = Path(__file__).resolve().parent.parent.parent / "data"
    file_path = base_path / filename
    df = pd.read_csv(file_path, usecols=[column_name])
    return df[column_name].tolist()

def add_derived_parameters():
    client, db, config_collection, input_collection, config_doc, input_doc, config_doc_id, input_doc_id = mongo_connect()

    vol_algal_cell_m3 = config_doc['vol_algal_cell_m3']
    radius_algae_m = ((3.0 / 4.0) * (vol_algal_cell_m3 / math.pi)) ** (1.0 / 3.0)
    spm_radius_um = radius_algae_m * 1e6
    compartments_list = load_csv_column(
            config_doc["comp_input_file_name"], "Cname"
        )
    base_path = Path(__file__).resolve().parent.parent.parent / "data"
    update_config = config_collection.update_one(
        {'_id': config_doc_id},
        {'$set': {
            'radius_algae_m': radius_algae_m,
            'spm_radius_um': spm_radius_um,
            'compartments_list': compartments_list,
            'base_path': str(base_path)
        }}
    )

def generate_particles_dataframe():
        client, db, config_collection, input_collection, config_doc, input_doc, config_doc_id, input_doc_id = mongo_connect()

        """Generates the microplastics input DataFrame from Utopia model attributes."""
        MPdensity_kg_m3 = input_doc['MPdensity_kg_m3']
        shape = input_doc['shape']
        N_sizeBins = config_doc['N_sizeBins']
        big_bin_diameter_um = config_doc['big_bin_diameter_um']
        MP_composition = input_doc['MP_composition']
        

        # Generate size distribution
        size_distribution = [big_bin_diameter_um]
        for _ in range(N_sizeBins - 1):
            size_distribution.append(size_distribution[-1] / 10)
        size_distribution.reverse()

        # Only supports spherical particles for now
        if shape == "sphere":
            data = {
                "Name": [f"mp{i+1}" for i in range(N_sizeBins)],
                "form": ["freeMP"] * N_sizeBins,
                "shape": [shape] * N_sizeBins,
                "composition": [MP_composition] * N_sizeBins,
                "density_kg_m3": [MPdensity_kg_m3] * N_sizeBins,
                "dimensionX_um": [d / 2 for d in size_distribution],
                "dimensionY_um": [d / 2 for d in size_distribution],
                "dimensionZ_um": [d / 2 for d in size_distribution],
            }
            particles_df = pd.DataFrame(data)

        return particles_df
        '''
            update_input = input_collection.update_one(
                {'_id': input_doc_id},
                {'$set': {
                    'particles_df': particles_df.to_dict(orient='records')
                }}
            )
        '''
          
def generate_coding_dictionaries():
    client, db, config_collection, input_collection, config_doc, input_doc, config_doc_id, input_doc_id = mongo_connect()
    """Generates Mp form, size and compartment coding dictionaries as attributes."""
    if input_doc["particles_df"] is None:
        raise ValueError("Particles DataFrame has not been generated.")
    particles_df = pd.DataFrame(input_doc["particles_df"])
    # Dictionary mapping particle names to sizes
    dict_size_coding = dict(
        zip(particles_df["Name"], particles_df["dimensionX_um"] * 2)
        )

    # Generate size codes (a-z based on number of bins)
    size_codes = list(string.ascii_lowercase[: config_doc["N_sizeBins"]])

    # Dictionary mapping size codes to sizes
    size_dict = dict(zip(size_codes, dict_size_coding.values()))

    # Dictionary mapping MP form codes to MP forms
    particle_forms_coding = dict(zip(config_doc["MPforms_list"], ["A", "B", "C", "D"]))
    MP_form_dict_reverse = {
            v: k for k, v in particle_forms_coding.items()
        }

    # Dictionary mapping compartment names to compartment codes
    particle_compartmentCoding = dict(
        zip(
                config_doc["compartments_list"],
                list(range(len(config_doc["compartments_list"]))),
            )
        )
    comp_dict_inverse = {
            str(v): k for k, v in particle_compartmentCoding.items()
        }
    
    update_config = config_collection.update_one(
        {'_id': config_doc_id},
        {'$set': {
            'dict_size_coding': dict_size_coding,
            'size_dict': size_dict,
            'particle_forms_coding': particle_forms_coding,
            'MP_form_dict_reverse': MP_form_dict_reverse,
            'particle_compartmentCoding': particle_compartmentCoding,
            'comp_dict_inverse': comp_dict_inverse
        }}
    )

def create_model_json():
    client, db, config_collection, input_collection, config_doc, input_doc, config_doc_id, input_doc_id = mongo_connect()
    model_json = {}
    # Loads required parameters from config and data dictionaries.

    # Microplastics physical properties
    model_json["MPdensity_kg_m3"] = input_doc["MPdensity_kg_m3"]
    model_json["MP_composition"] = input_doc["MP_composition"]
    model_json["shape"] = input_doc["shape"]
    model_json["MP_form"] = input_doc["MP_form"]
    model_json["big_bin_diameter_um"] = config_doc["big_bin_diameter_um"]
    model_json["N_sizeBins"] = config_doc["N_sizeBins"]
    model_json["FI"] = input_doc["FI"]
    model_json["t_half_deg_free"] = input_doc["t_half_deg_free"]
    model_json["t_frag_gen_FreeSurfaceWater"] = input_doc["t_frag_gen_FreeSurfaceWater"]

    model_json["heter_deg_factor"] = input_doc["heter_deg_factor"]
    model_json["biof_deg_factor"] = input_doc["biof_deg_factor"]
    model_json["factor_deepWater_soilSurface"] = input_doc["factor_deepWater_soilSurface"]
    model_json["factor_sediment"] = input_doc["factor_sediment"]

    model_json["biof_frag_factor"] = input_doc["biof_frag_factor"]
    model_json["heter_frag_factor"] = input_doc["heter_frag_factor"]

    # Environmental characteristics
    model_json["vol_algal_cell_m3"] = config_doc["vol_algal_cell_m3"]
    model_json["spm_density_kg_m3"] = config_doc["spm_density_kg_m3"]
    model_json["comp_input_file_name"] = config_doc["comp_input_file_name"]
    model_json["comp_interactFile_name"] = config_doc["comp_interactFile_name"]
    model_json["boxName"] = config_doc["boxName"]

    model_json["MPforms_list"] = config_doc["MPforms_list"]

    # Load parameters from config and data dictionaries
    model_json["MPforms_list"] = config_doc["MPforms_list"]
    model_json["compartments_list"] = load_csv_column(
        config_doc["comp_input_file_name"], "Cname"
    )
    model_json["solver"] = config_doc["solver"]
    model_json["compartment_types"] = config_doc["compartment_types"]

    # Derived environmental parameters
    model_json["radius_algae_m"] = ((3.0 / 4.0) * (config_doc["vol_algal_cell_m3"] / math.pi)) ** (
        1.0 / 3.0
    )
    model_json["spm_radius_um"] = model_json["radius_algae_m"] * 1e6

    # Emission scenario
    model_json["emiss_dict_g_s"] = input_doc["emiss_dict_g_s"]

    # Insert model_json into MongoDB collection "model_json" in the "utopia" database
    model_json_collection = db["model_json"]
    model_json_collection.delete_many({})  #可选 清空以前的值
    model_json_collection.insert_one(model_json)
    print("Model JSON created and inserted into MongoDB collection 'model_json'.")
    return model_json