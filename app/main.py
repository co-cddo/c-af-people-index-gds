import logging

import gradio as gr
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from gradio_interfaces import (
    manage_profile_interface,
    search_profile_interface,
    view_profile_data,
)
from people_finder_chromadb import PeopleFinder

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    data = df.to_dict("records")
    return data


# Mount Gradio apps with explicit paths
logger.info("Mounting Gradio apps...")

# Create and mount the Gradio apps
blocks_search = search_profile_interface(pf)
blocks_manage = manage_profile_interface(pf)
blocks_view = view_profile_data(pf)


@app.get("/view", include_in_schema=False)
async def redirect_view():
    return RedirectResponse(url="/view/")


@app.get("/manage", include_in_schema=False)
async def redirect_manage():
    return RedirectResponse(url="/manage/")


# Mount each Blocks interface
app = gr.mount_gradio_app(app, blocks_manage, path="/manage")
app = gr.mount_gradio_app(app, blocks_view, path="/view")
app = gr.mount_gradio_app(app, blocks_search, path="/")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting server...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")
