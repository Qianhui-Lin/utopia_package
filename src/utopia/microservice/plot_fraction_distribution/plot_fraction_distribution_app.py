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
from typing import Any
import math

app = FastAPI(title="Fraction Distribution Plotting Service", version="1.0.0")

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

def plot_fractionDistribution_heatmaps_json(result, fraction):
        """Plots the mass and number fractions after they have been extracted to the Results_extended df."""
        # Define the order for the MP_Form labels
        mp_form_order = [
            "freeMP",
            "heterMP",
            "biofMP",
            "heterBiofMP",
        ]  # Replace with your desired order

        # Define the order for the Compartment labels
        compartment_order = [
            "Ocean_Surface_Water",
            "Ocean_Mixed_Water",
            "Ocean_Column_Water",
            "Coast_Surface_Water",
            "Coast_Column_Water",
            "Surface_Freshwater",
            "Bulk_Freshwater",
            "Sediment_Freshwater",
            "Sediment_Ocean",
            "Sediment_Coast",
            "Beaches_Soil_Surface",
            "Beaches_Deep_Soil",
            "Background_Soil_Surface",
            "Background_Soil",
            "Impacted_Soil_Surface",
            "Impacted_Soil",
            "Air",
        ]  # Replace with your desired order

        # Pivot the DataFrame to have one row per combination of MP_Form, Compartment, and Size_Fraction_um
        results_extended_df = pd.DataFrame(result["processed_result"])
        pivot_table = results_extended_df.pivot_table(
            index=["MP_Form", "Size_Fraction_um"],
            columns="Compartment",
            values=fraction,
            aggfunc="mean",
        )

        # Reorder the rows based on mp_form_order and columns based on compartment_order
        pivot_table = pivot_table.loc[mp_form_order, compartment_order]

        # Apply log scale to the pivot table
        pivot_table_log = np.log10(pivot_table)

        # Replace -inf values with NaN
        pivot_table_log.replace(-np.inf, np.nan, inplace=True)

        # Stablish a lower limit
        # Set the lower limit for the values
        lower_limit = -14
        upper_limit = np.nanmax(pivot_table_log)

        # Replace values below the lower limit with NaN
        pivot_table_log = pivot_table_log.applymap(
            lambda x: np.nan if x < lower_limit else x
        )

        # Define a custom colormap with grey color for NaN values
        cmap = sns.color_palette("viridis", as_cmap=True)
        cmap.set_bad("white")

        # Plot the heatmap with logarithmic scale and custom colormap
        plt.figure(figsize=(12, 8))
        sns.heatmap(
            pivot_table_log,
            cmap=cmap,
            cbar=True,
            cbar_kws={"label": "log10 (" + fraction + ") "},
            annot=False,
            linewidths=0.5,
            linecolor="grey",
            vmin=lower_limit,
            vmax=upper_limit,
        )

        # Set compartment labels to cover all size fractions underneath
        compartment_labels = pivot_table.columns
        compartment_label_positions = np.arange(len(compartment_labels)) + 0.5
        plt.xticks(
            ticks=compartment_label_positions, labels=compartment_labels, rotation=90
        )

        # Set MP_Form and Size_Fraction_um labels
        row_labels = [
            f"{mp_form} - {size_frac_um}" for mp_form, size_frac_um in pivot_table.index
        ]
        row_label_positions = np.arange(len(pivot_table.index)) + 0.5
        plt.yticks(ticks=row_label_positions, labels=row_labels, rotation=0)
        titlename = (
            "Heatmap of log10 ("
            + fraction
            + " by MP_Form, Compartment, and Size_Fraction_um"
        )
        plt.title(titlename)
        plt.xlabel("Compartment", fontsize=14)
        plt.ylabel("MP_Form - Size_Fraction_um", fontsize=14)
        plt.tight_layout()

        fig = plt.gcf()

        return fig  # , titlename

def _respond_with_png(fig) -> Response:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png", headers={"Cache-Control": "no-store"})

@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Fraction Distribution Plotting Service is running", "status": "healthy"}

