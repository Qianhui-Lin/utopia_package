class Compartment:
    """Class Compartment (parent class) generates compartment objects that belong by default to an assigned model box (Cbox). Each compartment contains four different particle objects corresponding to the 4 described aggregation states of UTOPIA (freeMP, heterMP, biofMP, heterBiofMP) and the processes that can occur in the compartment are listed under the processess attribute. Each compartment has a set of connexions withing the UTOPIA box listed in the conexions attribute wich will be asigned by reading on the conexions input file of the model."""

    def __init__(
        self,
        Cname,
        Cdepth_m=None,
        Clength_m=None,
        Cwidth_m=None,
        Cvolume_m3=None,
        CsurfaceArea_m2=None,
    ):
        self.Cname = Cname
        self.Cdepth_m = Cdepth_m
        self.Clength_m = Clength_m
        self.Cwidth_m = Cwidth_m
        self.Cvolume_m3 = Cvolume_m3
        self.CsurfaceArea_m2 = CsurfaceArea_m2
        self.particles = {
            "freeMP": [],
            "heterMP": [],
            "biofMP": [],
            "heterBiofMP": [],
        }  # dictionary of particles in the compartment
        self.processess = [
            "degradation",
            "fragmentation",
            "heteroaggregation",
            "heteroaggregate_breackup",
            "biofouling",
            "defouling",
            "advective_transport",
            "settling",
            "rising",
        ]
        self.connexions = []

    def assign_box(self, Box):
        self.CBox = Box

    def add_particles(self, particle):
        self.particles[particle.Pform].append(particle)
        particle.assign_compartment(self)

    def calc_volume(self):
        if self.Cvolume_m3 is None:
            if any(
                attr is None for attr in [self.Cdepth_m, self.Clength_m, self.Cwidth_m]
            ):
                print(
                    "Missing parameters needded to calculate compartment volume --> Try calc_vol_fromBox or add missing values to compartment dimensions"
                )

            else:
                self.Cvolume_m3 = self.Cdepth_m * self.Clength_m * self.Cwidth_m
                # print(
                #     "Calculated "
                #     + self.Cname
                #     + " volume: "
                #     + str(self.Cvolume_m3)
                #     + " m3"
                # )
        else:
            pass
            # print("Assigned " + self.Cname + " volume: " + str(self.Cvolume_m3) + " m3")

    def calc_vol_fromBox(self):
        self.Cvolume_m3 = (
            self.CBox.Bvolume_m3 * self.CBox.CvolFractionBox[self.Cname.lower()]
        )

    def calc_particleConcentration_Nm3_initial(self):
        for p in self.particles:
            for s in self.particles[p]:
                self.particles[p][s].initial_conc_Nm3 = (
                    self.particles[p][s].Pnumber / self.Cvolume_m3
                )


"""Compartment Subclasses (inheritances) of the class compartment add extra attributes to the compatment that define the type of compartment (i.e. compartment processess) """


class compartment_water(Compartment):

    def __init__(
        self,
        Cname,
        SPM_mgL,
        waterFlow_m3_s,
        T_K,
        G,
        Cdepth_m=None,
        Clength_m=None,
        Cwidth_m=None,
        Cvolume_m3=None,
        CsurfaceArea_m2=None,
        flowVelocity_m_s=None,
    ):
        super().__init__(
            Cname, Cdepth_m, Clength_m, Cwidth_m, Cvolume_m3, CsurfaceArea_m2
        )
        self.SPM_mgL = SPM_mgL
        self.flowVelocity_m_s = flowVelocity_m_s
        self.waterFlow_m3_s = waterFlow_m3_s
        self.T_K = T_K
        self.G = G  # Shear rate (G, in s−1)
        self.processess = [
            "discorporation",
            "fragmentation",
            "heteroaggregation",
            "heteroaggregate_breackup",
            "biofouling",
            "defouling",
            "advective_transport",
            "settling",
            "rising",
            "mixing",
        ]


