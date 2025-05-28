# The study titled "Quantification of the Emission of Atmospheric Microplastics and Nanoplastics via Sea Spray" investigates how micro- and nanoplastics (MNPs) are aerosolized from ocean water through sea spray, focusing on the influence of particle size, density, and concentration. ​
# ACS Publications: https://pubs.acs.org/doi/full/10.1021/acs.estlett.3c00164
# Charbel Harb, Nishan Pokhrel, and Hosein Foroutan
# Environmental Science & Technology Letters 2023 10 (6), 513-519
# DOI: 10.1021/acs.estlett.3c00164

# Key Findings:

# Particle Size:
# The study observed that MNPs with diameters ≤10 μm can be emitted via bubble bursting.​
# Aerosolization efficiency decreases as particle size increases within this range.​

# Particle Density:
# Polystyrene (density ≈ 1,050 kg/m³) particles dispersed in bulk water showed higher aerosolization efficiency compared to polyethylene (density ≈ 920 kg/m³) particles, which tend to float.​
# This suggests that MNPs suspended in the water column are more likely to be aerosolized than those floating on the surface.​

# Particle Concentration:
# Aerosolization increases monotonically with higher MNP concentrations in water

# From the data provided in the paper, we can derive the following equations for aerosolization flux and rate constant where we consider the particle density as a factor.
# The equations are based on the findings of the study and incorporate the effects of wind speed, particle size, density, and concentration.:
from scipy.stats import linregress
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def emission_factor(dp_um):
    """
    Computes the emission factor (E_f) based on particle diameter (dp) in micrometers. After fitting a power law distribution to empirical data.

    Parameters:

        E_f_size_dict: dict
            A dictionary containing the particle diameter (dp) in micrometers (dp_um) as the key and the corresponding emission factor (E_f) as the value.
        dp_um : float or array-like
            Particle diameter in micrometers (µm)

    Returns:
        E_f : float or array-like
            Emission factor in m³ m⁻² s⁻¹
    """

    E_f_size_dict = {"Size": [0.5, 2, 10], "E_f": [2.20e-08, 2.56e-08, 3.28e-10]}

    df = pd.DataFrame(E_f_size_dict)

    # Log-Transform Data
    log_size = np.log(df["Size"])
    log_Ef = np.log(df["E_f"])

    # Linear Regression in Log-Log Space (Power-Law Fit)
    slope, intercept, r_value, p_value, std_err = linregress(log_size, log_Ef)

    # Convert to Power-Law Form: E_f = k * (Size)^alpha
    alpha = slope
    k = np.exp(intercept)
    R_squared = r_value**2  # Goodness-of-fit

    print(f"Power-Law Relationship: E_f = {k:.5e} * Size^{alpha:.3f}")
    print(f"R-squared: {R_squared:.3f}")

    # Calculate E_f for given dp_um
    return k * dp_um**-alpha  # E_f in m³ m⁻² s⁻¹


def settling_velocity(d_p, rho_p, rho_w=1000, mu=1.002e-3, g=9.81):
    """
    Compute the Stokes settling velocity for a particle in water.

    Parameters:
    d_p   : Particle diameter (m)
    rho_p : Particle density (kg/m³)
    rho_w : Water density (kg/m³) (default = 1000)
    mu    : Dynamic viscosity of water (Pa·s) (default = 1.002e-3)
    g     : Gravitational acceleration (m/s²) (default = 9.81)

    Returns:
    v_s   : Settling velocity (m/s)
    """
    return (g * d_p**2 * (rho_p - rho_w)) / (18 * mu)


def aerosolization_flux(U10, C, d_p, rho_p, E_f_base):
    """
    Compute the aerosolization flux incorporating particle density.

    Parameters:
    U10       : Wind speed at 10 m height (m/s)
    C         : MNP concentration in water (m⁻³)
    d_p       : Particle diameter (m)
    rho_p     : Particle density (kg/m³)
    E_f_base  : Baseline emission factor (m³ m⁻² s⁻¹) from the paper

    Returns:
    F         : Aerosolization flux (m⁻² s⁻¹)
    """
    # Compute settling velocity
    v_s = settling_velocity(d_p, rho_p)

    # Normalize E_f by a density correction factor
    v_s_ref = settling_velocity(2e-6, 1050)  # Reference: 2 µm PS (ρ ≈ 1050 kg/m³)
    density_factor = v_s_ref / v_s  # Higher v_s → lower resuspension

    # Adjusted emission factor
    E_f_mod = E_f_base * abs(density_factor)

    # Compute flux using the modified E_f
    F = (3.84e-6 * U10**3.41) * (E_f_mod * C)

    return F


def aerosolization_rate_constant(U10, C, d_p, rho_p, A_w, h):
    """
    Computes the first-order aerosolization rate constant k_a.

    Parameters:
    U10       : Wind speed at 10 m height (m/s)
    C         : MNP concentration in water (m⁻³)
    d_p       : Particle diameter (m)
    rho_p     : Particle density (kg/m³)
    E_f_base  : Baseline emission factor (m³ m⁻² s⁻¹)
    A_w       : Surface area of the water compartment (m²)
    h         : Depth of the water compartment (m)

    Returns:
    k_a       : Aerosolization rate constant (s⁻¹)
    """

    # Compute emission factor
    E_f_base = emission_factor(
        d_p * 1e6
    )  # Convert diameter to micrometers for the function

    # Compute aerosolization flux
    F = aerosolization_flux(U10, C, d_p, rho_p, E_f_base)

    # Compute rate constant
    k_a = F / (C * h)

    return k_a


# Example parameters
A_w = 1e6  # Water surface area (m²)
h = 10  # Depth of the surface water compartment (m)

U10 = 5  # Wind speed (m/s)
C = 1e6  # MNP concentration in water (m⁻³)
d_p = 1e-6  # Particle diameter (1 µm in meters)
rho_p = 900  # Particle density (e.g., PE ~900 kg/m³)
# E_f_base = 2.56e-8  # Emission factor for 2 µm PS

# Compute aerosolization rate constant
k_a = aerosolization_rate_constant(U10, C, d_p, rho_p, A_w, h)
print(f"Aerosolization Rate Constant: {k_a:.2e} s⁻¹")
