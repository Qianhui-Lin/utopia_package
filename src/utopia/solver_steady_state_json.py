# This file contains the function that solves the steady state ODEs for the system of particles

from utopia.helpers import mass_to_num, num_to_mass
import pandas as pd
import numpy as np
from utopia.preprocessing.RC_generator_json import get_compartment_for_particle



def solver_SS_json(model_json,interaction_documentation):

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

    R, PartMass_t0 = solve_ODES_SS(
        system_particle_object_list=model_json["system_particle_object_list"],
        q_num_s=0,
        input_flows_g_s=input_flows_g_s,
        interactions_df=interaction_documentation["interaction_df"],
        model_json = model_json,
    )
    return R, PartMass_t0, input_flows_g_s, input_flows_num_s, model_json


def solve_ODES_SS(
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
            comp = get_compartment_for_particle(p, model_json)
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
            comp = get_compartment_for_particle(p, model_json)
            Pcompartment_Cvolume_m3 = comp["Cvolume_m3"]
            p["C_g_m3_SS"] = p["Pmass_g_SS"] / float(Pcompartment_Cvolume_m3)
            R.loc[p["Pcode"], "concentration_g_m3"] = p["C_g_m3_SS"]
            p["C_num_m3_SS"] = p["Pnum_SS"] / float(Pcompartment_Cvolume_m3)
            R.loc[p["Pcode"], "concentration_num_m3"] = p["C_num_m3_SS"]

    else:
        print("ERROR: No particles have been input to the system")

    return R, PartMass_t0
