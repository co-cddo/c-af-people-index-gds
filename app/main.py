import gradio as gr
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from gradio_interfaces import manage_profile_interface, search_profile_interface
from people_finder_chromadb import PeopleFinder

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

pf = PeopleFinder("profiles.csv")

# Create Gradio apps
search_interface = search_profile_interface(pf)
manage_interface = manage_profile_interface(pf)

# Mount Gradio apps at specific paths
app = gr.mount_gradio_app(app, search_interface, path="/gradio-search")
app = gr.mount_gradio_app(app, manage_interface, path="/gradio-manage")


# Create GOV.UK wrapped routes
@app.get("/")
async def search_page(request: Request):
    return templates.TemplateResponse(
        "gradio_page.html",
        {
            "request": request,
            "title": "Search People",
            "gradio_version": gr.__version__,
            "gradio_url": "/gradio-search",
        },
    )


@app.get("/manage")
async def manage_page(request: Request):
    return templates.TemplateResponse(
        "gradio_page.html",
        {
            "request": request,
            "title": "Manage Profiles",
            "gradio_version": gr.__version__,
            "gradio_url": "/gradio-manage",
        },
    )


@app.get("/api/org-data")
async def get_org_data():
    df = pd.read_csv(
        "profiles.csv",
        # id,parentId, name,email,job_title,grade,location,team,area,unit,directorate,department,skills,experience
        dtype={
            "id": str,
            "parentId": str,
            "name": str,
            "email": str,
            "grade": str,
            "location": str,
            "team": str,
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


# Your existing org chart route
@app.get("/orgchart")
async def visualization_page(request: Request):
    return templates.TemplateResponse("visualization.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")
