# reads inputs from csv files and instantiates compartments and sets interactions between them

import csv
import pandas as pd
import numpy as np
from utopia.microservice.generate_object.generate_object_app import *


# in default_config.json, the inputs_path_file is set to "inputs_compartments.csv"
# compartment_types=model.compartment_types
def instantiate_compartments(inputs_path_file, compartment_types):

    UTOPIA_surfaceSea_water_compartments = compartment_types[
        "UTOPIA_surfaceSea_water_compartments"
    ]
    UTOPIA_water_compartments = compartment_types["UTOPIA_water_compartments"]
    UTOPIA_deep_soil_compartments = compartment_types["UTOPIA_deep_soil_compartments"]
    UTOPIA_soil_surface_compartments = compartment_types[
        "UTOPIA_soil_surface_compartments"
    ]
    UTOPIA_sediment_compartment = compartment_types["UTOPIA_sediment_compartment"]
    UTOPIA_air_compartments = compartment_types["UTOPIA_air_compartments"]

    with open(inputs_path_file, "r") as f:
        reader = csv.DictReader(f)
        compartments = list(reader)

    waterComp_objects = []
    sedimentComp_objects = []
    soilComp_objects = []
    airComp_objects = []

    waterComp_jsons = []
    sedimentComp_jsons = []
    soilComp_jsons = []
    airComp_jsons = []

    for c in compartments:
        if c["Cname"] in UTOPIA_water_compartments:
            obj = compartment_water(
                Cname=c["Cname"],
                SPM_mgL=parse_value(c["SPM_mgL"]),
                flowVelocity_m_s=parse_value(c["flowVelocity_m_s"]),
                waterFlow_m3_s=parse_value(c["waterFlow_m3_s"]),
                T_K=parse_value(c["T_K"]),
                G=parse_value(c["G"]),
                Cdepth_m=parse_value(c["Cdepth_m"]),
                Cvolume_m3=parse_value(c["Cvolume_m3"]),
                CsurfaceArea_m2=parse_value(c["CsurfaceArea_m2"]),
            )
            waterComp_objects.append(obj)
            waterComp_jsons.append(obj.to_dict())

        elif c["Cname"] in UTOPIA_surfaceSea_water_compartments:
            obj = compartment_surfaceSea_water(
                Cname=c.get("Cname"),
                SPM_mgL=parse_value(c.get("SPM_mgL")),
                flowVelocity_m_s=parse_value(c.get("flowVelocity_m_s")),
                waterFlow_m3_s=parse_value(c.get("waterFlow_m3_s")),
                T_K=parse_value(c.get("T_K")),
                G=parse_value(c.get("G")),
                Cdepth_m=parse_value(c.get("Cdepth_m")),
                Cvolume_m3=parse_value(c.get("Cvolume_m3")),
                CsurfaceArea_m2=parse_value(c.get("CsurfaceArea_m2")),
            )
            waterComp_objects.append(obj)
            waterComp_jsons.append(obj.to_dict())
            

        elif c["Cname"] in UTOPIA_sediment_compartment:
            
            obj = compartment_sediment(
                    Cname=c.get("Cname"),
                    Cdepth_m=parse_value(c.get("Cdepth_m")),
                    Cvolume_m3=parse_value(c.get("Cvolume_m3")),
                    CsurfaceArea_m2=parse_value(c.get("CsurfaceArea_m2")),
                )
            
            
            sedimentComp_objects.append(obj)
            sedimentComp_jsons.append(obj.to_dict())

        elif c["Cname"] in UTOPIA_deep_soil_compartments:
            obj = compartment_deep_soil(
                    Cdepth_m=parse_value(c.get("Cdepth_m")),
                    Cvolume_m3=parse_value(c.get("Cvolume_m3")),
                    Cname=c.get("Cname"),
                    CsurfaceArea_m2=parse_value(c.get("CsurfaceArea_m2")),
                )
            

            soilComp_objects.append(obj)
            soilComp_jsons.append(obj.to_dict())

        elif c["Cname"] in UTOPIA_soil_surface_compartments:
            obj = compartment_soil_surface(
                    Cname=c.get("Cname"),
                    Cdepth_m=parse_value(c.get("Cdepth_m")),
                    Cvolume_m3=parse_value(c.get("Cvolume_m3")),
                    CsurfaceArea_m2=parse_value(c.get("CsurfaceArea_m2")),
                )
            
            soilComp_objects.append(obj)
            soilComp_jsons.append(obj.to_dict())

        elif c["Cname"] in UTOPIA_air_compartments:
            obj = compartment_air(
                    Cname=c.get("Cname"),
                    Cdepth_m=c.get("Cdepth_m"),
                    Cvolume_m3=c.get("Cvolume_m3"),
                    CsurfaceArea_m2=c.get("CsurfaceArea_m2"),
                    flowVelocity_m_s=c.get("flowVelocity_m_s"),
                )
            

            airComp_objects.append(obj)
            airComp_jsons.append(obj.to_dict())

        else:
            pass

    Comp_objects = (
        waterComp_objects + sedimentComp_objects + soilComp_objects + airComp_objects
    )

    Comp_jsons = (
    waterComp_jsons + sedimentComp_jsons + soilComp_jsons + airComp_jsons
    )


    return Comp_objects, Comp_jsons

