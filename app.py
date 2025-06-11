from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import yaml

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Load queries from YAML
def load_yaml_queries(filename="queries.yaml"):
    with open(filename, "r") as f:
        data = yaml.safe_load(f)
    return data

@app.get("/categories/")
def get_categories():
    queries = load_yaml_queries()
    return queries

# Endpoint to get prompts from a specific category
@app.get("/category/{category_name}")
def get_category_prompts(category_name: str):
    queries = load_yaml_queries()
    for category in queries:
        if category["category"] == category_name:
            return category["prompts"]
    return {"error": "Category not found"}


def load_yaml_queries(filename="queries.yaml"):
    with open(filename, "r") as f:
        return yaml.safe_load(f)

@app.get("/")
def home(request: Request):
    queries = load_yaml_queries()
    categories = [category["category"] for category in queries]
    return templates.TemplateResponse("index.html", {"request": request, "categories": categories})
