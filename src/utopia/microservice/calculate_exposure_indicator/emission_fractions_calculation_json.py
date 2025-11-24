import copy
import os
import pandas as pd
# from utopia.utopia_json import *
# from utopia.results_processing_json.process_results_json import *


# from results_processing.process_results import ResultsProcessor
import matplotlib.pyplot as plt
import pymongo

# MongoDB settings - using environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

 #use this when mongodb runnning in container

DB_NAME = os.getenv("DB_NAME", "utopia")
CONFIG_COLLECTION = "configure_data"
INPUT_COLLECTION = "input_data"
MODEL_COLLECTION = "model_json"


dispersing_comp_list = ["Air", "Ocean_Mixed_Water", "Ocean_Surface_Water"]

def flatten_list_columns(df):
    for col in df.columns:
        # Clean each cell
        def clean_cell(x):
            # Convert strings to numbers if possible
            if isinstance(x, str):
                try:
                    return float(x)
                except ValueError:
                    return x   # leave unchanged if not convertible
            
            # Sum list-values
            if isinstance(x, list):
                return sum(x)
            
            return x

        df[col] = df[col].apply(clean_cell)

    return df


def emission_fractions_calculations_json(model_json,processed_result,processed_result_new_models,model_json_new_models,flow_estimation_new_models):
    """Calculate the emission fractions Following the LRTP metrics of the emission fractions approach (EFA; φ1, φ2, φ3) from https://doi.org/10.1021/acs.est.2c03047 Rigth now we are only calculating φ1 and φ2. The φ3 is not calculated as it is not needed for the model and we only estimate them in mass."""

    ## We use the same values of Crossectional area for Air and Water as in Breivik et al. 2022 and scale it for our water compartments

    Air_crossectional_area_m2 = (
        2.27e9  # Assuming a higth of air of 6000 m (From the OECD tool)
    )
    Water_crossectional_area_m2 = 2.68e7  # Assuming a higth of water of 100 m

    # Assuming that all the water is ocean water.

    Ocean_surface_crosssectional_area_m2 = Water_crossectional_area_m2 * (0.1 / 100)

    Ocean_mixed_crosssectional_area_m2 = Water_crossectional_area_m2 * (
        (100 - 0.1) / 100
    )

    crossSectional_area_m2 = {
        "Air": Air_crossectional_area_m2,
        "Ocean_Surface_Water": Ocean_surface_crosssectional_area_m2,
        "Ocean_Mixed_Water": Ocean_mixed_crosssectional_area_m2,
    }

    """ Mass Emission Fractions"""

    """Environmentally Dispersed Fraction (φ1)"""
    # Environmentally Dispersed Fraction (φ1) quantifies the relative extent to which the pollutants (MPs) can reach remote regions.
    processed_result_df = {}

    for R_comp in dispersing_comp_list:
        # processed_list = processed_result_new_models[R_comp]["processed_result"]
        # processed_list = processed_result_new_models["Ocean_Surface_Water"]["processed_result"]
        processed_list = processed_result["processed_result"]
        processed_result_df[R_comp] = pd.DataFrame(processed_list)
    φ1_dict_mass = {}
    φ1_dict_num = {}
    # print("=== DEBUG processed_result_new_models KEYS ===")
    # for R_comp in dispersing_comp_list:
    #     print(R_comp, processed_result_new_models[R_comp].keys())
    # Environmentally Dispersed Fractions (ϕ1)
    # print("\n=== FULL processed_result content for debugging ===")
    # import pprint
    # for R_comp in dispersing_comp_list:
    #     pprint.pprint(processed_result_new_models[R_comp]["processed_result"])
    for R_comp in dispersing_comp_list:
        df = processed_result_df[R_comp]

        # select rows belonging to this compartment
        comp_mask = df["Compartment"] == R_comp

        # sum concentration_g_m3 over all size fractions / forms for this compartment
        conc_sum = df.loc[comp_mask, "concentration_g_m3"].sum()

        Nadv = (
            conc_sum
            * crossSectional_area_m2[R_comp]
            # * float(model_json_new_models[R_comp]["dict_comp"][R_comp]["flowVelocity_m_s"])
            # * float(model_json_new_models["Ocean_Surface_Water"]["dict_comp"][R_comp]["flowVelocity_m_s"])
            * float(model_json["dict_comp"][R_comp]["flowVelocity_m_s"])

        )

        NE_g_s = sum(
            value
            # for subdict in model_json_new_models[R_comp]["emiss_dict_g_s"].values()
            # for subdict in model_json_new_models["Ocean_Surface_Water"]["emiss_dict_g_s"].values()
            for subdict in model_json["emiss_dict_g_s"].values()
            for value in subdict.values()
        )

        φ1_dict_mass[R_comp] = Nadv / NE_g_s
        # Dispersed fraction in number (TO BE DONE, have to think about this)
        # Nadv_num = (
        #     sum(
        #         model.Results_extended["concentration_num_m3"][
        #             model.Results_extended["Compartment"] == R_comp
        #         ]
        #     )
        #     * crossSectional_area_m2[R_comp]
        #     * float(model.dict_comp[R_comp].flowVelocity_m_s)
        # )
        # NE_num_s = sum(q_num_s)

        # φ1_dict_num[R_comp] = Nadv_num / NE_num_s

    # Estimate composition of Environmentally Dispersed Fractions in percentage:
    φ1_mass_comp = [
        round(v * 100 / sum(φ1_dict_mass.values()), 4) for v in φ1_dict_mass.values()
    ]
    # φ1_num_comp = [
    #     round(v * 100 / sum(φ1_dict_num.values()), 4) for v in φ1_dict_num.values()
    # ]
    φ1_comp_table = pd.DataFrame(
        {
            "Compartment": list(φ1_dict_mass.keys()),
            "φ1_mass_%": φ1_mass_comp,
        }
    )
    # "φ1_num_%": φ1_num_comp,
    for E1_comp, E1 in zip(φ1_dict_mass.keys(), φ1_dict_mass.values()):
        print(
            "Environmentally Dispersed Mass Fractions through {} = {}".format(
                E1_comp, E1
            )
        )
    print("φ1 for mass =", sum(φ1_dict_mass.values()))

    # for E1_comp_num, E1_num in zip(φ1_dict_num.keys(), φ1_dict_num.values()):
    #     print(
    #         "Environmentally Dispersed Particle Number Fractions through {} = {}".format(
    #             E1_comp_num, int(E1_num)
    #         )
    #     )
    # print("φ1 for particle number =", sum(φ1_dict_num.values()))

    """Remotely transferred fraction of mass (ϕ2)"""

    # φ2 expresses the relative extent to which a the MPs are (net) transferred to the target remote compartment following environmental dispersion to the remote region

    internal_comp_process_list = [
        "k_discorporation",
        "k_fragmentation",
        "k_heteroaggregation",
        "k_heteroaggregate_breackup",
        "k_biofouling",
        "k_defouling",
    ]

    φ2_dict_mass = {}
    # φ2_dict_num = {}

    # Remotely transferred fraction of mass to the target remote compartment (φ2) will come through air and water from the compartments listed in the dispersing_comp_list: Air, Ocean_Mixed_Water and Ocean_Surface_Water.

    # The target remote compartments are Ocean Surface Water as an approximation to study transfer to the Ocean Gyres, Ocean Column water and Ocean sediment and Beaches_Soil_Surface for representing transer to remote beaches.

    # We can estimate φ2 in mass idependent of the size fraction of the particles, however when estimating φ2 in particle number we have to do it per size fraction (to be done).
    """The remotely transferred fraction of particle number can only be estimated by size fraction?? If we do it with total number of particles independent of the size it can occur that we get negative values as the flows would be dominated by a specific size fraction and can potentially occur that the outflows of particles from a compartment in particle number is bigger than the inflows due to the fragmentation processess??"""

    target_remote_comp_List = [
        "Ocean_Surface_Water",
        "Ocean_Column_Water",
        "Sediment_Ocean",
        "Beaches_Soil_Surface",
    ]
    # import pprint

    # for transfComp in dispersing_comp_list:
    #     print("\n=== DEBUG outputFlows for", transfComp, "===")
    #     pprint.pprint(flow_estimation_new_models[transfComp]["tables_outputFlows_mass"])
    flow_input_df = {}
    flow_output_df = {}

    for transfComp in dispersing_comp_list:

        # Convert input flows (dict of list-of-dicts → dict of DataFrames)
        input_dict = flow_estimation_new_models[transfComp]["tables_inputFlows_mass"]
        print("generated input dict")
        flow_input_df[transfComp] = {
            target: pd.DataFrame(input_dict[target])
            for target in input_dict
        }
        print("generated flow_input_df")
        # Convert output flows (dict of list-of-dicts → dict of DataFrames)
        output_dict = flow_estimation_new_models[transfComp]["tables_outputFlows_mass"]
        flow_output_df[transfComp] = {
            target: pd.DataFrame(output_dict[target])
            for target in output_dict
        }
    for target_remote_comp in target_remote_comp_List:
        φ2_Tcomp = {}
        # φ2_Tcomp_num = {}
        for transfComp in dispersing_comp_list:
            if transfComp == target_remote_comp:
                NE_x_g_s = NE_g_s
                # NE_x_num_s = NE_num_s

            else:
                NE_x_g_s = 0
            # NE_x_num_s = 0

            input_flows  = flow_input_df[transfComp][target_remote_comp].copy()
            output_flows = flow_output_df[transfComp][target_remote_comp].copy()

            # input_flows_num = model_results[transfComp]["tables_inputFlows_num"][
            #     target_remote_comp
            # ]
            # output_flows_num = model_results[transfComp]["tables_outputFlows_number"][
            #     target_remote_comp
            # ]
            
            for k_p in internal_comp_process_list:
                if k_p in output_flows.columns:
                    output_flows.drop(columns=k_p, inplace=True)
                # if k_p in output_flows_num:
                #     output_flows_num.drop(columns=k_p, inplace=True)
                        # Flatten list-valued columns

            input_flows  = flatten_list_columns(input_flows)
            output_flows = flatten_list_columns(output_flows)
            print("generated flatten list columns")

            # Substitute the columns of the dataframe that have list of values for the sum of the values(sum output flows of that process)
            # for k_o in output_flows:
            #     output_flows[k_o] = [
            #         sum(x) if isinstance(x, list) else x for x in output_flows[k_o]
            #     ]

            # Compute totals safely
            total_in  = input_flows.sum(numeric_only=True).sum()
            total_out = output_flows.sum(numeric_only=True).sum()

            # φ2 calculation
            φ2_Tcomp[transfComp] = (
            φ1_dict_mass[transfComp] *
            (NE_x_g_s + total_in - total_out) /
            NE_g_s
            )

            # φ2_Tcomp[transfComp] = (
            #     φ1_dict_mass[transfComp]
            #     * (
            #         NE_x_g_s
            #         + sum([sum(input_flows[P]) for P in input_flows])
            #         - sum([sum(output_flows[P]) for P in output_flows])
            #     )
            #     / NE_g_s
            # )
            # φ2_Tcomp_num[transfComp] = (
            #     φ1_dict_num[transfComp]
            #     * (
            #         NE_x_num_s
            #         + sum([sum(input_flows_num[P]) for P in input_flows_num])
            #         - sum([sum(output_flows_num[P]) for P in output_flows_num])
            #     )
            #     / NE_num_s
            # )
        φ2_dict_mass[target_remote_comp] = φ2_Tcomp
        # φ2_dict_num[target_remote_comp] = φ2_Tcomp_num

    φ2_mass = []
    for E2_comp, E2 in zip(φ2_dict_mass.keys(), φ2_dict_mass.values()):
        φ2_mass.append(sum(E2.values()))

        print(
            "Remotely transferred fraction to {} = {}".format(E2_comp, sum(E2.values()))
        )

    # for E2_compN, E2N in zip(φ2_dict_num.keys(), φ2_dict_num.values()):
    #     print(
    #         "Remotely transferred particle number fraction to {} = {}".format(
    #             E2_compN, sum(E2N.values())
    #         )
    #     )

    print("Total remotely transferred mass fraction = {}".format(sum(φ2_mass)))

    φ2_mass_table = pd.DataFrame(
        {"Remotely transferred fraction to": φ2_dict_mass.keys(), "φ2": φ2_mass}
    )

    emission_fractions_mass_data = {
        "Emission Fraction": ["φ1", "φ2_1", "φ2_2", "φ2_3", "φ2_4"],
        "y": [sum(φ1_dict_mass.values())] + φ2_mass,
    }

    return emission_fractions_mass_data  # , φ1_comp_table


