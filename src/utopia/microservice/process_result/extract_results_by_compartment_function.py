from utopia.helpers import *

def extract_results_by_compartment_json(processed_results,model_json,flow_estimation):
        if processed_results["processed_result"] is None:
            raise ValueError(
                "Mass and particle number fractions not extracted. Call process_results() first."
            )
        
        df = pd.DataFrame(processed_results["processed_result"])

        mass_g = []
        particle_number = []
        mass_frac_100 = []
        num_frac_100 = []
        mass_conc_g_m3 = []
        num_conc = []
        for comp in list(model_json["dict_comp"].keys()):
            comp_df = df[df["Compartment"] == comp]

            mass_g.append(comp_df["mass_g"].sum())
            particle_number.append(comp_df["number_of_particles"].sum())
            mass_frac_100.append(comp_df["mass_fraction"].sum() * 100)
            num_frac_100.append(comp_df["number_fraction"].sum() * 100)
            mass_conc_g_m3.append(comp_df["concentration_g_m3"].sum())
            num_conc.append(comp_df["concentration_num_m3"].sum())
            


        results_by_comp = pd.DataFrame(columns=["Compartments"])
        results_by_comp["Compartments"] = list(model_json["dict_comp"].keys())
        results_by_comp["mass_g"] = mass_g
        results_by_comp["number_of_particles"] = particle_number
        results_by_comp["%_mass"] = mass_frac_100
        results_by_comp["%_number"] = num_frac_100
        results_by_comp["Concentration_g_m3"] = mass_conc_g_m3
        results_by_comp["Concentration_num_m3"] = num_conc

        # self.results_by_comp = results_by_comp
        # return results_by_comp
        """Calculate inflows and outflows (mass and number) by compartment and update results_by_comp."""
        inflows_mass_list = []
        inflows_num_list = []
        outflows_mass_list = []
        outflows_num_list = []

        for n in range(len(results_by_comp)):
            compartment = results_by_comp.iloc[n]["Compartments"]

            # Calculate inflows and outflows for mass
            inflows_mass = process_flows_comp_json(
                compartment, "input_flows", flow_estimation["flows_dict_mass"]
            )
            outflows_mass = process_flows_comp_json(
                compartment, "output_flows", flow_estimation["flows_dict_mass"]
            )
            inflows_mass_list.append(inflows_mass)
            outflows_mass_list.append(outflows_mass)

            # Calculate inflows and outflows for number
            inflows_num = process_flows_comp_json(
                compartment, "input_flows", flow_estimation["flows_dict_number"]
            )
            outflows_num = process_flows_comp_json(
                compartment, "output_flows", flow_estimation["flows_dict_number"]
            )
            inflows_num_list.append(inflows_num)
            outflows_num_list.append(outflows_num)

        # Update the Results_extended DataFrame with the calculated flows
        results_by_comp["inflows_g_s"] = inflows_mass_list
        results_by_comp["inflows_num_s"] = inflows_num_list
        results_by_comp["outflows_g_s"] = outflows_mass_list
        results_by_comp["outflows_num_s"] = outflows_num_list
        results_by_comp["Total_inflows_g_s"] = [
            sum(results_by_comp.iloc[i].inflows_g_s.values())
            for i in range(len(results_by_comp))
        ]
        results_by_comp["Total_inflows_num_s"] = [
            sum(results_by_comp.iloc[i].inflows_num_s.values())
            for i in range(len(results_by_comp))
        ]
        results_by_comp["Total_outflows_g_s"] = [
            sum(results_by_comp.iloc[i].outflows_g_s.values())
            for i in range(len(results_by_comp))
        ]
        results_by_comp["Total_outflows_num_s"] = [
            sum(results_by_comp.iloc[i].outflows_num_s.values())
            for i in range(len(results_by_comp))
        ]

        processed_results["results_by_comp"] = results_by_comp
        #self.processed_results["results_by_comp"] = results_by_comp
        return results_by_comp