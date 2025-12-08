import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LogNorm
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import pymongo
import os
from bson import ObjectId
from io import BytesIO

app = FastAPI(title="Emission Fraction Plotting Service", version="1.0.0")
#MONGO_URI= "mongodb://utopiauser:utopiapassword@localhost:27018/utopia?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/") 
DB_NAME = os.getenv("DB_NAME", "utopia")
MODEL_COLLECTION = "model_json"
INTERACTION_MATRIX_COLLECTION = "interaction"
RESULT_COLLECTION = "result"
FLOW_COLLECTION = "flow"
RATE_CONSTANT_COLLECTION = "rate_constant"
PARTICLE_STATE_COLLECTION = "particle_state"
FLOW_ESTIMATION_COLLECTION = "flow_estimation"
PROCESSED_RESULT_COLLECTION = "processed_result"
EXPOSURE_INDICATOR_COLLECTION = "exposure_indicator"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
model_json_collection = db[MODEL_COLLECTION]
interaction_collection = db[INTERACTION_MATRIX_COLLECTION]
result_collection = db[RESULT_COLLECTION]
flow_collection = db[FLOW_COLLECTION]
rate_constant_collection = db[RATE_CONSTANT_COLLECTION]
particle_state_collection = db[PARTICLE_STATE_COLLECTION]
flow_estimation_collection = db[FLOW_ESTIMATION_COLLECTION]
processed_result_collection = db[PROCESSED_RESULT_COLLECTION]
exposure_indicator_collection = db[EXPOSURE_INDICATOR_COLLECTION]

class ModelRequest(BaseModel):
    model_id: str
    emission_fraction_id: str

def emission_fractions_plot(emission_fractions_data, emiss_comp):
    import pandas as pd
    import numpy as np

    if len(emiss_comp) == 1:
        emiss_comp = emiss_comp[0]
    else:
        print(
            "The emission compartment is not unique and emission fractions can not be plotted?."
        )
    # emission_fractions_data["y"] =

    data = {
        "x": ["$\phi_1$", "$\phi_21$", "$\phi_22$", "$\phi_23$", "$\phi_24$"],
        "y": [
            np.log10(x) if x > 0 else np.log10(1e-20)
            for x in emission_fractions_data["y"]
        ],
        "category": [
            "$\phi_1$",
            "$\phi_21$:Remote Ocean Surface",
            "$\phi_22$:Remote Ocean Column",
            "$\phi_23$:Remote Ocean Sediments",
            "$\phi_24$:Remote Beaches",
        ],
    }
    df = pd.DataFrame(data)

    # Create a dictionary to map unique categories to colors
    colors = {
        "$\phi_1$": "red",
        "$\phi_21$:Remote Ocean Surface": "blue",
        "$\phi_22$:Remote Ocean Column": "green",
        "$\phi_23$:Remote Ocean Sediments": "orange",
        "$\phi_24$:Remote Beaches": "purple",
    }

    # Plot the DataFrame with different colors per category and add a legend
    fig, ax = plt.subplots()
    for category, color in colors.items():
        df_category = df[df["category"] == category]
        ax.scatter(
            df_category["x"],
            df_category["y"],
            c=color,
            label=category,
            marker="_",
            s=100,
        )

    ax.set_ylim([-12, 0])
    plt.ylabel(
        "log10($\phi$)",
        fontsize=14,
    )
    plt.xlabel(
        "Emission Fraction",
        fontsize=14,
    )

    plt.title(
        "Mass Emission Fractions after emissions to " + emiss_comp,
        fontsize=14,
    )

    # Set the legend outside the plot and at the bottom
    plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=14)
    plt.tight_layout()
    fig = plt.gcf()
    # plt.show()
    return fig

def _respond_with_png(fig) -> Response:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png", headers={"Cache-Control": "no-store"})

@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Emission Fraction Plotting Service is running", "status": "healthy"}

@app.get(
    "/plot/emission_fraction/{model_id}/{emission_fraction_id}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "emission fraction figure"}}
)
def plot_emission_fraction(model_id: str, emission_fraction_id: str):
    try:
        emission_fractions_mass_data = pd.DataFrame(exposure_indicator_collection.find_one({"_id":ObjectId(emission_fraction_id)})["emission_fraction_mass"])
        model_json = model_json_collection.find_one({'_id':ObjectId(model_id)})
        emiss_comp = []
        for compartment, size_fractions in model_json["emiss_dict_g_s"].items():
                for fraction, value in size_fractions.items():
                    if value > 0:
                        emiss_comp.append(compartment)
        fig = emission_fractions_plot(emission_fractions_mass_data, emiss_comp)
        return _respond_with_png(fig)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))