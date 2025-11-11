from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import Any
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import seaborn as sns
import pandas as pd
import numpy as np
import pymongo
import os
from bson import ObjectId
from io import BytesIO

app = FastAPI(title="Rate Constants Plotting Service", version="1.0.0")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "utopia")
MODEL_COLLECTION = "model_json"
RATE_CONSTANT_COLLECTION = "rate_constant"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
model_json_collection = db[MODEL_COLLECTION]
rate_constant_collection = db[RATE_CONSTANT_COLLECTION]

def create_rateConstants_table_json(model_id,rate_constant_id):
        model_json = model_json_collection.find_one({'_id':ObjectId(model_id)})
        rate_constant_data = rate_constant_collection.find_one({'_id':ObjectId(rate_constant_id)})
        #print("rate_constant_data:", rate_constant_data)

        df_dict = {
            "Pcode":[],
            "Compartment": [],
            "MP_form": [],
            "Size_Bin": [],
            "Rate_Constants": [],
        }

        for p in model_json["system_particle_object_list"]:
            df_dict["Pcode"].append(p["Pcode"])
            df_dict["Compartment"].append(p["Pcompartment_Cname"])
            df_dict["MP_form"].append(p["Pform"])
            df_dict["Size_Bin"].append(p["Pname"][:3])
        for p in rate_constant_data["system_particle_rate_constant_list"]:
            df_dict["Rate_Constants"].append(p["RateConstants"])
    # Print lengths for debugging
        print("Length of Pcode:", len(df_dict["Pcode"]))
        print("Length of Compartment:", len(df_dict["Compartment"]))
        print("Length of MP_form:", len(df_dict["MP_form"]))
        print("Length of Size_Bin:", len(df_dict["Size_Bin"]))
        print("Length of Rate_Constants:", len(df_dict["Rate_Constants"]))

        df = pd.DataFrame(df_dict)
        df2 = df["Rate_Constants"].apply(pd.Series)
        df = df.drop(columns="Rate_Constants")
        df3 = pd.concat([df, df2], axis=1)
        
        
        return df3


def plot_rateConstants_json(model_id,rate_constant_id):
        def sum_if_list(value):
            """Returns the sum of a list if the input is a list, otherwise returns the value itself."""
            return sum(value) if isinstance(value, list) else value

        """(FIX RC for wet deposition, now its given as a list of rate constants per surface compartment only for dry deposition and wet depossition is turned off)This needs to be fixed also for the matrix of interactions and estimation of flows"""
        RC_df = create_rateConstants_table_json(model_id,rate_constant_id)
        rateConstants_df = RC_df.fillna(0)
        selected_columns = rateConstants_df.columns[4:]
        data_raw = RC_df[selected_columns]
        selected_data = data_raw.applymap(sum_if_list)
        log_data = selected_data.applymap(lambda x: np.log10(x) if x > 0 else np.nan)

        # Violin Plot
        plt.figure(figsize=(10, 6))
        sns.violinplot(data=log_data)
        # plt.yscale('log')
        plt.xticks(rotation=90)
        plt.title("Distribution of rate constants as log(k_s-1)")
        plt.show()
        fig = plt.gcf()
        # self.processed_results["RC_violin_plot"] = fig
        return RC_df

@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Rate Constants Plotting Service is running", "status": "healthy"}

@app.get("/rate_constants/{model_id}/{rate_constant_id}")
def get_rate_constants_table(model_id: str, rate_constant_id: str):
    """
    Return the processed rate constants table for a given model.
    """
    try:
        df = create_rateConstants_table_json(model_id, rate_constant_id)
        # 1. Replace +/-inf with NaN
        df = df.replace([np.inf, -np.inf], np.nan)
        # 2. Convert all NaN to None (JSON null)
        df = df.where(pd.notnull(df), None)
        # 3. (optional) Print a warning if you had to clean
        if df.isnull().values.any():
            print("Warning: Some values were NaN or Inf and are now null in JSON.")
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/plot/rate_constants/{model_id}/{rate_constant_id}",
         response_class=Response,
            responses={
                200: {
                    "content": {"image/png": {}},
                    "description": "PNG image of the rate constants violin plot"
                }
            },
            summary="Get rate constants violin plot",
            description="Returns a violin plot (as a PNG image) of the rate constants for the given model.")

def plot_rate_constants(model_id: str, rate_constant_id: str):
    """
    Generate and return the rate constants violin plot for a given model as a PNG image.
    """
    def sum_if_list(value: Any):
        return sum(value) if isinstance(value, list) else value

    try:
        RC_df = create_rateConstants_table_json(model_id,rate_constant_id)
        if RC_df is None or RC_df.empty:
            raise HTTPException(status_code=400, detail="No data available for this model_id.")
        rateConstants_df = RC_df.fillna(0)
        selected_columns = rateConstants_df.columns[4:]
        data_raw = RC_df[selected_columns]
        selected_data = data_raw.applymap(sum_if_list)
        log_data = selected_data.applymap(lambda x: np.log10(x) if x > 0 else np.nan)


        # Violin Plot (Matplotlib only)
        plt.figure(figsize=(10, 6))
        sns.violinplot(data=log_data)
        plt.xticks(range(1, len(log_data.columns)+1), log_data.columns, rotation=90)
        plt.title("Distribution of rate constants as log(k_s-1)")
        plt.xlabel("Process")
        plt.ylabel("log10(rate constant)")
        plt.tight_layout()

        # Save plot to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        return Response(content=buf.read(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))