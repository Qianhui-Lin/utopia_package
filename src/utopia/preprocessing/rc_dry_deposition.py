import math


def deposition_rate(d_p, rho_p, rho_f, mu, T, H=1.5, g=9.81):
    """
    Estimates the deposition rate (first-order rate constant) for airborne particles.
    Includes both gravitational settling and Brownian motion diffusion.

    Parameters:
    d_p   : Particle diameter (m)
    rho_p : Particle density (kg/m³)
    rho_f : Fluid density (kg/m³) (typically ~1.2 kg/m³ for air at sea level)
    mu    : Dynamic viscosity of air (Pa·s) (typically ~1.8e-5 Pa·s at 20°C)
    T     : Temperature (K) (typically ~293 K for room temperature)
    H     : Boundary layer height (m) (e.g., 1.5 m indoor, 1000 m outdoor)
    g     : Gravitational acceleration (m/s²) (default: 9.81 m/s²)

    Returns:
    k_d   : Deposition rate constant (1/s)
    v_d   : Deposition velocity (m/s)
    regime: Dominant deposition mechanism
    """

    # Constants
    k_B = 1.38e-23  # Boltzmann constant (J/K)

    # Calculate gravitational settling velocity using same approach as for particle settling in water
    v_s_stokes = (g * (rho_p - rho_f) * d_p**2) / (18 * mu)
    Re_stokes = (rho_f * v_s_stokes * d_p) / mu

    if Re_stokes < 0.1:
        v_s = v_s_stokes
        regime = "Brownian + Stokes' Law (laminar flow)"
    else:
        # Intermediate regime (iterative approach)
        v_s = v_s_stokes
        for _ in range(10):
            Re = (rho_f * v_s * d_p) / mu
            Cd = (24 / Re) * (1 + 0.15 * Re**0.687)
            v_s = math.sqrt((4 * g * d_p * (rho_p - rho_f)) / (3 * Cd * rho_f))

        if Re < 1000:
            regime = "Intermediate (empirical drag correction)"
        else:
            Cd_newton = 0.44
            v_s = math.sqrt((4 * g * d_p * (rho_p - rho_f)) / (3 * Cd_newton * rho_f))
            regime = "Newton's Law (turbulent flow)"

    # Brownian diffusion velocity (for nanoparticles)
    D_B = (k_B * T) / (3 * math.pi * mu * d_p)  # Diffusivity
    v_b = D_B / d_p  # Approximate Brownian deposition velocity

    # Total deposition velocity: sum of both effects
    v_d = v_s + v_b
    k_d = v_d / H  # First-order deposition rate

    return k_d, v_d, regime
