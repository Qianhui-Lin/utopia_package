import math
import numpy as np
import json


class Particulates:
    """Class Particulates generates particulate objects, especifically microplastic particle objects. The class defines a particle object by its composition, shape and dimensions"""

    # constructor
    def __init__(
        self,
        Pname,
        Pform,
        Pcomposition,
        Pdensity_kg_m3,
        Pshape,
        PdimensionX_um,
        PdimensionY_um,
        PdimensionZ_um,
        t_half_d=5000,
        Pnumber_t0=None,
    ):
        self.Pname = Pname
        self.Pform = Pform  # Pform has to be in the particles type list: ["freeMP",""heterMP","biofMP","heterBiofMP"]
        self.Pcomposition = Pcomposition
        self.Pdensity_kg_m3 = Pdensity_kg_m3
        self.Pshape = Pshape
        self.PdimensionX_um = PdimensionX_um  # shortest size
        self.PdimensionY_um = PdimensionY_um  # longest size
        self.PdimensionZ_um = PdimensionZ_um  # intermediate size
        self.PdimensionX_m = PdimensionX_um / 1000000  # shortest size
        self.PdimensionY_m = PdimensionY_um / 1000000  # longest size
        self.PdimensionZ_m = PdimensionZ_um / 1000000  # intermediate size
        self.Pnumber_t0 = Pnumber_t0  # number of particles at time 0. to be objetained from emissions and background concentration of the compartment
        self.radius_m = (
            self.PdimensionX_um / 1e6
        )  # In spherical particles from MP radius (x dimension)
        self.diameter_m = self.radius_m * 2
        self.diameter_um = self.diameter_m * 1e6
        self.Pemiss_t_y = 0  # set as 0
        self.t_half_d = t_half_d

    def __repr__(self):
        return (
            "{"
            + self.Pname
            + ", "
            + self.Pform
            + ", "
            + self.Pcomposition
            + ", "
            + self.Pshape
            + ", "
            + str(self.Pdensity_kg_m3)
            + ", "
            + str(self.radius_m)
            + "}"
        )
    
    def to_dict(self):
        """Convert the particulate object to a dictionary for JSON serialization"""
        data = {}
        
        # Get all attributes that don't start with underscore and aren't methods
        for attr_name in dir(self):
            if not attr_name.startswith('_') and not callable(getattr(self, attr_name)):
                attr_value = getattr(self, attr_name)
                
                # Handle numpy types that aren't JSON serializable
                if isinstance(attr_value, (np.integer, np.floating)):
                    attr_value = attr_value.item()
                elif isinstance(attr_value, np.ndarray):
                    attr_value = attr_value.tolist()
                
                data[attr_name] = attr_value
        
        return data
    
    def to_json(self, indent=2):
        """Convert the particulate object to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)


    
    # JSON-based methods that work directly on JSON dictionaries
    # here particle_json should be a python dict
    @staticmethod
    def calc_volume_json(particle_json):
        """Particle volume calculation that works directly on JSON. Returns updated JSON."""
        # particle = particle_json.copy()  # not modify original 有待确认
         
        if particle_json["Pshape"] == "sphere":
            radius_m = particle_json["PdimensionX_um"] / 1e6
            particle_json["Pvolume_m3"] = 4 / 3 * math.pi * (radius_m) ** 3
            particle_json["CSF"] = 1
            
        elif (
            particle_json["Pshape"] == "fibre"
            or particle_json["Pshape"] == "fiber"
            or particle_json["Pshape"] == "cylinder"
        ):
            radius_m = particle_json["PdimensionX_um"] / 1e6
            PdimensionY_m = particle_json["PdimensionY_um"] / 1e6
            particle_json["Pvolume_m3"] = math.pi * (radius_m) ** 2 * PdimensionY_m
            particle_json["CSF"] = radius_m / math.sqrt(PdimensionY_m * radius_m)
            
        elif particle_json["Pshape"] == "pellet" or particle_json["Pshape"] == "fragment":
            PdimensionX_m = particle_json["PdimensionX_um"] / 1e6
            PdimensionY_m = particle_json["PdimensionY_um"] / 1e6
            PdimensionZ_m = particle_json["PdimensionZ_um"] / 1e6
            particle_json["Pvolume_m3"] = PdimensionX_m * PdimensionY_m * PdimensionZ_m
            particle_json["CSF"] = PdimensionX_m / math.sqrt(PdimensionY_m * PdimensionZ_m)
            
        else:
            print("Error: unknown shape")
            
        return particle_json
    
    @staticmethod
    def calc_numConc_json(particle_json, concMass_mg_L, concNum_part_L):
        """Number concentration calculation that works directly on JSON. Returns updated JSON."""
        # particle = particle_json.copy()  # not modify original 有待确认
        
        if concNum_part_L == 0:
            particle_json["concNum_part_m3"] = (
                concMass_mg_L / 1000 / particle_json["Pdensity_kg_m3"] / particle_json["Pvolume_m3"]
            )
        else:
            particle_json["concNum_part_m3"] = concNum_part_L * 1000
            
        return particle_json
    
    @staticmethod
    def assign_compartment_json(particle_json, comp):
        # 这里在updated_comp_json = add_particles_to_compartment_json(
                        #comp,  # Convert current comp dict back to JSON string
                        #p_copy,            # Pass the particle dict (function handles it)
                        #p_form             # Pass the particle form
                    #)出现了circular reference问题
        # 
        # 因此，可以仅存储compartment的名称或ID，而不是整个compartment dict，如下：
        #particle_json["Pcompartment"] = comp.get("Cname") 
        # 但是，我担心万一有用
        # 所以，此处可以把comp直接存为str，同时也存储compartment的ID
        # 后来发现，后面也用到了boxname，所以也存一下
        # print("keys of comp:", list(comp.keys()))
        particle_json["Pcompartment_Cname"] = comp["Cname"]
        particle_json["Pcompartment_CBox_Bname"] = comp["CBox_Bname"]
        
        # particle_json["Pcompartment"] = json.dumps(comp) 这样好像不行

        #particle = particle_json.copy()  # not modify original 有待确认
        #或者：
        #particle_json["Pcompartment"] = comp

        return particle_json


    # methods

    def calc_volume(self):
        """Particle volume calculation. Different formulas for different particle shapes, currently defined for spheres, fibres, cylinders, pellets and irregular fragments"""

        if self.Pshape == "sphere":
            self.Pvolume_m3 = 4 / 3 * math.pi * (self.radius_m) ** 3
            # calculates volume (in m3) of spherical particles from MP radius (x dimension)
            self.CSF = 1
            # calculate corey shape factor (CSF)
            # (Waldschlaeger 2019, doi:10.1021/acs.est.8b06794)
            # print(
            #     "Calculated " + self.Pname + " volume: " + str(self.Pvolume_m3) + " m3"
            # )
            # print("Calculated Corey Shape Factor: " + str(self.CSF))

        elif (
            self.Pshape == "fibre"
            or self.Pshape == "fiber"
            or self.Pshape == "cylinder"
        ):
            self.Pvolume_m3 = math.pi * (self.radius_m) ** 2 * (self.PdimensionY_m)
            # calculates volume (in m3) of fibres or cylinders from diameter and
            # length assuming cylindrical shape where X is the shorterst size (radius) ans Y the longest (heigth)
            self.CSF = (self.radius_m) / math.sqrt(self.PdimensionY_m * self.radius_m)
            # calculate corey shape factor (CSF)
            # (Waldschlaeger 2019, doi:10.1021/acs.est.8b06794)
            # print(
            #     "Calculated " + self.Pname + " volume: " + str(self.Pvolume_m3) + " m3"
            # )
            # print("Calculated Corey Shape Factor: " + str(self.CSF))

        elif self.Pshape == "pellet" or self.Pshape == "fragment":
            self.Pvolume_m3 = (
                self.PdimensionX_m * self.PdimensionY_m * self.PdimensionZ_m
            )
            # approximate volume calculation for irregular fragments
            # approximated as a cuboid using longest, intermediate and shortest length
            #!! Note: not sure if pellets fits best here or rather as sphere/cylinder
            # might adjust later!!
            self.CSF = self.PdimensionX_m / math.sqrt(
                self.PdimensionY_m * self.PdimensionZ_m
            )
            # calculate corey shape factor (CSF)
            # (Waldschlaeger 2019, doi:10.1021/acs.est.8b06794)
            # print(
            #     "Calculated " + self.Pname + " volume: " + str(self.Pvolume_m3) + " m3"
            # )
            # print("Calculated Corey Shape Factor: " + str(self.CSF))

        else:
            print("Error: unknown shape")
            # print error message for shapes other than spheres
            # (to be removed when other volume calculations are implemented)

    def calc_numConc(self, concMass_mg_L, concNum_part_L):

        if concNum_part_L == 0:
            self.concNum_part_m3 = (
                concMass_mg_L / 1000 / self.Pdensity_kg_m3 / self.Pvolume_m3
            )
            # if mass concentration is given, it is converted to number concentration
        else:
            self.concNum_part_m3 = concNum_part_L * 1000
            # if number concentration is given, it is converted from part/L to part/m3

    def assign_compartment(self, comp):
        self.Pcompartment = comp


class ParticulatesBF(Particulates):
    "This is a class to create ParticulatesBIOFILM objects"

    # class attribute
    species = "particulate"

    # constructor
    def __init__(self, parentMP, spm):

        self.Pname = parentMP.Pname + "_BF"
        self.Pcomposition = parentMP.Pcomposition
        self.Pform = "biofMP"
        self.parentMP = parentMP
        self.BF_density_kg_m3 = spm.Pdensity_kg_m3
        self.BF_thickness_um = spm.PdimensionX_um
        self.radius_m = parentMP.radius_m + (
            self.BF_thickness_um / 1e6
        )  # In spherical particles from MP radius (x dimension)
        self.diameter_m = self.radius_m * 2
        self.diameter_um = self.diameter_m * 1e6
        self.t_half_d = 25000  # As per The Full Multi parameterization
        if parentMP.PdimensionY_um == 0:
            self.PdimensionY_um = 0
        else:
            self.PdimensionY_um = parentMP.PdimensionY_um + self.BF_thickness_um * 2

        if parentMP.PdimensionZ_um == 0:
            self.PdimensionZ_um = 0
        else:
            self.PdimensionZ_um = parentMP.PdimensionZ_um + self.BF_thickness_um * 2

        if parentMP.PdimensionX_um == 0:
            self.PdimensionX_um = 0
        else:
            self.PdimensionX_um = parentMP.PdimensionX_um + self.BF_thickness_um * 2

        self.Pshape = (
            parentMP.Pshape
        )  # to be updated for biofilm, could argue that shape is retained (unlike for SPM-bound)
        self.Pdensity_kg_m3 = (
            self.parentMP.radius_m**3 * self.parentMP.Pdensity_kg_m3
            + (
                (self.parentMP.radius_m + (self.BF_thickness_um / 1e6)) ** 3
                - self.parentMP.radius_m**3
            )
            * self.BF_density_kg_m3
        ) / ((self.parentMP.radius_m + (self.BF_thickness_um / 1e6)) ** 3)
        # equation from Kooi et al for density

        self.PdimensionX_m = self.PdimensionX_um / 1000000  # shortest size
        self.PdimensionY_m = self.PdimensionY_um / 1000000  # longest size
        self.PdimensionZ_m = self.PdimensionZ_um / 1000000  # intermediate size

    @staticmethod
    def create_bf_json(parentMP_json, spm_json):
        """Create a ParticulatesBF JSON from parent MP and SPM JSONs"""
        bf_json = {}
        
        bf_json["Pname"] = parentMP_json["Pname"] + "_BF"
        bf_json["Pcomposition"] = parentMP_json["Pcomposition"]
        bf_json["Pform"] = "biofMP"
        bf_json["species"] = "particulate"
        bf_json["parentMP"] = parentMP_json.copy()
        bf_json["BF_density_kg_m3"] = spm_json["Pdensity_kg_m3"]
        bf_json["BF_thickness_um"] = spm_json["PdimensionX_um"]
        
        bf_json["radius_m"] = parentMP_json["radius_m"] + (bf_json["BF_thickness_um"] / 1e6)
        bf_json["diameter_m"] = bf_json["radius_m"] * 2
        bf_json["diameter_um"] = bf_json["diameter_m"] * 1e6
        bf_json["t_half_d"] = 25000
        
        if parentMP_json["PdimensionY_um"] == 0:
            bf_json["PdimensionY_um"] = 0
        else:
            bf_json["PdimensionY_um"] = parentMP_json["PdimensionY_um"] + bf_json["BF_thickness_um"] * 2

        if parentMP_json["PdimensionZ_um"] == 0:
            bf_json["PdimensionZ_um"] = 0
        else:
            bf_json["PdimensionZ_um"] = parentMP_json["PdimensionZ_um"] + bf_json["BF_thickness_um"] * 2

        if parentMP_json["PdimensionX_um"] == 0:
            bf_json["PdimensionX_um"] = 0
        else:
            bf_json["PdimensionX_um"] = parentMP_json["PdimensionX_um"] + bf_json["BF_thickness_um"] * 2

        bf_json["Pshape"] = parentMP_json["Pshape"]
        
        # Calculate density using Kooi et al equation
        bf_json["Pdensity_kg_m3"] = (
            parentMP_json["radius_m"]**3 * parentMP_json["Pdensity_kg_m3"]
            + (
                (parentMP_json["radius_m"] + (bf_json["BF_thickness_um"] / 1e6)) ** 3
                - parentMP_json["radius_m"]**3
            )
            * bf_json["BF_density_kg_m3"]
        ) / ((parentMP_json["radius_m"] + (bf_json["BF_thickness_um"] / 1e6)) ** 3)

        bf_json["PdimensionX_m"] = bf_json["PdimensionX_um"] / 1000000
        bf_json["PdimensionY_m"] = bf_json["PdimensionY_um"] / 1000000
        bf_json["PdimensionZ_m"] = bf_json["PdimensionZ_um"] / 1000000
        bf_json["Pemiss_t_y"] = 0
        
        bf_json["_class_type"] = "ParticulatesBF"
        
        return bf_json

class ParticulatesSPM(Particulates):
    "This is a class to create ParticulatesSPM objects"

    # class attribute
    species = "particulate"

    # constructor
    def __init__(self, parentSPM, parentMP):

        self.Pname = parentMP.Pname + "_SPM"
        self.Pcomposition = parentMP.Pcomposition
        if parentMP.Pform == "biofMP":
            self.Pform = "heterBiofMP"
            self.t_half_d = 50000  # As per The Full multi parameterization
        else:
            self.Pform = "heterMP"
            self.t_half_d = 100000  # As per The Full multi parameterizatio
        self.parentMP = parentMP
        self.parentSPM = parentSPM
        self.Pdensity_kg_m3 = parentMP.Pdensity_kg_m3 * (
            parentMP.Pvolume_m3 / (parentMP.Pvolume_m3 + parentSPM.Pvolume_m3)
        ) + parentSPM.Pdensity_kg_m3 * (
            parentSPM.Pvolume_m3 / (parentMP.Pvolume_m3 + parentSPM.Pvolume_m3)
        )
        self.radius_m = (
            3 * (parentMP.Pvolume_m3 + parentSPM.Pvolume_m3) / (4 * math.pi)
        ) ** (
            1 / 3
        )  # Note: this is an equivalent radius. MP-SPM most likely not truly spherical
        self.diameter_m = self.radius_m * 2
        self.diameter_um = self.diameter_m * 1e6
        self.Pshape = (
            parentMP.Pshape
        )  # to be updated for biofilm, could argue that shape is retained (unlike for SPM-bound)


    # methods

    # volume calculation - currently simple version.
    # more complexity to be added later:
    # different formulas for different particle shapes.
    # currently defined for spheres, fibres, cylinders, pellets and irregular fragments
    def calc_volume_heter(self, parentMP, parentSPM):
        if self.Pshape == "sphere":
            self.Pvolume_m3 = parentMP.Pvolume_m3 + parentSPM.Pvolume_m3
            # calculates volume (in m3) of spherical particles from MP radius (x dimension)
            self.CSF = 1
            # calculate corey shape factor (CSF)
            # (Waldschlaeger 2019, doi:10.1021/acs.est.8b06794)

        elif (
            self.Pshape == "fibre"
            or self.Pshape == "fiber"
            or self.Pshape == "cylinder"
        ):
            self.Pvolume_m3 = parentMP.Pvolume_m3 + parentSPM.Pvolume_m3
            # calculates volume (in m3) of fibres or cylinders from diameter and
            # length assuming cylindrical shape where X is the shorterst size (radius) ans Y the longest (heigth)
            self.CSF = (self.radius_m) / math.sqrt(self.PdimensionY_m * self.radius_m)
            # calculate corey shape factor (CSF)
            # (Waldschlaeger 2019, doi:10.1021/acs.est.8b06794)

        elif self.Pshape == "pellet" or self.Pshape == "fragment":
            self.Pvolume_m3 = parentMP.Pvolume_m3 + parentSPM.Pvolume_m3
            # approximate volume calculation for irregular fragments
            # approximated as a cuboid using longest, intermediate and shortest length
            #!! Note: not sure if pellets fits best here or rather as sphere/cylinder
            # might adjust later!!
            self.CSF = self.PdimensionX_m / math.sqrt(
                self.PdimensionY_m * self.PdimensionZ_m
            )
            # calculate corey shape factor (CSF)
            # (Waldschlaeger 2019, doi:10.1021/acs.est.8b06794)

        else:
            print("Error: unknown shape")

        # print("Calculated " + self.Pname + " volume: " + str(self.Pvolume_m3) + " m3")

# JSON-based methods for ParticulatesSPM that work directly on JSON dictionaries
    @staticmethod
    def create_pspm_json(parentSPM_json, parentMP_json):
        """Create a ParticulatesSPM JSON from parent SPM and MP JSONs"""
        pspm_json = {}
        
        pspm_json["Pname"] = parentMP_json["Pname"] + "_SPM"
        pspm_json["Pcomposition"] = parentMP_json["Pcomposition"]
        pspm_json["species"] = "particulate"
        
        if parentMP_json["Pform"] == "biofMP":
            pspm_json["Pform"] = "heterBiofMP"
            pspm_json["t_half_d"] = 50000
        else:
            pspm_json["Pform"] = "heterMP"
            pspm_json["t_half_d"] = 100000
            
        pspm_json["parentMP"] = parentMP_json.copy()
        pspm_json["parentSPM"] = parentSPM_json.copy()
        
        # Calculate density
        pspm_json["Pdensity_kg_m3"] = parentMP_json["Pdensity_kg_m3"] * (
            parentMP_json["Pvolume_m3"] / (parentMP_json["Pvolume_m3"] + parentSPM_json["Pvolume_m3"])
        ) + parentSPM_json["Pdensity_kg_m3"] * (
            parentSPM_json["Pvolume_m3"] / (parentMP_json["Pvolume_m3"] + parentSPM_json["Pvolume_m3"])
        )
        
        # Calculate equivalent radius
        pspm_json["radius_m"] = (
            3 * (parentMP_json["Pvolume_m3"] + parentSPM_json["Pvolume_m3"]) / (4 * math.pi)
        ) ** (1 / 3)
        
        pspm_json["diameter_m"] = pspm_json["radius_m"] * 2
        pspm_json["diameter_um"] = pspm_json["diameter_m"] * 1e6
        pspm_json["Pshape"] = parentMP_json["Pshape"]
        pspm_json["Pemiss_t_y"] = 0
        
        pspm_json["_class_type"] = "ParticulatesSPM"
        
        return pspm_json
    
    @staticmethod
    def calc_volume_heter_json(pspm_json, parentMP_json, parentSPM_json):
        """Volume calculation for heterogeneous particles that works directly on JSON. Returns updated JSON."""
        # particle = pspm_json.copy()  # not modify original 有待确认
        
        if pspm_json["Pshape"] == "sphere":
            pspm_json["Pvolume_m3"] = parentMP_json["Pvolume_m3"] + parentSPM_json["Pvolume_m3"]
            pspm_json["CSF"] = 1
            
        elif (
            pspm_json["Pshape"] == "fibre"
            or pspm_json["Pshape"] == "fiber"
            or pspm_json["Pshape"] == "cylinder"
        ):
            pspm_json["Pvolume_m3"] = parentMP_json["Pvolume_m3"] + parentSPM_json["Pvolume_m3"]
            radius_m = pspm_json["radius_m"]
            PdimensionY_m = pspm_json.get("PdimensionY_m", parentMP_json.get("PdimensionY_m", 0))
            pspm_json["CSF"] = radius_m / math.sqrt(PdimensionY_m * radius_m)
            
        elif pspm_json["Pshape"] == "pellet" or pspm_json["Pshape"] == "fragment":
            pspm_json["Pvolume_m3"] = parentMP_json["Pvolume_m3"] + parentSPM_json["Pvolume_m3"]
            PdimensionX_m = pspm_json.get("PdimensionX_m", parentMP_json.get("PdimensionX_m", 0))
            PdimensionY_m = pspm_json.get("PdimensionY_m", parentMP_json.get("PdimensionY_m", 0))
            PdimensionZ_m = pspm_json.get("PdimensionZ_m", parentMP_json.get("PdimensionZ_m", 0))
            pspm_json["CSF"] = PdimensionX_m / math.sqrt(PdimensionY_m * PdimensionZ_m)
            
        else:
            print("Error: unknown shape")
            
        return pspm_json