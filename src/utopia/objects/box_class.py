class Box:
    """Class box generates one object box representing the unit world in the case of the UTOPIA parameterization that can contain 17 compartments and that can have connexions to other boxes (for example if conecting several UTOPIA boxes to give spatial resolution to a global model)"""

    description = "Generic Box class"

    def __init__(
        self,
        Bname,
        Bdepth_m=None,
        Blength_m=None,
        Bwidth_m=None,
        Bvolume_m3=None,
        Bconexions=None,
    ):
        # Assign attributes to self (instance attributes). Those set up as None are optional attributes
        self.Bname = Bname  # name of the box
        self.Bdepth_m = Bdepth_m  # depth of the box
        self.Blength_m = Blength_m  # length of the box
        self.Bwidth_m = Bwidth_m  # width of the box
        self.Bvolume_m3 = Bvolume_m3  # volume of the box
        self.compartments = []  # list of compartments in the box
        self.Bconexions = Bconexions  # conexions to other model boxes

    def __repr__(self):
        return (
            "{"
            + self.Bname
            + ", "
            + str(self.Bdepth_m)
            + ", "
            + str(self.Blength_m)
            + ", "
            + str(self.Bwidth_m)
            + "}"
        )

    def add_compartment(self, comp):
        self.compartments.append(comp)
        comp.assign_box(self)

    def calc_Bvolume_m3(self):
        if self.Bvolume_m3 is None:
            if any(
                attr is None for attr in [self.Bdepth_m, self.Blength_m, self.Bwidth_m]
            ):
                print(
                    "Missing parameters needded to calculate Box volume --> calculating based on compartments volume"
                )
                if len(self.compartments) == 0:
                    print(
                        "No compartments assigned to this model box --> use add_compartment(comp)"
                    )
                else:
                    vol = []
                    for c in range(len(self.compartments)):
                        if self.compartments[c].Cvolume_m3 is None:
                            print(
                                "Volume of compartment "
                                + self.compartments[c].Cname
                                + " is missing"
                            )
                            continue
                        else:
                            vol.append(self.compartments[c].Cvolume_m3)
                    self.Bvolume_m3 = sum(vol)
            else:
                self.Bvolume_m3 = self.Bdepth_m * self.Blength_m * self.Bwidth_m
                # print("Box volume: " + str(self.Bvolume_m3)+" m3")
        else:
            print("Box volume already assigned: " + str(self.Bvolume_m3) + " m3")
