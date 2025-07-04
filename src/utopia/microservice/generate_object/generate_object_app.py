import pymongo
import math
import pandas as pd
import string
import os
import sys
from pathlib import Path
from utopia.globalConstants import *
from utopia.objects.box_class_json import *
from utopia.objects.particulate_classes_json import *
from utopia.objects.compartment_classes_json import *
from utopia.preprocessing.readinputs_from_csv_json import *
import json
import copy

def mongo_connect():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client['utopia']
    config_collection = db['configure_data']
    input_collection = db['input_data']

    config_doc = config_collection.find_one()
    config_doc_id = config_doc['_id'] if config_doc is not None else None

    input_doc = input_collection.find_one()
    input_doc_id = input_doc['_id'] if input_doc is not None else None

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

def generate_particles_dataframe_json():
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
            particles_df = pd.DataFrame(data).to_dict(orient='records')


        return particles_df
        '''
            update_input = input_collection.update_one(
                {'_id': input_doc_id},
                {'$set': {
                    'particles_df': particles_df.to_dict(orient='records')
                }}
            )
        '''
          
def generate_coding_dictionaries_json():
    client, db, *_, = mongo_connect()
    model_json_collection = db["model_json"]
    model_json_doc = model_json_collection.find_one()
    model_json_doc_id = model_json_doc['_id']
    """Generates Mp form, size and compartment coding dictionaries as attributes."""
    if model_json_doc["particles_df"] is None:
        raise ValueError("Particles DataFrame has not been generated.")
    particles_df = pd.DataFrame(model_json_doc["particles_df"])
    # Dictionary mapping particle names to sizes
    dict_size_coding = dict(
        zip(particles_df["Name"], particles_df["dimensionX_um"] * 2)
        )

    # Generate size codes (a-z based on number of bins)
    size_codes = list(string.ascii_lowercase[: model_json_doc["N_sizeBins"]])

    # Dictionary mapping size codes to sizes
    size_dict = dict(zip(size_codes, dict_size_coding.values()))

    # Dictionary mapping MP form codes to MP forms
    particle_forms_coding = dict(zip(model_json_doc["MPforms_list"], ["A", "B", "C", "D"]))
    MP_form_dict_reverse = {
            v: k for k, v in particle_forms_coding.items()
        }

    # Dictionary mapping compartment names to compartment codes
    particle_compartmentCoding = dict(
        zip(
                model_json_doc["compartments_list"],
                list(range(len(model_json_doc["compartments_list"]))),
            )
        )
    comp_dict_inverse = {
            str(v): k for k, v in particle_compartmentCoding.items()
        }
    
    update_model_json = model_json_collection.update_one(
        {'_id': model_json_doc_id},
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

    model_json["particles_df"] = generate_particles_dataframe_json()

    # Add base path
    base_path = Path(__file__).resolve().parent.parent.parent / "data"
    model_json["base_path"] = str(base_path)



    # Insert model_json into MongoDB collection "model_json" in the "utopia" database
    model_json_collection = db["model_json"]
    # model_json_collection.delete_many({})  #可选 清空以前的值
    result = model_json_collection.insert_one(model_json)
    inserted_id = result.inserted_id
    print("Model JSON created and inserted into MongoDB collection 'model_json'.")
    return inserted_id,model_json


def generate_objects_json(model_json):
    """Function for generating the UTOPIA model objects: model box, model compartments and the model particles"""
    # Boxes
    UTOPIA = create_box_json(model_json["boxName"])
    # print(f"The model box {boxName} has been created")
    # UTOPIA现在是json 字符串 之后可能要修改
    modelBoxes = [UTOPIA]
    ## ⚠️ 改这里 b现在不是dict 而是json字符串，改成dict
    # modelBoxes=instantiateBoxes_from_csv(boxFile)
    boxNames_list = [b["Bname"] for b in modelBoxes]

    # Compartmets
    """Call read imput file function for compartments"""
    # base_path = Path(__file__).resolve().parent / "data"
    # Use model_json as the model object
    inputs_path_file = Path(model_json["base_path"]) / model_json["comp_input_file_name"]

    _, compartments = instantiate_compartments(
        inputs_path_file=inputs_path_file, compartment_types=model_json["compartment_types"]
    )

    connexions_path_file = Path(model_json["base_path"]) / model_json["comp_interactFile_name"]
    set_interactions(compartments, connexions_path_file)

    # Assign modelling code to compartments (now compartments is a list of dicts)
    for c in range(len(compartments)):
        compartments[c]["Ccode"] = c + 1


    for idx, c in enumerate(compartments):
        # Convert compartment dict to JSON string
        compartment_json_str = json.dumps(c)
        # Calculate volume using your function
        updated_json_str = calc_volume_compartment_json(compartment_json_str)
        # Update the compartment dict with new values
        compartments[idx] = json.loads(updated_json_str)

    # Dictionary of compartments
    dict_comp = {
        item["Cname"]: item for item in compartments
    }

    compartmentNames_list = [item["Cname"] for item in compartments]

    # PARTICLES

    ##Free microplastics (freeMP)

    # MP_freeParticles = instantiateParticles_from_csv(inputs_path + mp_imputFile_name)
    # ⚠️ generate_particles_json_from_df 里面并没有计算MP_freeParticles的体积 有点奇怪❓
    # 哦，在下面算了，但是只对MP_freeParticles_json 计算了体积，没有对MP_freeParticles_obj计算体积
    # 此处插入mongodb的 particles_df仍为list, 而非 DataFrame
    model_json["particles_df"] = pd.DataFrame(model_json["particles_df"])
    MP_freeParticles_obj, MP_freeParticles_json = generate_particles_json_from_df(model_json["particles_df"])
    # here, MP_freeParticles is a list of dicts, each dict representing a particle
    dict_size_coding = dict(
        zip(
            [p["Pname"] for p in MP_freeParticles_json],
            [p["diameter_um"] for p in MP_freeParticles_json],
        )
    )
    for i in MP_freeParticles_obj:
        i.calc_volume()
    ###Calculate freeMP volume
    for i in MP_freeParticles_json:
        Particulates.calc_volume_json(i)
        # print(f"Density of {i.Pname}: {i.Pdensity_kg_m3} kg_m3")
        ##Biofouled microplastics (biofMP)
        spm = Particulates(
            Pname="spm1",
            Pform="suspendedParticulates",
            Pcomposition="Mixed",
            Pdensity_kg_m3=model_json["spm_density_kg_m3"],
            Pshape="sphere",
            PdimensionX_um=model_json["spm_radius_um"],
            PdimensionY_um=0,
            PdimensionZ_um=0,
        )
        spm_dict = spm.to_dict()
        Particulates.calc_volume_json(spm_dict)
        # print(f"spm Volume: {spm.Pvolume_m3} m3")
        # print(f"Density of spm: {spm.Pdensity_kg_m3} kg_m3")

    # 注意 也有一个可以直接生成json particulatesBF的函数
    MP_biofouledParticles_json = []
    MP_biofouledParticles_obj = []
    '''
    for i in MP_freeParticles_obj:
        MP_singel_biofouledParticle_obj = ParticulatesBF(parentMP=i, spm=spm)
        MP_singel_biofouledParticle_json = MP_singel_biofouledParticle_obj.to_dict()

        MP_biofouledParticles_json.append(MP_singel_biofouledParticle_json)
        MP_biofouledParticles_obj.append(MP_singel_biofouledParticle_obj)
    # print(
    #     f"The biofouled MP particles {[p.Pname for p in MP_biofouledParticles]} have been generated"
    # )
    for i in MP_biofouledParticles_obj:
        i.calc_volume()

    ###Calculate biofMP volume
    for i in MP_biofouledParticles_json:
        Particulates.calc_volume_json(i)
        # print(f"Density of {i.Pname}: {i.Pdensity_kg_m3} kg_m3")
    '''
    for i in MP_freeParticles_json:
        MP_singel_biofouledParticle_json = ParticulatesBF.create_bf_json (parentMP_json = i, spm_json = spm_dict)
        MP_biofouledParticles_json.append(MP_singel_biofouledParticle_json)

    ###Calculate biofMP volume
    for i in MP_biofouledParticles_json:
        Particulates.calc_volume_json(i)
        # print(f"Density of {i.Pname}: {i.Pdensity_kg_m3} kg_m3")
    ##Heteroaggregated microplastics (heterMP)
    MP_heteroaggregatedParticles_json = []
    for i in MP_freeParticles_json:
        MP_single_heterParticle_json = ParticulatesSPM.create_pspm_json(parentSPM_json = spm_dict, parentMP_json = i)
        MP_heteroaggregatedParticles_json.append(MP_single_heterParticle_json)
    # print(
    #     f"The heteroaggregated MP particles {[p.Pname for p in MP_heteroaggregatedParticles]} have been generated"
    # )

    ###Calculate heterMP volume
    for i in MP_heteroaggregatedParticles_json:
        ParticulatesSPM.calc_volume_heter_json(i, parentMP_json=i["parentMP"], parentSPM_json = i["parentSPM"])
        # print(f"Density of {i.Pname}: {i.Pdensity_kg_m3} kg_m3")

    ##Biofouled and Heteroaggregated microplastics (biofHeterMP)
    MP_biofHeter_json = []
    for i in MP_biofouledParticles_json:
        MP_single_biofHeter_json = ParticulatesSPM.create_pspm_json(
            parentSPM_json=spm_dict, parentMP_json=i)
        MP_biofHeter_json.append(MP_single_biofHeter_json)
    # for i in MP_biofHeter:
    #     print(f"Density of {i.Pname}: {i.Pdensity_kg_m3} kg_m3")
    # print(
    #     f"The biofouled and heteroaggregated MP particles {[p.Pname for p in MP_biofHeter]} have been generated"
    # )

    ###Calculate biofHeterMP volume
    for i in MP_biofHeter_json:
        ParticulatesSPM.calc_volume_heter_json(i, parentMP_json=i["parentMP"], parentSPM_json = i["parentSPM"])

    particles = (
        MP_freeParticles_json
        + MP_biofouledParticles_json
        + MP_heteroaggregatedParticles_json
        + MP_biofHeter_json
    )

    particles_properties = {
        "Particle": [p["Pname"] for p in particles],
        "Radius_m": [p["radius_m"] for p in particles],
        "Volume_m3": [p["Pvolume_m3"] for p in particles],
        "Density_kg_m3": [p["Pdensity_kg_m3"] for p in particles],
        "Corey Shape Factor": [p["CSF"] for p in particles],
    }

    particles_properties_df = pd.DataFrame(data=particles_properties)

    # Assign compartmets to UTOPIA

    for comp in compartments:
        comp_copy = copy.deepcopy(comp)
        add_compartment_to_json(UTOPIA, comp_copy)
    # print(
    #     f"The compartments {[comp.Cname for comp in UTOPIA.compartments]} have been assigned to {UTOPIA.Bname } model box"
    # )

    # Estimate volume of UTOPIA box by adding volumes of the compartments addedd
    # UTOPIA.calc_Bvolume_m3() #currently volume of soil and air boxess are missing, to be added to csv file

    # Add particles to compartments
    # modelBoxes is a list of JSON strings, compartments is a list of JSON strings
    for box_idx, box_json_str in enumerate(modelBoxes):
        # box_json_str may be a dict or a JSON string
        if isinstance(box_json_str, dict):
            box = box_json_str
        else:
            box = json.loads(box_json_str)
        if "compartments" in box:
            for comp_idx, comp_json_str in enumerate(box["compartments"]):
                # comp_json_str may be a dict or a JSON string
                if isinstance(comp_json_str, dict):
                    comp = comp_json_str
                else:
                    comp = json.loads(comp_json_str)
                for p in particles:
                    p_copy = copy.deepcopy(p)
                    p_form = p_copy["Pform"] 
# Call add_particles_to_compartment_json
                    updated_comp_json = add_particles_to_compartment_json(
                        comp,  # Convert current comp dict back to JSON string
                        p_copy,            # Pass the particle dict (function handles it)
                        p_form             # Pass the particle form
                    )
                    
                    # Update comp dict with the result
                    if isinstance(comp, dict):
                        comp = json.loads(updated_comp_json) if isinstance(updated_comp_json, str) else updated_comp_json
                    else:
                        comp = json.loads(updated_comp_json)
                
                # After all particles added, update the compartment in the box
                box["compartments"][comp_idx] = comp

        modelBoxes[box_idx] = box

    # List of particle objects in the system:
    system_particle_object_list_json = []

    for b in modelBoxes:
        # b = json.loads(b_json)
        if "compartments" in b:
            for c in b["compartments"]:
                # c = json.loads(c_json)
                if "particles" in c:
                    for particle_type in ["freeMP", "heterMP", "biofMP", "heterBiofMP"]:
                        if particle_type in c["particles"]:
                            for particle in c["particles"][particle_type]:
                                # Ensure particle is a dict (not a JSON string)
                                if isinstance(particle, str):
                                    particle_dict = json.loads(particle)
                                else:
                                    particle_dict = particle
                                system_particle_object_list_json.append(particle_dict)

    # Generate list of species names and add code name to object
    SpeciesList = generate_system_species_list_json(system_particle_json_list = system_particle_object_list_json,MPforms_list = model_json["MPforms_list"], compartmentNames_list = compartmentNames_list, boxNames_list = boxNames_list)

    print("modleBoxes: ", modelBoxes)
    print("type of modelBoxes: ", type(modelBoxes))
    print("UTOPIA_dict_: ", UTOPIA)
    particles_properties_df_dict = particles_properties_df.to_dict(orient="records")

    # DataFrames cannot be directly inserted into MongoDB.
    # You need to convert them to a list of dictionaries first.
    return (
        system_particle_object_list_json,
        SpeciesList,
        spm_dict,
        dict_comp,
        particles_properties_df_dict
    )


###CONTINUE HERE### 