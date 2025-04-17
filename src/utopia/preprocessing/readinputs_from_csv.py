# reads inputs from csv files and instantiates compartments and sets interactions between them

import csv
import pandas as pd
import numpy as np
from utopia.preprocessing.objects_generation import *


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
    for c in compartments:
        if c["Cname"] in UTOPIA_water_compartments:
            waterComp_objects.append(
                compartment_water(
                    Cname=c.get("Cname"),
                    SPM_mgL=c.get("SPM_mgL"),
                    flowVelocity_m_s=c.get("flowVelocity_m_s"),
                    waterFlow_m3_s=c.get("waterFlow_m3_s"),
                    T_K=c.get("T_K"),
                    G=c.get("G"),
                    Cdepth_m=c.get("Cdepth_m"),
                    Cvolume_m3=c.get("Cvolume_m3"),
                    CsurfaceArea_m2=c.get("CsurfaceArea_m2"),
                )
            )

        elif c["Cname"] in UTOPIA_surfaceSea_water_compartments:
            waterComp_objects.append(
                compartment_surfaceSea_water(
                    Cname=c.get("Cname"),
                    SPM_mgL=c.get("SPM_mgL"),
                    flowVelocity_m_s=c.get("flowVelocity_m_s"),
                    waterFlow_m3_s=c.get("waterFlow_m3_s"),
                    T_K=c.get("T_K"),
                    G=c.get("G"),
                    Cdepth_m=c.get("Cdepth_m"),
                    Cvolume_m3=c.get("Cvolume_m3"),
                    CsurfaceArea_m2=c.get("CsurfaceArea_m2"),
                )
            )
        elif c["Cname"] in UTOPIA_sediment_compartment:
            sedimentComp_objects.append(
                compartment_sediment(
                    Cname=c.get("Cname"),
                    Cdepth_m=c.get("Cdepth_m"),
                    Cvolume_m3=c.get("Cvolume_m3"),
                    CsurfaceArea_m2=c.get("CsurfaceArea_m2"),
                )
            )

        elif c["Cname"] in UTOPIA_deep_soil_compartments:
            soilComp_objects.append(
                compartment_deep_soil(
                    Cdepth_m=c.get("Cdepth_m"),
                    Cvolume_m3=c.get("Cvolume_m3"),
                    Cname=c.get("Cname"),
                    CsurfaceArea_m2=c.get("CsurfaceArea_m2"),
                )
            )

        elif c["Cname"] in UTOPIA_soil_surface_compartments:
            soilComp_objects.append(
                compartment_soil_surface(
                    Cname=c.get("Cname"),
                    Cdepth_m=c.get("Cdepth_m"),
                    Cvolume_m3=c.get("Cvolume_m3"),
                    CsurfaceArea_m2=c.get("CsurfaceArea_m2"),
                )
            )

        elif c["Cname"] in UTOPIA_air_compartments:
            airComp_objects.append(
                compartment_air(
                    Cname=c.get("Cname"),
                    Cdepth_m=c.get("Cdepth_m"),
                    Cvolume_m3=c.get("Cvolume_m3"),
                    CsurfaceArea_m2=c.get("CsurfaceArea_m2"),
                    flowVelocity_m_s=c.get("flowVelocity_m_s"),
                )
            )
        else:
            pass

    Comp_objects = (
        waterComp_objects + sedimentComp_objects + soilComp_objects + airComp_objects
    )
    return Comp_objects


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
        df_comp = comp_connex_df[["Compartments", c.Cname]].dropna()
        c.connexions = dict(zip(df_comp["Compartments"], df_comp[c.Cname]))


def instantiateParticles_from_csv(compFile):
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
