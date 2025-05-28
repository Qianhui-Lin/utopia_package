import pandas as pd
import numpy as np


def Exposure_indicators_calculation(model):
    #### EXPOSURE INDICATORS ####
    # When estimating the overall exposure indicators we do not take on account the Column Water and Ocean Sediment compartments. This is to mantain consistency with the OECD tool as there the particles going deeper than 100 m into the ocean are considered lossess, therefore we also use that as a boundary in our system. Also in this way we prevent the ocean sediment and column water from driving the POV and residence times values. However our emission fraction estimates do take this compartmets into consideration and the MPs fate into the whole UTOPIA system is reflected there.

    """Overall persistance (years)"""

    # From the OECD tool (REF: Wegmann et al, 2009. https://doi.org/10.1016/j.envsoft.2008.06.014) Overall persistence (POV, days) is a measure of the time scale of degradation of the chemical in the whole environment. For each mode of emission i, it is calculated by dividing the total mass at steady-state (Mi,TOT, kg) by the sum of all degradation mass fluxes in air (A), water (W) and soil (S) ((FDEG,i,A + FDEG,i,W + FDEG,i,S), kg/h)

    # Overall persistance for the plastic material in all size classes and table of overall persistance per compartment:

    # Overall mass persistence

    discorporation_flows = []
    discorporation_flows_all = []
    for k in model.tables_outputFlows_mass:
        discorporation_flows_all.append(
            sum(model.tables_outputFlows_mass[k].k_discorporation)
        )
        if k != "Ocean_Column_Water" and k != "Sediment_Ocean":
            discorporation_flows.append(
                sum(model.tables_outputFlows_mass[k].k_discorporation)
            )

    # remove ocean column water and ocean sediment results
    comp_outBoundares = ["Ocean_Column_Water", "Sediment_Ocean"]
    Results_extended_EI = model.Results_extended[
        ~model.Results_extended["Compartment"].isin(comp_outBoundares)
    ]

    Pov_mass_sec = sum(Results_extended_EI["mass_g"]) / sum(discorporation_flows)

    Pov_mass_days = Pov_mass_sec / 86400
    Pov_mass_years = Pov_mass_days / 365

    print_output = "False"

    if print_output == "True":
        print("Overall mass persistence (years): " + str(int(Pov_mass_years)))
    else:
        pass

    # Table of overall mass persistences per compartment
    Pov_comp_years = []
    for c in model.tables_outputFlows_mass.keys():
        if (
            sum(
                model.Results_extended[model.Results_extended["Compartment"] == c][
                    "mass_g"
                ]
            )
            == 0
        ):
            Pov_comp_years.append(
                "NaN"
            )  # When there is no mass in the compartment Pov has no value (marked as NAN)
        else:
            Pov_comp_years.append(
                (
                    sum(
                        model.Results_extended[
                            model.Results_extended["Compartment"] == c
                        ]["mass_g"]
                    )
                    / sum(model.tables_outputFlows_mass[c].k_discorporation)
                )
                / 86400
                / 365
            )

    Pov_Tov_comp_df = pd.DataFrame(
        {
            "Compartment": model.tables_outputFlows_mass.keys(),
            "Pov_years(mass)": Pov_comp_years,
        }
    )

    # Overall number persistence

    discorporation_flows_num = []
    discorporation_flows_num_all = []
    for k in model.tables_outputFlows_number:
        discorporation_flows_num_all.append(
            sum(model.tables_outputFlows_number[k].k_discorporation)
        )
        if k != "Ocean_Column_Water" and k != "Sediment_Ocean":
            discorporation_flows_num.append(
                sum(model.tables_outputFlows_number[k].k_discorporation)
            )

    Pov_num_sec = sum(Results_extended_EI["number_of_particles"]) / sum(
        discorporation_flows_num
    )

    Pov_num_days = Pov_num_sec / 86400
    Pov_num_years = Pov_num_days / 365

    if print_output == "True":
        print("Overall particle number persistence (years): " + str(int(Pov_num_years)))
    else:
        pass

    # Table of discorporation flows per compartment in number
    Pov_comp_years_num = []
    for c in model.tables_outputFlows_number.keys():
        if (
            sum(
                model.Results_extended[model.Results_extended["Compartment"] == c][
                    "number_of_particles"
                ]
            )
            == 0
        ):
            Pov_comp_years_num.append(
                "NaN"
            )  # When there is no number in the compartment Pov has no value (marked as NAN)
        else:
            Pov_comp_years_num.append(
                sum(
                    model.Results_extended[model.Results_extended["Compartment"] == c][
                        "number_of_particles"
                    ]
                )
                / sum(model.tables_outputFlows_number[c].k_discorporation)
                / 86400
                / 365
            )

    Pov_Tov_comp_df["Pov_years(particle_number)"] = Pov_comp_years_num

    # Overall persistence specific to each size class are mass and number independent:

    # NOTE! When the mass is only present in one size fraction then the Pov has to be equal to the overall Pov and mas and number Pov should be the same

    size_list = ["a", "b", "c", "d", "e"]
    Pov_size_dict_years = {}
    for size in size_list:
        discorporation_fargmentation_flows = []
        for k in model.tables_outputFlows_mass:
            if k != "Ocean_Column_Water" and k != "Sediment_Ocean":
                outputFlow_df = model.tables_outputFlows_mass[k]
                sliced_df = outputFlow_df[outputFlow_df.index.str[0] == size]
                discorporation_fargmentation_flows.append(
                    sum(
                        [
                            ele if type(ele) != list else sum(ele)
                            for ele in sliced_df.k_fragmentation
                        ]
                    )
                    + sum(sliced_df.k_discorporation)
                )

        mass_sizeFraction = sum(
            Results_extended_EI[Results_extended_EI.index.str[0] == size].mass_g
        )
        if (
            mass_sizeFraction == 0
        ):  ## If there are no particles of a specific size fraction in the system one does not need to estimate Pov
            Pov_size_dict_years[model.model.size_dict[size]] = "NaN"
            continue

        Pov_size_sec = mass_sizeFraction / sum(discorporation_fargmentation_flows)
        Pov_size_days = Pov_size_sec / 86400
        Pov_size_years = Pov_size_days / 365
        # print(
        #     "Overall persistence of size "
        #     + str(size_dict[size])
        #     + " um (years): "
        #     + str(int(Pov_size_years))
        # )
        Pov_size_dict_years[model.model.size_dict[size]] = Pov_size_years

    """ Overall residence time (years)"""
    # With the new system boundaries we acount for sequestration in deep soils and burial into coast and freshwater sediment but for the Ocean sediment we do not take burial but the settling into the ocean column water compartment as well as mixing. (We exclude the Ocean column water and ocean sediment from the system boundaries in these calculations)

    # from The OECD Tool (REF: ) the overall residence time in a multimedia environment (h), is the ratio of the total mass at steady-state for the given mode of emission (Mi,TOT, kg) divided by the emission mass flux, Fi,E, that enters medium i.

    # However here we are estimating residence time as the mass at steady state divided by the sum of the fluxes of disintegration and advection out of the system (in this case thorugh settling into the ocean column watter as well as burial and sequestration into the soil and deep sediment compartments) ut also weigthed out by the resuspension and mixing from ocean column water.

    systemloss_flows_mass = []
    systemloss_flows_number = []

    for k in model.tables_outputFlows_mass:
        if k in ["Beaches_Deep_Soil", "Background_Soil", "Impacted_Soil"]:
            systemloss_flows_mass.append(
                sum(model.tables_outputFlows_mass[k].k_discorporation)
                + sum(model.tables_outputFlows_mass[k].k_sequestration_deep_soils)
            )
        if k in ["Sediment_Freshwater", "Sediment_Coast"]:
            systemloss_flows_mass.append(
                sum(model.tables_outputFlows_mass[k].k_discorporation)
                + sum(model.tables_outputFlows_mass[k].k_burial)
            )
            systemloss_flows_number.append(
                sum(model.tables_outputFlows_number[k].k_discorporation)
                + sum(model.tables_outputFlows_number[k].k_burial)
            )
        elif k == "Ocean_Mixed_Water":
            # Calculate net flow lossess from the Ocean Midex water compartment through deep ocean
            flow_mix_down_mass = []
            flow_mix_down_number = []
            flow_mix_up_mass = []
            flow_mix_up_number = []
            flow_rising_mass = []
            flow_rising_number = []
            for p in model.model.system_particle_object_list:
                if p.Pcompartment.Cname == "Ocean_Mixed_Water":
                    flow_mix_down_mass.append(
                        p.RateConstants["k_mixing"][1] * p.Pmass_g_SS
                    )
                    flow_mix_down_number.append(
                        p.RateConstants["k_mixing"][1] * p.Pnum_SS
                    )
                elif p.Pcompartment.Cname == "Ocean_Column_Water":
                    flow_mix_up_mass.append(p.RateConstants["k_mixing"] * p.Pmass_g_SS)
                    flow_mix_up_number.append(p.RateConstants["k_mixing"] * p.Pnum_SS)
                    flow_rising_mass.append(p.RateConstants["k_rising"] * p.Pmass_g_SS)
                    flow_rising_number.append(p.RateConstants["k_rising"] * p.Pnum_SS)

            systemloss_flows_mass.append(
                sum(model.tables_outputFlows_mass[k].k_discorporation)
                + sum(model.tables_outputFlows_mass[k].k_settling)
                + sum(flow_mix_down_mass)
                - sum(flow_mix_up_mass)
                - sum(flow_rising_mass)
            )
            systemloss_flows_number.append(
                sum(model.tables_outputFlows_number[k].k_discorporation)
                + sum(model.tables_outputFlows_number[k].k_settling)
                + sum(flow_mix_down_number)
                - sum(flow_mix_up_number)
                - sum(flow_rising_number)
            )

        elif k != "Ocean_Column_Water" and k != "Sediment_Ocean":
            systemloss_flows_mass.append(
                sum(model.tables_outputFlows_mass[k].k_discorporation)
            )
            systemloss_flows_number.append(
                sum(model.tables_outputFlows_number[k].k_discorporation)
            )
        else:
            pass

    Tov_mass_sec = sum(Results_extended_EI["mass_g"]) / sum(systemloss_flows_mass)
    Tov_num_sec = sum(Results_extended_EI["number_of_particles"]) / sum(
        systemloss_flows_number
    )

    Tov_mass_days = Tov_mass_sec / 86400
    Tov_num_days = Tov_num_sec / 86400
    Tov_mass_years = Tov_mass_days / 365
    Tov_num_years = Tov_num_days / 365

    if print_output == "True":
        print(
            "Overall residence time is calculated assuming the model boundaries to be at 100 m depth into the Ocean, 30 cm into the sediments and 0.1 m into the soil. Particles travelling deeper are considered losses"
        )

        print("Overall mass residence time (years): " + str(round(Tov_mass_years, 1)))

        print(
            "Overall particle number residence time (years): "
            + str(round(Tov_num_years, 1))
        )
    else:
        pass

    # Residence time especific to each compartment following the definition by Wegmann et al, 2009.:
    # Residence time Tov in a multimedia environment (h), is the ratio of the total mass at steady-state for the given mode of emission (Mi,TOT, kg) divided by the emission mass flux, Fi,E, that enters medium i.

    Tov_comp_mass_years = []
    Tov_comp_number_years = []
    for c, cn in zip(
        model.tables_outputFlows_mass.keys(),
        range(len(model.tables_outputFlows_mass.keys())),
    ):
        direct_emiss = sum(list(model.model.emiss_dict_g_s[c].values()))
        Tov_comp_mass_years.append(
            sum(
                model.Results_extended[model.Results_extended["Compartment"] == c][
                    "mass_g"
                ]
            )
            / (
                direct_emiss
                + sum(
                    sum(val) if isinstance(val, (list, np.ndarray)) else val
                    for x in model.tables_outputFlows_mass[c].columns
                    for val in model.tables_outputFlows_mass[c][x]
                )
            )
            / 60
            / 60
            / 24
            / 365
        )

        Tov_comp_number_years.append(
            sum(
                model.Results_extended[model.Results_extended["Compartment"] == c][
                    "number_of_particles"
                ]
            )
            / sum(
                [
                    sum(model.tables_inputFlows_number[c][x])
                    for x in model.tables_inputFlows_number[c].keys()
                ]
            )
            / 60
            / 60
            / 24
            / 365
        )

    Pov_Tov_comp_df["Tov_years(mass_g)"] = Tov_comp_mass_years
    Pov_Tov_comp_df["Tov_years(particle_number)"] = Tov_comp_number_years

    # NOTE: When only one size class pressent, should the residence time be the same in particle number and in mass?? !!! TO check!!!

    # Overall residence time specific to each size class (mass and number independent):

    Tov_size_dict_years = {}
    for size in size_list:

        mass_sizeFraction = sum(
            Results_extended_EI[Results_extended_EI.index.str[0] == size].mass_g
        )

        if mass_sizeFraction == 0:
            Tov_size_dict_years[model.model.size_dict[size]] = "NaN"
            continue

        systemloss_flows_size = []
        for k in model.tables_outputFlows_mass:
            outputFlow_df = model.tables_outputFlows_mass[k]
            sliced_df = outputFlow_df[outputFlow_df.index.str[0] == size]
            if k in ["Beaches_Deep_Soil", "Background_Soil", "Impacted_Soil"]:
                systemloss_flows_size.append(
                    sum(
                        [
                            ele if type(ele) != list else sum(ele)
                            for ele in sliced_df.k_fragmentation
                        ]
                    )
                    + sum(sliced_df.k_discorporation)
                    + sum(sliced_df.k_sequestration_deep_soils)
                )
            elif k in ["Sediment_Freshwater", "Sediment_Coast"]:
                systemloss_flows_size.append(
                    sum(
                        [
                            ele if type(ele) != list else sum(ele)
                            for ele in sliced_df.k_fragmentation
                        ]
                    )
                    + sum(sliced_df.k_discorporation)
                    + sum(sliced_df.k_burial)
                )
            elif k == "Ocean_Mixed_Water":
                # Calculate net flow lossess from the Ocean Midex water compartment through deep ocean
                flow_mix_down = []
                flow_mix_up = []
                flow_rising = []
                for p in model.model.system_particle_object_list:
                    if p.Pcode[0] == size:
                        if p.Pcompartment.Cname == "Ocean_Mixed_Water":
                            flow_mix_down.append(
                                p.RateConstants["k_mixing"][1] * p.Pmass_g_SS
                            )
                        elif p.Pcompartment.Cname == "Ocean_Column_Water":
                            flow_mix_up.append(
                                p.RateConstants["k_mixing"] * p.Pmass_g_SS
                            )
                            flow_rising.append(
                                p.RateConstants["k_rising"] * p.Pmass_g_SS
                            )

                systemloss_flows_size.append(
                    sum(
                        [
                            ele if type(ele) != list else sum(ele)
                            for ele in sliced_df.k_fragmentation
                        ]
                    )
                    + sum(sliced_df.k_discorporation)
                    + sum(sliced_df.k_settling)
                    + sum(flow_mix_down)
                    - sum(flow_mix_up)
                    - sum(flow_rising)
                )

            elif k != "Ocean_Column_Water" and k != "Sediment_Ocean":
                systemloss_flows_size.append(
                    sum(
                        [
                            ele if type(ele) != list else sum(ele)
                            for ele in sliced_df.k_fragmentation
                        ]
                    )
                    + sum(sliced_df.k_discorporation)
                )

            else:
                pass

        Tov_size_sec = mass_sizeFraction / sum(systemloss_flows_size)
        Tov_size_days = Tov_size_sec / 86400
        Tov_size_years = Tov_size_days / 365

        if print_output == "True":
            print(
                "Overall residence time of size "
                + str(model.model.size_dict[size])
                + " um (years): "
                + str(round(Tov_size_years, 2))
            )
        else:
            pass

        Tov_size_dict_years[model.model.size_dict[size]] = Tov_size_years

    # model.Pov_mass_years = Pov_mass_years
    # model.Pov_num_years = Pov_num_years
    # model.Tov_mass_years = Tov_mass_years
    # model.Tov_num_years = Tov_num_years
    # model.Pov_size_dict_years = Pov_size_dict_years
    # model.Tov_size_dict_years = Tov_size_dict_years
    # model.Pov_Tov_comp_df = Pov_Tov_comp_df

    # Build table of overall exposure indicators
    overall_exposure_indicators = pd.DataFrame(
        {
            "Overall exposure indicators": ["Mass", "Number"],
            "Overall persistence (years)": [Pov_mass_years, Pov_num_years],
            "Overall residence time (years)": [Tov_mass_years, Tov_num_years],
        }
    )

    ## Build table of size fraction indicators
    size_fraction_indicators = pd.DataFrame(
        Pov_size_dict_years.items(), columns=["Size (um)", "Pov (years)"]
    )
    size_fraction_indicators["Tov (years)"] = Tov_size_dict_years.values()

    # model.overall_exposure_indicators = overall_exposure_indicators
    # model.size_fraction_indicators = size_fraction_indicators
    return (overall_exposure_indicators, size_fraction_indicators)
    # return (
    #     Pov_mass_years,
    #     Pov_num_years,
    #     Pov_size_dict_years,
    #     Tov_mass_years,
    #     Tov_num_years,
    #     Tov_size_dict_years,
    #     Pov_Tov_comp_df,
    # )
