"""Functions to check the mass balance of the model"""


def massBalance_json(model_json, R_document,flow_document):
    # Estimate looses: loss processess=[discorporation, burial]
    # Lossess also from fragmentation of the smallest size bin
    # k_soil_convection is only a loss process when coming from the deeper soil compartments and I need to take the second value of the list.,"k_soil_convection"
    loss_processess = ["k_discorporation", "k_burial", "k_sequestration_deep_soils"]
    elimination_rates = []

    # Estimate outflows

    for p in model_json["system_particle_object_list"]:

        if p["Pcode"][0] == "a":
            elimination_rates.append(
                sum(
                    [
                        p["RateConstants"][e]
                        for e in loss_processess
                        if e in p["RateConstants"]
                    ]
                )
                + sum(p["RateConstants"]["k_fragmentation"])
            )
        else:
            elimination_rates.append(
                sum(
                    [
                        p["RateConstants"][e]
                        for e in loss_processess
                        if e in p["RateConstants"]
                    ]
                )
            )
    # 🏗️🚧
    # 这里需要改 因为准备把R存放到一个单独的数据库中，根据model_json 的ID来获取
    # mass at Steady state
    m_ss = R_document["result"]["mass_g"]
    # 前提是 input_flows_g_S 是存放在model_json中的

    # output flow
    
    out_flow_g_s = sum(e * m for e, m in zip(elimination_rates, m_ss))

    in_flow_g_s = list(flow_document["input_flows_g_s"].values())

    difference_inf_outf = str(sum(in_flow_g_s) - out_flow_g_s)
    print("Difference inflow-outflow = " + difference_inf_outf)
    return difference_inf_outf


def compartment_massBalance(
    comp,
    tables_outputFlows,
    PartMass_t0,
    comp_dict_inverse,
    dict_comp,
    tables_inputFlows,
):
    loss_processess = ["k_discorporation", "k_burial", "k_sequestration_deep_soils"]

    # fragmentation is a loss process only for the smallest size bin (a=0.5nm)

    transfer_processes = [
        "k_advective_transport",
        "k_rising",
        "k_settling",
        "k_sea_spray_aerosol",
        "k_sediment_resuspension",
        "k_runoff_transport",
        "k_percolation",
        "k_tillage",
        "k_soil_air_resuspension",
        "k_wind_trasport",
        "k_dry_deposition",
        "k_wet_deposition",
        "k_mixing",
        "k_beaching",
        "k_soil_convection",
    ]
    comp_loss_processess = loss_processess + transfer_processes

    outputs_frag = sum(
        [
            sum(val)
            for i, val in zip(
                tables_outputFlows[comp].index[0],
                tables_outputFlows[comp]["k_fragmentation"],
            )
            if i == 0.5
        ]
    )
    # output flow from fragmentation should be == 0 as we account fragemntation of the smallest size fraction as dissintegration
    if outputs_frag != 0:
        print("Error: fragmentation of smallest size bin not zero")

    output_flows = tables_outputFlows[comp]
    # output_flows = output_flows.drop(["MP_size", "MP_form"], axis=1)

    ##Take into account for dry deposition and wet deposition the sum of all output flows

    for proc in output_flows:
        output_flows[proc] = output_flows[proc].apply(
            lambda x: sum(x) if isinstance(x, list) else x
        )

    output_flows_sum = output_flows.sum()

    out_flow_comp_g_s = sum(
        [
            val
            for proc, val in zip(output_flows_sum.index, output_flows_sum)
            if proc in comp_loss_processess
        ]
    )

    # input flow
    # Emissions
    for i, s in zip(PartMass_t0.index, PartMass_t0.values):
        if sum(s) != 0:
            if comp_dict_inverse[float(i[2:-7])] == comp:
                emiss_flow_g_s = -sum(s)
            else:
                emiss_flow_g_s = 0

    transport_input_flow = sum(tables_inputFlows[comp].sum())
    # transport_input_flow = sum(
    #     tables_inputFlows[comp].drop(["MP_size", "MP_form"], axis=1).sum()
    # )

    # Mass balance per compartment
    # print(
    #     "Difference inflow-outflow in "
    #     + comp
    #     + " is = "
    #     + str(emiss_flow_g_s + transport_input_flow - out_flow_comp_g_s - outputs_frag)
    # )
    return {
        "Inflow": emiss_flow_g_s + transport_input_flow,
        "Outflow": out_flow_comp_g_s + outputs_frag,
    }
