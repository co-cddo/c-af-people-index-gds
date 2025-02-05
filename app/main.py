from pathlib import Path

import gradio as gr
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from gradio_interfaces import create_gradio_interface
from people_finder_chromadb import PeopleFinder

pf = PeopleFinder("profiles.csv")

app = FastAPI()

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")


@app.get("/orgchart")
async def visualization_page(request: Request):
    return templates.TemplateResponse("visualization.html", {"request": request})


@app.get("/api/org-data")
async def get_org_data():
    # Read your org.csv file
    df = pd.read_csv(
        "org.csv",
        dtype={
            "id": str,
            "parentId": str,
            "name": str,
            "imageUrl": str,
            "title": str,
            "department": str,
        },
        na_values=[""],
        keep_default_na=False,
    )
    df = df.replace({float("nan"): None})

    # Convert DataFrame to list of dictionaries
    data = df.to_dict("records")
    print(data)
    return data


app = gr.mount_gradio_app(app, create_gradio_interface(pf), path="/")