class compartment_surfaceSea_water(Compartment):

    def __init__(
        self,
        Cname,
        SPM_mgL,
        waterFlow_m3_s,
        T_K,
        G,
        Cdepth_m=None,
        Clength_m=None,
        Cwidth_m=None,
        Cvolume_m3=None,
        CsurfaceArea_m2=None,
        flowVelocity_m_s=None,
    ):
        super().__init__(
            Cname, Cdepth_m, Clength_m, Cwidth_m, Cvolume_m3, CsurfaceArea_m2
        )
        self.SPM_mgL = SPM_mgL
        self.flowVelocity_m_s = flowVelocity_m_s
        self.waterFlow_m3_s = waterFlow_m3_s
        self.T_K = T_K
        self.G = G  # Shear rate (G, in s−1)
        self.processess = [
            "discorporation",
            "fragmentation",
            "heteroaggregation",
            "heteroaggregate_breackup",
            "biofouling",
            "defouling",
            "advective_transport",
            "settling",
            "rising",
            "mixing",
            "sea_spray_aerosol",
            "beaching",
        ]


class compartment_sediment(Compartment):
    def __init__(
        self,
        Cname,
        Cdepth_m=None,
        Clength_m=None,
        Cwidth_m=None,
        Cvolume_m3=None,
        CsurfaceArea_m2=None,
    ):
        super().__init__(
            Cname, Cdepth_m, Clength_m, Cwidth_m, Cvolume_m3, CsurfaceArea_m2
        )
        self.processess = [
            "discorporation",
            "fragmentation",
            "sediment_resuspension",
            "burial",
        ]


class compartment_soil_surface(Compartment):
    def __init__(
        self,
        Cname,
        Cdepth_m=None,
        Clength_m=None,
        Cwidth_m=None,
        Cvolume_m3=None,
        CsurfaceArea_m2=None,
    ):
        super().__init__(
            Cname, Cdepth_m, Clength_m, Cwidth_m, Cvolume_m3, CsurfaceArea_m2
        )

        self.processess = [
            "discorporation",
            "fragmentation",
            "runoff_transport",
            "percolation",
            "soil_air_resuspension",
            "soil_convection",
        ]
        # Potential etra parameters to add:
        # self.earthworm_density_in_m3 = earthworm_density_in_m3
        # self.Qrunoff_m3 = Qrunoff_m3


class compartment_deep_soil(Compartment):
    def __init__(
        self,
        Cname,
        Cdepth_m=None,
        Clength_m=None,
        Cwidth_m=None,
        Cvolume_m3=None,
        CsurfaceArea_m2=None,
    ):
        super().__init__(
            Cname, Cdepth_m, Clength_m, Cwidth_m, Cvolume_m3, CsurfaceArea_m2
        )
        self.processess = [
            "discorporation",
            "fragmentation",
            "sequestration_deep_soils",
            "soil_convection",
        ]


# retention_in_soil (straining?) of the particles in soil following heteroaggregation with geocolloids?
# shall we also include heteroaggregation/heteroaggegrate break-up processess in the soil compartment?

# Difference between retention in soil and sequestration deep soil: sequestrations deep soil is an elemination process-->out of the system)


class compartment_air(Compartment):
    def __init__(
        self,
        Cname,
        T_K=None,
        wind_speed_m_s=None,
        I_rainfall_mm=None,
        Cdepth_m=None,
        Clength_m=None,
        Cwidth_m=None,
        Cvolume_m3=None,
        CsurfaceArea_m2=None,
        flowVelocity_m_s=None,
    ):
        super().__init__(
            Cname, Cdepth_m, Clength_m, Cwidth_m, Cvolume_m3, CsurfaceArea_m2
        )
        self.T_K = T_K
        self.wind_speed_m_s = wind_speed_m_s
        self.I_rainfall_mm = I_rainfall_mm
        self.flowVelocity_m_s = flowVelocity_m_s
        self.processess = [
            "discorporation",
            "fragmentation",
            "wind_trasport",
            "dry_deposition",
            "wet_deposition",
        ]
        # shall we also include heteroaggregation/heteroaggegrate break-up processess in the air compartment?
