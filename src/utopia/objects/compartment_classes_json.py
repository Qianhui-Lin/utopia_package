import json
from utopia.objects.particulate_classes_json import *
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


def assign_box_to_compartment_json(compartment_json_str, box_dict):
    """Assign a box to a compartment JSON or dict

    Args:
        compartment_json_str: Compartment as JSON string or dict
        box_dict: Box as JSON string or dict

    Returns:
        Compartment JSON string with box assigned
    """
    # Parse if input is a string
    if isinstance(compartment_json_str, str):
        compartment_dict = json.loads(compartment_json_str)
    else:
        compartment_dict = compartment_json_str

    if isinstance(box_dict, str):
        box_dict = json.loads(box_dict)

    # Assign box to compartment
    compartment_dict["CBox_Bname"] = box_dict["Bname"]

    return compartment_dict
'''
def add_particles_to_compartment_json(compartment_json_str, particle_dict, particle_form):
    """Add particles to a compartment JSON
    
    Args:
        compartment_json_str: JSON string of the compartment
        particle_dict: Dictionary representing the particle
        particle_form: String indicating particle form ('freeMP', 'heterMP', 'biofMP', 'heterBiofMP')
    """
    # Parse JSON string
    compartment_dict = json.loads(compartment_json_str)
    
    # Validate particle form
    if particle_form not in compartment_dict["particles"]:
        raise ValueError(f"Invalid particle form: {particle_form}")
    
    # Add particle to appropriate list
    compartment_dict["particles"][particle_form].append(particle_dict)
    
    # Also assign compartment to particle if it has that field
    if isinstance(particle_dict, dict):
        particle_dict["assigned_compartment"] = compartment_dict["Cname"]
    
    return json.dumps(compartment_dict, indent=2, ensure_ascii=False)
'''
def add_particles_to_compartment_json(compartment_dict, particle_json_str, particle_form):
    """Add particles to a compartment JSON
    
    Args:
        compartment_json_str: JSON string of the compartment
        particle_json_str: JSON string representing the particle
        particle_form: String indicating particle form ('freeMP', 'heterMP', 'biofMP', 'heterBiofMP')
    """
    # Import the static method (adjust the import based on your file structure)
    # from particulate import Particulate
    # Or if you want to pass it as a parameter, see alternative below
    
    # Parse JSON strings

    
    if isinstance(particle_json_str, str):
        particle_dict = json.loads(particle_json_str)
    else:
        particle_dict = particle_json_str
    
    # Validate particle form
    if particle_form not in compartment_dict["particles"]:
        raise ValueError(f"Invalid particle form: {particle_form}")
    
    # Ensure the particle form key exists as a list
    if not isinstance(compartment_dict["particles"][particle_form], list):
        compartment_dict["particles"][particle_form] = []
    
    # First, add the particle to the compartment's particles list
    compartment_dict["particles"][particle_form].append(particle_dict)
    
    # Then, use the static method assign_compartment_json to assign compartment to particle
    # This mimics particle.assign_compartment(self) where self is the entire compartment
    updated_particle = Particulates.assign_compartment_json(particle_dict.copy(), compartment_dict)
    
    # Update the particle in the list with the one that has the compartment assigned
    compartment_dict["particles"][particle_form][-1] = updated_particle
    '''
    for form, plist in compartment_dict["particles"].items():
        for idx, p in enumerate(plist):
            print(f"particles[{form}][{idx}] is {type(p)}")
    这一段是用来debug是不是混入了object的
    '''
    '''
    def find_non_serializable(obj, path=""):
        # 只递归 dict 和 list
        if isinstance(obj, dict):
            for k, v in obj.items():
                find_non_serializable(v, path + f"['{k}']")
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                find_non_serializable(item, path + f"[{idx}]")
        else:
            # 非基础类型
            if not isinstance(obj, (str, int, float, bool, type(None), dict, list)):
                print(f"Non-serializable object at {path}: {type(obj)}")

    # 在 json.dumps 之前调用
    find_non_serializable(compartment_dict)
'''
    
    return json.dumps(compartment_dict, indent=2, ensure_ascii=False)

