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

app = FastAPI(title="Compartment Distribution Plotting Service", version="1.0.0")
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

class ModelRequest(BaseModel):
    model_id: str
    processed_result_id :str

def plot_compartment_distribution(
        processed_results, mass_or_number
    ):  # mass_or_number: "%_mass" or ""%_number""
        """Bar chart plot of the mass or particle number distribution of particles by compartment."""
        compartment_colors = {
            "Ocean_Surface_Water": "#756bb1",
            "Ocean_Mixed_Water": "#756bb1",
            "Ocean_Column_Water": "#756bb1",
            "Coast_Surface_Water": "#2c7fb8",
            "Coast_Column_Water": "#2c7fb8",
            "Surface_Freshwater": "#9ebcda",
            "Bulk_Freshwater": "#9ebcda",
            "Sediment_Freshwater": "#fdae6b",
            "Sediment_Ocean": "#fdae6b",
            "Sediment_Coast": "#fdae6b",
            "Beaches_Soil_Surface": "#ffeda0",
            "Beaches_Deep_Soil": "#ffeda0",
            "Background_Soil_Surface": "#e5f5e0",
            "Background_Soil": "#e5f5e0",
            "Impacted_Soil_Surface": "#d95f0e",
            "Impacted_Soil": "#d95f0e",
            "Air": "#deebf7",
        }

        # Sort and round the values
        df = (
            pd.DataFrame(processed_results["results_by_comp"])[["Compartments", mass_or_number]]
            .round(2)
            .sort_values(by=mass_or_number, ascending=False)
        )

        # Get the list of colors based on the Compartments in the df
        bar_colors = df["Compartments"].map(compartment_colors)

        # Plot
        fig, ax = plt.subplots(figsize=(8, len(df) * 0.4))
        bars = ax.barh(df["Compartments"], df[mass_or_number], color=bar_colors)

        # Fix x-axis to 100%
        ax.set_xlim(0, 100)

        # Add labels to bars
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + 1, bar.get_y() + bar.get_height() / 2, f"{width}%", va="center"
            )

        # Labels and formatting
        ax.set_xlabel(mass_or_number)
        ax.set_ylabel("Compartments")
        ax.set_title(f"{mass_or_number} Distribution by Compartment")
        ax.invert_yaxis()  # To match sorting order

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
    return {"message": "Compartment Distribution Plotting Service is running", "status": "healthy"}


@app.get(
    "/plot/compartment_distribution/mass/{model_id}/{processed_result_id}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "compartment distribution figure (mass)"}}
)
def plot_mass_compartment_distribution(model_id: str, processed_result_id: str):
    try:
        processed_results = processed_result_collection.find_one({"_id": ObjectId(processed_result_id)})
        if not processed_results:
            raise HTTPException(status_code=404, detail="Processed result not found")
        fig = plot_compartment_distribution(processed_results, "%_mass")
        return _respond_with_png(fig)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/plot/compartment_distribution/number/{model_id}/{processed_result_id}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "compartment distribution figure (number)"}}
)
def plot_number_compartment_distribution(model_id: str, processed_result_id: str):
    try:
        processed_results = processed_result_collection.find_one({"_id": ObjectId(processed_result_id)})
        if not processed_results:
            raise HTTPException(status_code=404, detail="Processed result not found")
        fig = plot_compartment_distribution(processed_results, "%_number")
        return _respond_with_png(fig)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))