# compartments 在objects_generation.py中是instantiate_compartments的返回值 
# 这里初始的返回值只有Comp_objects, 我后来又加上了Comp_jsons ⚠️

def set_interactions(compartments, connexions_path_file):
    # Create connexions attributes as dictionaries for the different #compartments from the compartmentsInteractions file
    with open(connexions_path_file, "r") as infile:
        reader = csv.reader(infile)
        array = []
        for row in reader:
            r = []
            for ele in row:
                if "," in ele:
                    r.append(ele.split(","))
                else:
                    r.append(ele)
            array.append(r)
        comp_connex_df = pd.DataFrame(array)
        comp_connex_df.columns = comp_connex_df[0]
        # comp_connex_df = comp_connex_df.set_index("Compartments")
        comp_connex_df = comp_connex_df.drop(index=[0])
        comp_connex_df.replace("", np.nan, inplace=True)

    # comp_connex_df = pd.read_csv(connexions_path_file)

    for c in compartments:
        
        cname = c["Cname"]
        if cname in comp_connex_df.columns:
            df_comp = comp_connex_df[["Compartments", cname]].dropna()
            c["connexions"] = dict(zip(df_comp["Compartments"], df_comp[cname]))


def instantiateParticles_from_csv(compFile): #此方法没有被调用
    with open(compFile, "r") as f:
        reader = csv.DictReader(f)
        particles = list(reader)

    particlesObj_list = []
    for p in particles:
        particlesObj_list.append(
            Particulates(
                Pname=p.get("Name"),
                Pform=p.get("form"),
                Pcomposition=p.get("composition"),
                Pdensity_kg_m3=float(p.get("density_kg_m3")),
                Pshape=p.get("shape"),
                PdimensionX_um=float(p.get("dimensionX_um")),
                PdimensionY_um=float(p.get("dimensionY_um")),
                PdimensionZ_um=float(p.get("dimensionZ_um")),
            )
        )

    return particlesObj_list


def generate_particles_from_df(particles_df):
    """Generates a list of Particulates objects from a pandas DataFrame."""

    particlesObj_list = []
    for _, row in particles_df.iterrows():
        particlesObj_list.append(
            Particulates(
                Pname=row["Name"],
                Pform=row["form"],
                Pcomposition=row["composition"],
                Pdensity_kg_m3=float(row["density_kg_m3"]),
                Pshape=row["shape"],
                PdimensionX_um=float(row["dimensionX_um"]),
                PdimensionY_um=float(row["dimensionY_um"]),
                PdimensionZ_um=float(row["dimensionZ_um"]),
            )
        )

    return particlesObj_list

