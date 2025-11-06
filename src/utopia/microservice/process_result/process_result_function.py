# from utopia.helpers import 
import re
import pandas as pd
from utopia.helpers import *
import requests

def process_results_json(model_json, result,flow_estimation, particle_state,interaction_matrix_dict):
        system_particle_state_list = particle_state["system_particle_state_list"]
        """Reformat results dataframe for easier analysis by specifying size fractions, MP forms and compartments and deriving mass and number fractions, input and outup flows."""
        # Reformat results (R) dataframe 需要检查✊ 同时检查一下需不需要再换回来
        if not isinstance(result["result"], pd.DataFrame):
            df = pd.DataFrame(result["result"])
            if 'index' in result:
                df.index = result['index']
            result["result"] = df
        result["result"]["Size_Fraction_um"] = [model_json["size_dict"][x[0]] for x in result["result"].index]
        result["result"]["MP_Form"] = [
            model_json["MP_form_dict_reverse"][x[1]] for x in result["result"].index
        ]
        print("Index sample:", list(result["result"].index)[:5])
        print("Type of index[0]:", type(result["result"].index[0]))



        def extract_compartment(x):
            match = re.search(r'(\d+)', x)
            if match:
                return match.group(1)  
            else:
                raise ValueError(f"Cannot extract compartment from {x}")

        #result["result"]["Compartment"] = [
            #model_json["comp_dict_inverse"][float(x[2:-7])] for x in result["result"].index
        #]
        result["result"]["Compartment"] = [
            model_json["comp_dict_inverse"][extract_compartment(x)] for x in result["result"].index
            ]

        Results = result["result"][
            [
                "Compartment",
                "MP_Form",
                "Size_Fraction_um",
                "mass_g",
                "number_of_particles",
                "concentration_g_m3",
                "concentration_num_m3",
            ]
        ]
        # Calculate mass and number fractions relative to the total mass and number of particles and store in new dataframe "Results_extended" (needed for plotting results heatmaps)
        total_mass = sum(Results["mass_g"])
        total_number = sum(Results["number_of_particles"])
        Results_extended = Results.copy()
        Results_extended.loc[:, "mass_fraction"] = [
            x / total_mass for x in Results["mass_g"]
        ]
        Results_extended.loc[:, "number_fraction"] = [
            x / total_number for x in Results["number_of_particles"]
        ]

        mass_fraction_df = Results_extended.loc[
            :, ["Compartment", "MP_Form", "Size_Fraction_um", "mass_fraction"]
        ]

        number_fraction_df = Results_extended.loc[
            :, ["Compartment", "MP_Form", "Size_Fraction_um", "number_fraction"]
        ]

        """ Add input and output flows dict to results extended dataframe"""

        Results_extended2 = addFlows_to_results_df_json(flow_estimation,Results_extended) 

        """ Fix input flows dict to results extended dataframe"""


        # interactions_pp_df = fillInteractions_fun_OOP_dict_json(
        #     model_json["system_particle_object_list"],
        #     model_json["SpeciesList"],
        #     model_json["surfComp_list"],
        #     model_json["dict_comp"]
        # ) 
        # Estimate Pnum_SS (particle number at steady state) for each particle object in the system
        # for p in model_json["system_particle_object_list"]:
        #     p["Pnum_SS"] = mass_to_num(p["Pmass_g_SS"], p["Pvolume_m3"], p["Pdensity_kg_m3"])
        # Create a dictionary of recieving inflows per particle taking the values from the interactions matrix
        # Build a lookup of Pmass_g_SS from the state list
        state_by_code = {s["Pcode"]: s["Pmass_g_SS"] for s in system_particle_state_list}
        for p in model_json["system_particle_object_list"]:
            mass_g_ss = state_by_code.get(p["Pcode"])
            if mass_g_ss is not None:
                p["Pnum_SS"] = mass_to_num(mass_g_ss, p["Pvolume_m3"], p["Pdensity_kg_m3"])
        particle_inflows_dict_mass = {}
        particle_inflows_dict_number = {}
        for p in model_json["system_particle_object_list"]:
            inflows_p_mass = []
            inflows_p_num = []
            emission_rate_g_s = model_json["emiss_dict_g_s"][p["Pcompartment_Cname"]][
                p["Pcode"][0]
            ]
            emission_rate_num_s = mass_to_num(
                emission_rate_g_s, p["Pvolume_m3"], p["Pdensity_kg_m3"]
            )
            for p2 in model_json["system_particle_object_list"]:
                interaction_rate = interaction_matrix_dict[p2["Pcode"]][p["Pcode"]]
                mass_ss = state_by_code[p2["Pcode"]]
                num_ss  = p2["Pnum_SS"]
                # 有点意思 两个分支的结果是不一样的 🉐
                if type(interaction_rate) == dict:
                    inflow = {k: v * mass_ss for k, v in interaction_rate.items()}
                    inflows_p_mass.append(inflow)
                    inflows_p_num.append(
                        {k: v * num_ss for k, v in interaction_rate.items()}
                    )
                else:
                    inflows_p_mass.append(interaction_rate * mass_ss)
                    inflows_p_num.append(interaction_rate * num_ss)
            dict_list = [item for item in inflows_p_mass if isinstance(item, dict)]
            dict_list_num = [item for item in inflows_p_num if isinstance(item, dict)]
            merged_dict = {}
            merged_dict_num = {}
            for d in dict_list:
                for k, v in d.items():
                    if k in merged_dict:
                        merged_dict[k] += v
                    else:
                        merged_dict[k] = v
            for d in dict_list_num:
                for k, v in d.items():
                    if k in merged_dict_num:
                        merged_dict_num[k] += v
                    else:
                        merged_dict_num[k] = v

            particle_inflows_dict_mass[p["Pcode"]] = merged_dict
            particle_inflows_dict_number[p["Pcode"]] = merged_dict_num
            # Add the emission rate to the inflow dictionary
            merged_dict["Emission_flow"] = emission_rate_g_s
            merged_dict_num["Emission_flow"] = emission_rate_num_s

        # Substitute the inputflow values in the results_extended dataframe:
        for ele in particle_inflows_dict_mass:
            Results_extended2.at[ele, "inflows_g_s"] = particle_inflows_dict_mass[ele]
        for ele in particle_inflows_dict_number:
            Results_extended.at[ele, "inflows_num_s"] = particle_inflows_dict_number[
                ele
            ]
        # Add total input and putput flows to Results extended dataframe
        Results_extended2["Total_inflows_g_s"] = [
            sum(Results_extended2.iloc[i]["inflows_g_s"].values())
            for i in range(len(Results_extended2))
        ]

        Results_extended2["Total_outflows_g_s"] = [
            sum(Results_extended2.iloc[i]["outflows_g_s"].values())
            for i in range(len(Results_extended2))
        ]

        Results_extended2["Total_inflows_num_s"] = [
            sum(Results_extended2.iloc[i]["inflows_num_s"].values())
            for i in range(len(Results_extended2))
        ]

        Results_extended2["Total_outflows_num_s"] = [
            sum(Results_extended2.iloc[i]["outflows_num_s"].values())
            for i in range(len(Results_extended2))
        ]
        result["Results_extended"] = Results_extended2
        result["processed_results"] = {}
        result["processed_results"]["Results_extended"] = Results_extended2

        # return result["Results_extended"] # pandas df格式 之后需要转化
        return result["Results_extended"]

