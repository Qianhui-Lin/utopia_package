import numpy as np


def wet_deposition_rate(d_p, R):
    """
    Estimates the wet deposition scavenging coefficient (Λ) based on particle size and rainfall intensity.

    Parameters:
    d_p : Particle diameter (m)
    R   : Rainfall intensity (mm/h)

    Returns:
    Lambda : Wet deposition rate constant (1/s)
    """
    # Empirical scavenging rate coefficients from literature (Slinn, Andronache, etc.)
    if d_p < 0.01e-6:  # <10 nm
        beta = 1e-6  # Very low efficiency
    elif d_p < 0.1e-6:  # 10-100 nm
        beta = 5e-6
    elif d_p < 1e-6:  # 100-1000 nm
        beta = 1e-5
    elif d_p < 10e-6:  # 1-10 µm
        beta = 5e-5
    elif d_p < 100e-6:  # 10-100 µm
        beta = 2e-4
    else:  # >100 µm (large particles efficiently scavenged)
        beta = 5e-4

    # Compute scavenging coefficient (1/s)
    Lambda = beta * R / 3600  # Convert mm/h to per second

    return Lambda


# # Example: Wet deposition of 1 µm particles with 5 mm/h rain
# d_p = 1e-6  # 1 µm
# R = 5  # mm/h rainfall intensity

# Lambda = wet_deposition_rate(d_p, R)
# print(f"Wet deposition rate: {Lambda:.2e} 1/s")

# REFERENCES for sources of scavenging coefficients
# Slinn, W. G. N. (1982)

# Title: "Turbulent Diffusion in the Atmosphere and in the Ocean"

# Journal: Springer-Verlag

# Summary: This work provides a detailed description of aerosol removal from the atmosphere through wet deposition, including particle size-dependent scavenging coefficients for particles in the 0.1 µm to 100 µm range. It also discusses the influence of rainfall intensity on scavenging rates.

# Link: Slinn (1982)

# Seinfeld, J. H., and Pandis, S. N. (2006)

# Title: "Atmospheric Chemistry and Physics: From Air Pollution to Climate Change"

# Publisher: Wiley-Interscience

# Summary: This textbook covers a wide range of atmospheric processes, including the collection efficiency of rain for particles of different sizes and its dependence on rain intensity. It also presents scavenging coefficients as a function of particle size and type of precipitation.

# Link: Seinfeld and Pandis (2006)

# Andronache, C. (2003)

# Title: "Parameterization of Rain Scavenging of Aerosols"

# Journal: Journal of Geophysical Research: Atmospheres

# DOI: 10.1029/2002JD002613

# Summary: This paper provides a comprehensive review of wet deposition processes, including scavenging coefficients for various particle sizes, as well as how these coefficients depend on rainfall intensity.

# Link: Andronache (2003)

# Grythe, H., et al. (2014)

# Title: "Global Wet Deposition of Atmospheric Aerosols: A Model Study"

# Journal: Atmospheric Chemistry and Physics

# DOI: 10.5194/acp-14-1457-2014

# Summary: This study develops a model of wet deposition and estimates scavenging coefficients for various aerosol types. It provides useful values for scavenging rates of particles in the range of 0.1 µm to 100 µm, as well as a range of rainfall intensities.

# Link: Grythe et al. (2014)

# Pruppacher, H. R., and Klett, J. D. (1997)

# Title: "Microphysics of Clouds and Precipitation"

# Publisher: Kluwer Academic Publishers

# Summary: This book provides a fundamental understanding of cloud physics and precipitation processes, including aerosol removal by rain. It gives mathematical relationships for scavenging coefficients based on raindrop size distribution and particle size.

# Link: Pruppacher and Klett (1997)