##### the end
def estimate_emission_fractions_json(model_json):
    from utopia.results_processing.process_results import ResultsProcessor
    client = pymongo.MongoClient(MONGO_URI)
    db = client['utopia']
    model_json_collection = db[MODEL_COLLECTION]

    """Estimate emission fractions"""
    # For estimating the emission fractions we need to make emissions to targeted compartments.

    # Run model with emissions to specific compartments that can cause emissions to remote regions (dispersing compartments) to estimate the emission fractions

    model_results = {}

    # run the model with new data (just modifying the recieving compartment)

    # Reasign emissions to the dispersing compartments
    # Identify where the emission is
    base_emiss_dict = model_json["emiss_dict_g_s"]
    for compartment, values in base_emiss_dict.items():
        if any(v != 0 for v in values.values()):
            emission_pattern = values
            source_compartment = compartment
            break

    # Generate new dictionaries moving emission to each dispersing compartment and run the model

    for dispersing_comp in dispersing_comp_list:
        new_dict = copy.deepcopy(base_emiss_dict)

        # Clear all emissions
        for comp in new_dict:
            for k in new_dict[comp]:
                new_dict[comp][k] = 0

        # Apply the emission pattern to the target compartment
        new_dict[dispersing_comp] = copy.deepcopy(emission_pattern)

        # Create a copy of the model and asign the new emissions dictionary
        new_model_json = copy.deepcopy(model_json)
        new_model_json["emiss_dict_g_s"] = new_dict
        # run the new model objet to use new results

        model_json_collection = db["model_json"]
        if '_id' in new_model_json:
            del new_model_json['_id']
        inserted_new_model_json = model_json_collection.insert_one(new_model_json)
        new_model_id = inserted_new_model_json.inserted_id

        #把new_model_json 也插入 mongodb，得到新的 new_model_id
        #new_model_id = "new_model_id_placeholder"
        
        (R, PartMass_t0, input_flows_g_s, input_flows_num_s,_) = run_json(new_model_json)
        
        result_collection = db['result']
        flow_collection = db['flow']

        
        result_collection.insert_one({
            'model_id': new_model_id,
            'result': R.to_dict('list'),
            'index': list(R.index)
        })

        new_result = result_collection.find_one({'model_id': new_model_id}) #NOTE 需要补充

        flow_doc = {
            'model_id': new_model_id,
            'input_flows_g_s': input_flows_g_s,
            'input_flows_num_s': input_flows_num_s
        }

        flow_collection.insert_one(flow_doc)


        # Process results
        #processor_new_model = ResultsProcessor(new_model)  # Pass model with results
        #processor_new_model.estimate_flows()
        #flow_new_model = {} #NOTE 需要补充
        flow_new_model = flow_collection.find_one({'model_id': new_model_id})

        estimate_flows_json(new_model_json, flow_new_model)
        generate_flows_dict_json(new_model_json, flow_new_model)
        process_results_json(new_model_json, new_result, flow_new_model) # 返回更新后的new_result

        model_results[dispersing_comp] = {
            "Results_extended": new_result["Results_extended"],
            "tables_outputFlows": flow_new_model["tables_outputFlows_mass"],
            "tables_outputFlows_number": flow_new_model["tables_outputFlows_number"],
            "tables_inputFlows": flow_new_model["tables_inputFlows_mass"],
            "tables_inputFlows_num": flow_new_model["tables_inputFlows_number"],
        }

    # Estimate emission fractions for the setted emission scenario
    emission_fractions_mass_data = emission_fractions_calculations_json(
        new_result, new_model_json,model_results
    )
    emiss_comp = []
    # 此处需要检查是 model_json还是new_model_json
    for compartment, size_fractions in model_json["emiss_dict_g_s"].items():
        for fraction, value in size_fractions.items():
            if value > 0:
                emiss_comp.append(compartment)

    fig = plot_emission_fractions(emission_fractions_mass_data, emiss_comp)

    return (emission_fractions_mass_data, fig)

    ###Continue here. I need an etry for emiss comp and to add the function missing above

    # plot_emission_fractions(emission_fractions_mass_data,emiss_comp)