@app.get(
    "/plot/fraction_distribution/mass/{model_id}/{processed_result_id}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "PNG mass-fraction heatmap"}}
)
def plot_mass_fraction(model_id: str, processed_result_id: str):
    try:
        processed_results = processed_result_collection.find_one({"_id": ObjectId(processed_result_id)})
        if not processed_results:
            raise HTTPException(status_code=404, detail="Processed result not found")
        fig = plot_fractionDistribution_heatmaps_json(processed_results, "mass_fraction")
        return _respond_with_png(fig)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/plot/fraction_distribution/number/{model_id}/{processed_result_id}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "PNG number-fraction heatmap"}}
)
def plot_number_fraction(model_id: str, processed_result_id: str):
    try:
        processed_results = processed_result_collection.find_one({"_id": ObjectId(processed_result_id)})
        if not processed_results:
            raise HTTPException(status_code=404, detail="Processed result not found")
        fig = plot_fractionDistribution_heatmaps_json(processed_results, "number_fraction")
        return _respond_with_png(fig)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/plot/fraction_distribution/mass/normalised/{model_id}/{processed_result_id}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "PNG normalised mass-fraction bar chart"}}
)
def plot_mass_fraction_normalised(model_id: str, processed_result_id: str):
    try:
        processed_results = processed_result_collection.find_one({"_id": ObjectId(processed_result_id)})

        if not processed_results:
            raise HTTPException(status_code=404, detail="Processed result not found")

        df= pd.DataFrame(processed_results["processed_result"])

        # First normalize concentrations within each compartment
        df_norm = df.copy()
        df_norm["normalized_conc"] = df_norm.groupby("Compartment")["concentration_g_m3"].transform(
            lambda x: x / x.sum()
        )

        # Get all compartments
        compartments = df_norm["Compartment"].unique()
        n_compartments = len(compartments)

        # Choose subplot grid size (approx. square)
        ncols = 4
        nrows = math.ceil(n_compartments / ncols)

        # Plot
        fig, axes = plt.subplots(nrows, ncols, figsize=(4*ncols, 3*nrows), sharey=True)

        for ax, comp in zip(axes.flat, compartments):
            subset = df_norm[df_norm["Compartment"] == comp].sort_values("Size_Fraction_um")
            ax.bar(subset["Size_Fraction_um"].astype(str), subset["normalized_conc"])
            ax.set_title(comp, fontsize=9)
            ax.set_xlabel("Size (µm)")
            ax.set_ylabel("Relative contribution")
            ax.tick_params(axis="x", rotation=45)

        # Remove empty subplots if any
        for ax in axes.flat[n_compartments:]:
            ax.axis("off")

        plt.tight_layout()
        fig = plt.gcf()
        return _respond_with_png(fig)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get(
    "/plot/fraction_distribution/number/normalised/{model_id}/{processed_result_id}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "PNG normalised number-fraction bar chart"}}
)
def plot_number_fraction_normalised(model_id: str, processed_result_id: str):
    try:
        processed_results = processed_result_collection.find_one({"_id": ObjectId(processed_result_id)})

        if not processed_results:
            raise HTTPException(status_code=404, detail="Processed result not found")

        df= pd.DataFrame(processed_results["processed_result"])

        # First normalize concentrations within each compartment
        df_norm = df.copy()
        df_norm["normalized_conc"] = df_norm.groupby("Compartment")["concentration_num_m3"].transform(
    lambda x: x / x.sum()
)

        # Get all compartments
        compartments = df_norm["Compartment"].unique()
        n_compartments = len(compartments)

        # Choose subplot grid size (approx. square)
        ncols = 4
        nrows = math.ceil(n_compartments / ncols)

        # Plot
        fig, axes = plt.subplots(nrows, ncols, figsize=(4*ncols, 3*nrows), sharey=True)

        for ax, comp in zip(axes.flat, compartments):
            subset = df_norm[df_norm["Compartment"] == comp].sort_values("Size_Fraction_um")
            ax.bar(subset["Size_Fraction_um"].astype(str), subset["normalized_conc"])
            ax.set_title(comp, fontsize=9)
            ax.set_xlabel("Size (µm)")
            ax.set_ylabel("Relative contribution")
            ax.tick_params(axis="x", rotation=45)

        # Remove empty subplots if any
        for ax in axes.flat[n_compartments:]:
            ax.axis("off")

        plt.tight_layout()
        fig = plt.gcf()
        return _respond_with_png(fig)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))