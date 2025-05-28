import numpy as np


def generate_fsd_matrix(FI):
    # function to generate the FSD matrix (generates a fragemntation matrix based on the selected fragmentation style determined by FI)
    # Initialize a 5x5 matrix with zeros
    matrix = np.zeros((5, 5))
    c1 = 0.2
    c2 = 0.15
    c3 = 0.1

    matrix[1, 0] = 1
    matrix[2, 0] = 1 - FI
    matrix[2, 1] = FI
    if FI <= 0.5:
        matrix[3, 1] = FI * 2 * c1
        matrix[4, 1] = FI * 2 * c2
        matrix[4, 2] = FI * 2 * c3
    else:
        matrix[3, 1] = c1 - ((FI - 0.5) * 2 * c1)
        matrix[4, 1] = c2 - ((FI - 0.5) * 2 * c2)
        matrix[4, 2] = c3 - ((FI - 0.5) * 2 * c3)
    matrix[3, 0] = matrix[2, 0] + (0.5 * matrix[3, 1])
    matrix[3, 2] = 1 - matrix[3, 0] - matrix[3, 1]
    matrix[4, 0] = matrix[3, 0] + (0.5 * matrix[4, 1]) + (0.25 * matrix[4, 2])
    matrix[4, 3] = 1 - matrix[4, 0] - matrix[4, 1] - matrix[4, 2]

    return matrix


# function to convert mass to number
def mass_to_num(mass_g, volume_m3, density_kg_m3):
    number = mass_g / 1000 / density_kg_m3 / volume_m3
    # number of particles has always to be integer?
    return number


# function to convert number to mass
def num_to_mass(number, volume_m3, density_kg_m3):
    mass_g = number * volume_m3 * density_kg_m3 * 1000
    return mass_g


# Function to handle summing lists and individual elements
def handle_value(value):
    if isinstance(value, list):
        return sum(value)
    return value


def sum_column_values(column):
    return sum(handle_value(value) for value in column)


def process_flows(compartment, size_fraction, mp_form, flow_type, flows_dict):
    """Process flows (inflows or outflows) for a given compartment, size fraction, and MP form."""
    df_comp = flows_dict[flow_type][compartment]
    df_filtered = df_comp[
        (df_comp["MP_form"] == mp_form) & (df_comp["MP_size"] == size_fraction)
    ]
    df_cleaned = df_filtered.drop(["MP_size", "MP_form"], axis=1)
    return {col: sum_column_values(df_cleaned[col]) for col in df_cleaned.columns}


def process_flows_comp(compartment, flow_type, flows_dict):
    """Process flows (inflows or outflows) for a given compartment, this means the heteroaggregation and biofouling processess should not be included"""
    df_comp = flows_dict[flow_type][compartment]
    df_cleaned = df_comp.drop(["MP_size", "MP_form"], axis=1)

    # List of processess to not include:
    excluded_columns = [
        "k_heteroaggregation",
        "k_heteroaggregate_breackup",
        "k_biofouling",
        "k_defouling",
        "k_fragmentation",
    ]

    return {
        col: sum_column_values(df_cleaned[col])
        for col in df_cleaned.columns
        if col not in excluded_columns
    }