def addFlows_to_results_df_json(flow_estimation, Results_extended):
        """Calculate inflows and outflows (mass and number) and update Results_extended."""
        inflows_mass_list = []
        inflows_num_list = []
        outflows_mass_list = []
        outflows_num_list = []

        for n in range(len(Results_extended)):
            compartment = Results_extended.iloc[n]["Compartment"]
            size_fraction = Results_extended.iloc[n]["Size_Fraction_um"]
            mp_form = Results_extended.iloc[n]["MP_Form"]

            # Calculate inflows and outflows for mass
            inflows_mass = process_flows_json(
                compartment, size_fraction, mp_form, "input_flows", flow_estimation["flows_dict_mass"]
            )
            outflows_mass = process_flows_json(
                compartment,
                size_fraction,
                mp_form,
                "output_flows",
                flow_estimation["flows_dict_mass"],
            )
            inflows_mass_list.append(inflows_mass)
            outflows_mass_list.append(outflows_mass)

            # Calculate inflows and outflows for number
            inflows_num = process_flows_json(
                compartment,
                size_fraction,
                mp_form,
                "input_flows",
                flow_estimation["flows_dict_number"],
            )
            outflows_num = process_flows_json(
                compartment,
                size_fraction,
                mp_form,
                "output_flows",
                flow_estimation["flows_dict_number"],
            )
            inflows_num_list.append(inflows_num)
            outflows_num_list.append(outflows_num)

        # Update the Results_extended DataFrame with the calculated flows
        Results_extended["inflows_g_s"] = inflows_mass_list
        Results_extended["inflows_num_s"] = inflows_num_list
        Results_extended["outflows_g_s"] = outflows_mass_list
        Results_extended["outflows_num_s"] = outflows_num_list

        return Results_extended