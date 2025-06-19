import json
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

    def to_json(self):
        """Convert compartment object to JSON"""
        data = {
            "Cname": self.Cname,
            "Cdepth_m": self.Cdepth_m,
            "Clength_m": self.Clength_m,
            "Cwidth_m": self.Cwidth_m,
            "Cvolume_m3": self.Cvolume_m3,
            "CsurfaceArea_m2": self.CsurfaceArea_m2,
            "particles": self.particles,
            "processess": self.processess,
            "connexions": self.connexions,
        }
        
        # Add CBox if it exists
        if hasattr(self, 'CBox'):
            data["CBox"] = getattr(self.CBox, 'to_json', lambda: str(self.CBox))()
        
        return json.dumps(data, indent=2)
    
    def to_dict(self):
        """Convert compartment object to dictionary"""
        data = {
            "Cname": self.Cname,
            "Cdepth_m": self.Cdepth_m,
            "Clength_m": self.Clength_m,
            "Cwidth_m": self.Cwidth_m,
            "Cvolume_m3": self.Cvolume_m3,
            "CsurfaceArea_m2": self.CsurfaceArea_m2,
            "particles": self.particles,
            "processess": self.processess,
            "connexions": self.connexions,
        }
        
        # Add CBox if it exists
        if hasattr(self, 'CBox'):
            data["CBox"] = getattr(self.CBox, 'to_dict', lambda: str(self.CBox))()
        
        return data    


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

    def to_json(self):
        """Convert water compartment object to JSON"""
        data = super().to_dict()
        data.update({
            "SPM_mgL": self.SPM_mgL,
            "flowVelocity_m_s": self.flowVelocity_m_s,
            "waterFlow_m3_s": self.waterFlow_m3_s,
            "T_K": self.T_K,
            "G": self.G,
            "compartment_type": "water"
        })
        return json.dumps(data, indent=2)

    def to_dict(self):
        """Convert water compartment object to dictionary"""
        data = super().to_dict()
        data.update({
            "SPM_mgL": self.SPM_mgL,
            "flowVelocity_m_s": self.flowVelocity_m_s,
            "waterFlow_m3_s": self.waterFlow_m3_s,
            "T_K": self.T_K,
            "G": self.G,
            "compartment_type": "water"
        })
        return data


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

def to_json(self):
        """Convert surface sea water compartment object to JSON"""
        data = super().to_dict()
        data.update({
            "SPM_mgL": self.SPM_mgL,
            "flowVelocity_m_s": self.flowVelocity_m_s,
            "waterFlow_m3_s": self.waterFlow_m3_s,
            "T_K": self.T_K,
            "G": self.G,
            "compartment_type": "surfaceSea_water"
        })
        return json.dumps(data, indent=2)

def to_dict(self):
        """Convert surface sea water compartment object to dictionary"""
        data = super().to_dict()
        data.update({
            "SPM_mgL": self.SPM_mgL,
            "flowVelocity_m_s": self.flowVelocity_m_s,
            "waterFlow_m3_s": self.waterFlow_m3_s,
            "T_K": self.T_K,
            "G": self.G,
            "compartment_type": "surfaceSea_water"
        })
        return data


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
    
    def to_json(self):
        """Convert sediment compartment object to JSON"""
        data = super().to_dict()
        data.update({
            "compartment_type": "sediment"
        })
        return json.dumps(data, indent=2)

    def to_dict(self):
        """Convert sediment compartment object to dictionary"""
        data = super().to_dict()
        data.update({
            "compartment_type": "sediment"
        })
        return data


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
    
    def to_json(self):
        """Convert soil surface compartment object to JSON"""
        data = super().to_dict()
        data.update({
            "compartment_type": "soil_surface"
        })
        return json.dumps(data, indent=2)

    def to_dict(self):
        """Convert soil surface compartment object to dictionary"""
        data = super().to_dict()
        data.update({
            "compartment_type": "soil_surface"
        })
        return data

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


    def to_json(self):
        """Convert deep soil compartment object to JSON"""
        data = super().to_dict()
        data.update({
            "compartment_type": "deep_soil"
        })
        return json.dumps(data, indent=2)

    def to_dict(self):
        """Convert deep soil compartment object to dictionary"""
        data = super().to_dict()
        data.update({
            "compartment_type": "deep_soil"
        })
        return data


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

    def to_json(self):
        """Convert air compartment object to JSON"""
        data = super().to_dict()
        data.update({
            "T_K": self.T_K,
            "wind_speed_m_s": self.wind_speed_m_s,
            "I_rainfall_mm": self.I_rainfall_mm,
            "flowVelocity_m_s": self.flowVelocity_m_s,
            "compartment_type": "air"
        })
        return json.dumps(data, indent=2)

    def to_dict(self):
        """Convert air compartment object to dictionary"""
        data = super().to_dict()
        data.update({
            "T_K": self.T_K,
            "wind_speed_m_s": self.wind_speed_m_s,
            "I_rainfall_mm": self.I_rainfall_mm,
            "flowVelocity_m_s": self.flowVelocity_m_s,
            "compartment_type": "air"
        })
        return data