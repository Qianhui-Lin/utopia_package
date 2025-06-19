import json

def create_box_json(
    Bname,
    Bdepth_m=None,
    Blength_m=None,
    Bwidth_m=None,
    Bvolume_m3=None,
    Bconexions=None,
):
    if compartments is None:
        compartments = []
    
    box_dict = {
        "Bname": Bname,
        "Bdepth_m": Bdepth_m,
        "Blength_m": Blength_m,
        "Bwidth_m": Bwidth_m,
        "Bvolume_m3": Bvolume_m3,
        "Bconexions": Bconexions,
        "compartments": [],
        "description": "Generic Box class"
    }
    
    return json.dumps(box_dict, indent=2, ensure_ascii=False)

def add_compartment_to_json(box_json_str, compartment_dict):
    """Add a compartment to an existing box JSON string"""
    # Parse JSON string to dictionary
    box_dict = json.loads(box_json_str)
    
    # Add compartment
    box_dict["compartments"].append(compartment_dict)
    
    # Return updated JSON string
    return json.dumps(box_dict, indent=2, ensure_ascii=False)


def calc_volume_from_json(box_json_str):
    """Calculate volume for a box from JSON string"""
    # Parse JSON string to dictionary
    box_dict = json.loads(box_json_str)
    
    if box_dict["Bvolume_m3"] is None:
        # Try to calculate from dimensions
        if all(attr is not None for attr in [box_dict["Bdepth_m"], box_dict["Blength_m"], box_dict["Bwidth_m"]]):
            box_dict["Bvolume_m3"] = box_dict["Bdepth_m"] * box_dict["Blength_m"] * box_dict["Bwidth_m"]
            print(f"Box volume calculated: {box_dict['Bvolume_m3']} m3")
        else:
            # Calculate from compartments
            print("Missing parameters needed to calculate Box volume --> calculating based on compartments volume")
            if len(box_dict["compartments"]) == 0:
                print("No compartments assigned to this model box")
            else:
                vol = []
                for comp in box_dict["compartments"]:
                    if comp.get("Cvolume_m3") is None:
                        print(f"Volume of compartment {comp.get('Cname', 'Unknown')} is missing")
                        continue
                    else:
                        vol.append(comp["Cvolume_m3"])
                if vol:
                    box_dict["Bvolume_m3"] = sum(vol)
    else:
        print(f"Box volume already assigned: {box_dict['Bvolume_m3']} m3")
    
    # Return updated JSON string
    return json.dumps(box_dict, indent=2, ensure_ascii=False)


