import preprocessing.RC_generator as RC_generator


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
