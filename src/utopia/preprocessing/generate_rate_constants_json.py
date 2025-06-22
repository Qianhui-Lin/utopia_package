# import utopia.preprocessing.RC_generator as RC_generator
import utopia.preprocessing.RC_generator_json as RC_generator

'''
def generate_rate_constants(model):
    """Generates rate constants for all processes for each particle in the system."""
    for particle in model.system_particle_object_list:
        particle.RateConstants = dict.fromkeys(
            ["k_" + p for p in particle.Pcompartment.processess]
        )
        for process in particle.RateConstants:
            proc = process[2:]
            particle.RateConstants[process] = getattr(RC_generator, proc)(
                particle, model
            )

    return model
'''
def generate_rate_constants_json(model_json):
    dict_comp = model_json["dict_comp"]
    for particle in model_json["system_particle_object_list"]:
        compartment = get_compartment_for_particle(particle, dict_comp)
        processes = compartment["processess"]
        particle["RateConstants"] = dict.fromkeys([f'k_{p}' for p in processes])
        for process in particle["RateConstants"]:
            proc = process[2:]
            particle["RateConstants"][process] = getattr(RC_generator, proc)(
                particle, model_json
            )
    return model_json


# 在这里是根据particle的Pcompartment_Cname 从 dict_comp 提取 compartment dict 
# 注意一致性。。。。
def get_compartment_for_particle(particle, dict_comp):
    """
    Returns the compartment dictionary from dict_comp corresponding to the particle's Pcompartment_Cname.
    """
    cname = particle.get("Pcompartment_Cname")
    if cname is None:
        raise KeyError("Particle does not have 'Pcompartment_Cname'")
    if cname not in dict_comp:
        raise KeyError(f"Compartment name '{cname}' not found in dict_comp")
    return dict_comp[cname]