def calc_volume_compartment_json(compartment_json_str):
    """Calculate volume for a compartment from JSON string"""
    # Parse JSON string
    compartment_dict = json.loads(compartment_json_str)
    
    if compartment_dict["Cvolume_m3"] is None:
        # Check if we have all required dimensions
        required_dims = ["Cdepth_m", "Clength_m", "Cwidth_m"]
        if any(compartment_dict[attr] is None for attr in required_dims):
            print(
                "Missing parameters needed to calculate compartment volume --> "
                "Try calc_vol_fromBox or add missing values to compartment dimensions"
            )
        else:
            # Calculate volume
            compartment_dict["Cvolume_m3"] = (
                compartment_dict["Cdepth_m"] * 
                compartment_dict["Clength_m"] * 
                compartment_dict["Cwidth_m"]
            )
            print(f"Calculated {compartment_dict['Cname']} volume: {compartment_dict['Cvolume_m3']} m3")
    else:
        print(f"Assigned {compartment_dict['Cname']} volume: {compartment_dict['Cvolume_m3']} m3")
    
    return json.dumps(compartment_dict, indent=2, ensure_ascii=False)

def calc_vol_fromBox_compartment_json(compartment_json_str):
    """Calculate compartment volume from assigned box JSON"""
    # Parse JSON string
    compartment_dict = json.loads(compartment_json_str)
    
    # Check if box is assigned
    if "CBox" not in compartment_dict:
        print("No box assigned to this compartment. Use assign_box_to_compartment_json first.")
        return json.dumps(compartment_dict, indent=2, ensure_ascii=False)
    
    box_dict = compartment_dict["CBox"]
    
    # Check if box has volume and volume fractions
    if box_dict.get("Bvolume_m3") is None:
        print("Box volume is not calculated. Calculate box volume first.")
        return json.dumps(compartment_dict, indent=2, ensure_ascii=False)
    
    if "CvolFractionBox" not in box_dict:
        print("Box does not have compartment volume fractions defined.")
        return json.dumps(compartment_dict, indent=2, ensure_ascii=False)
    
    compartment_name_lower = compartment_dict["Cname"].lower()
    if compartment_name_lower not in box_dict["CvolFractionBox"]:
        print(f"Volume fraction for compartment '{compartment_dict['Cname']}' not found in box.")
        return json.dumps(compartment_dict, indent=2, ensure_ascii=False)
    
    # Calculate volume
    compartment_dict["Cvolume_m3"] = (
        box_dict["Bvolume_m3"] * box_dict["CvolFractionBox"][compartment_name_lower]
    )
    
    print(f"Calculated {compartment_dict['Cname']} volume from box: {compartment_dict['Cvolume_m3']} m3")
    
    return json.dumps(compartment_dict, indent=2, ensure_ascii=False)

def calc_particleConcentration_Nm3_initial_json(compartment_json_str):
    """Calculate initial particle concentration for compartment JSON"""
    # Parse JSON string
    compartment_dict = json.loads(compartment_json_str)
    
    # Check if volume is calculated
    if compartment_dict["Cvolume_m3"] is None:
        print("Compartment volume is not calculated. Calculate volume first.")
        return json.dumps(compartment_dict, indent=2, ensure_ascii=False)
    
    # Calculate concentration for each particle type
    for particle_type in compartment_dict["particles"]:
        for i, particle in enumerate(compartment_dict["particles"][particle_type]):
            if isinstance(particle, dict) and "Pnumber" in particle:
                # Calculate initial concentration
                initial_conc = particle["Pnumber"] / compartment_dict["Cvolume_m3"]
                compartment_dict["particles"][particle_type][i]["initial_conc_Nm3"] = initial_conc
            else:
                print(f"Particle in {particle_type} missing 'Pnumber' attribute")
    
    return json.dumps(compartment_dict, indent=2, ensure_ascii=False)

# Helper function to work with both compartment and box together
def add_compartment_to_box_and_assign_json(box_json_str, compartment_json_str):
    """Add compartment to box and assign box to compartment in one operation"""
    # Parse JSON strings
    box_dict = json.loads(box_json_str)
    compartment_dict = json.loads(compartment_json_str)
    
    # Add compartment to box
    box_dict["compartments"].append(compartment_dict)
    
    # Assign box to compartment
    compartment_dict["CBox"] = box_dict
    
    # Update the compartment in the box's compartments list
    box_dict["compartments"][-1] = compartment_dict
    
    return json.dumps(box_dict, indent=2, ensure_ascii=False)
