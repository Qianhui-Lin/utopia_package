import numpy as np
from scipy.stats import lognorm, uniform

def sample_param(distribution_name, params, n):
    if distribution_name == "lognorm":
        return lognorm.rvs(s=params["s"], scale=params["scale"], size=n)
    elif distribution_name == "uniform":
        return uniform.rvs(loc=params["loc"], scale=params["scale"], size=n)
    else:
        raise ValueError(f"Unknown distribution: {distribution_name}")

def generate_mc_samples(base_input: dict, param_distributions: dict, n_cases: int):
    """
    base_input: dict of the original input (your JSON)
    param_distributions: dict defining sample distributions
    n_cases: number of MC runs
    """
    sampled_inputs = []

    for i in range(n_cases):
        # deep copy of base input
        new_input = base_input.copy()

        # sample each parameter
        for param, (dist_name, dist_params) in param_distributions.items():
            new_input[param] = sample_param(dist_name, dist_params, 1)[0]

        sampled_inputs.append(new_input)

    return sampled_inputs