def generate_particles_json_from_df(particles_df):
    """Generates both a list of Particulates objects and their JSON dicts from a pandas DataFrame."""
    
    particles_obj_list = []
    particles_json_list = []
    for _, row in particles_df.iterrows():
        # Create the object first
        particle_obj = Particulates(
            Pname=row["Name"],
            Pform=row["form"],
            Pcomposition=row["composition"],
            Pdensity_kg_m3=float(row["density_kg_m3"]),
            Pshape=row["shape"],
            PdimensionX_um=float(row["dimensionX_um"]),
            PdimensionY_um=float(row["dimensionY_um"]),
            PdimensionZ_um=float(row["dimensionZ_um"]),
        )
        particles_obj_list.append(particle_obj)
        # Convert to JSON and add to list
        particles_json_list.append(particle_obj.to_dict())

    return particles_obj_list, particles_json_list


def generate_system_species_list(
    system_particle_object_list, MPforms_list, compartmentNames_list, boxNames_list
):
    particle_sizes_coding = {"mp1": "a", "mp2": "b", "mp3": "c", "mp4": "d", "mp5": "e"}

    particle_forms_coding = dict(zip(MPforms_list, ["A", "B", "C", "D"]))

    particle_compartmentCoding = dict(
        zip(compartmentNames_list, list(range(len(compartmentNames_list))))
    )

    def particle_nameCoding(particle, boxNames_list):
        # if len(boxNames_list) != 1:

        particle_sizeCode = particle_sizes_coding[particle.Pname[0:3]]
        particle_formCode = particle_forms_coding[particle.Pform]
        particle_compartmentCode = particle_compartmentCoding[
            particle.Pcompartment.Cname
        ]
        particle_boxCode = particle.Pcompartment.CBox.Bname

        particleCode = (
            particle_sizeCode
            + particle_formCode
            + str(particle_compartmentCode)
            + "_"
            + particle_boxCode
        )

        return particleCode

    SpeciesList = []
    for particle in system_particle_object_list:
        SpeciesList.append(particle_nameCoding(particle, boxNames_list))
        particle.Pcode = particle_nameCoding(particle, boxNames_list)

    return SpeciesList
# ⚠️⚠️⚠️
def generate_system_species_list_json(
    system_particle_json_list, MPforms_list, compartmentNames_list, boxNames_list
):
    """JSON version that works with particle JSON objects (dictionaries)."""
    particle_sizes_coding = {"mp1": "a", "mp2": "b", "mp3": "c", "mp4": "d", "mp5": "e"}

    particle_forms_coding = dict(zip(MPforms_list, ["A", "B", "C", "D"]))

    particle_compartmentCoding = dict(
        zip(compartmentNames_list, list(range(len(compartmentNames_list))))
    )

    def particle_nameCoding_json(particle_json, boxNames_list):
        """Generate particle code from JSON particle data."""
        
        particle_sizeCode = particle_sizes_coding[particle_json["Pname"][0:3]]
        particle_formCode = particle_forms_coding[particle_json["Pform"]]
        
        # Handle compartment data - assuming it's stored as nested JSON or reference
        #if isinstance(particle_json["Pcompartment"], dict):
            # If compartment is stored as nested JSON
        compartment_name = particle_json["Pcompartment_Cname"]
        box_name = particle_json["Pcompartment_CBox_Bname"]
        #else:
            # If compartment is stored as string reference or other format
            
            #compartment_name = particle_json["Pcompartment"]
            #box_name = boxNames_list[0] if boxNames_list else "default"
        
        particle_compartmentCode = particle_compartmentCoding[compartment_name]
        
        particleCode = (
            particle_sizeCode
            + particle_formCode
            + str(particle_compartmentCode)
            + "_"
            + box_name
        )

        return particleCode

    SpeciesList = []
    updated_particles_json = []
    
    for particle_json in system_particle_json_list:
        # Create a copy to avoid modifying original 有待确认
        #updated_particle = particle_json.copy()
        
        # Generate the particle code
        particle_code = particle_nameCoding_json(particle_json, boxNames_list)
        # Add to lists
        SpeciesList.append(particle_code)        
        # Add the code to the particle JSON
        particle_json["Pcode"] = particle_code
        

    return SpeciesList

def parse_value(val):
    if val is None:
        return None
    val = val.strip()
    if val.lower() == "nan" or val == "":
        return None
    try:
        return float(val)
    except ValueError:
        return val
