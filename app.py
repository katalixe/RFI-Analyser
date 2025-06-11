from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import PlainTextResponse
import yaml
import os

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

# @app.get("/category_content/{category_name}", response_class=HTMLResponse)
# def get_category_content(category_name: str):
#     filename = f"{category_name}.txt"
#     if not os.path.exists(filename):
#         return f"<h2>No content found for category: {category_name}</h2>"
#     with open(filename, "r") as f:
#         content = f.read()
#     # Simple HTML formatting for display
#     return f"<h2>Content for {category_name}</h2><pre>{content}</pre>"

@app.get("/")
def home(request: Request):
    queries = load_yaml_queries()
    categories = [category["category"] for category in queries]
    return templates.TemplateResponse("index.html", {"request": request, "categories": categories})

@app.get("/category/{category_name}/llm_response")
def get_llm_response(category_name: str):
    filename = f"{category_name}.md"
    if not os.path.exists(filename):
        return {"error": f"No content found for category: {category_name}"}
    with open(filename, "r") as f:
        content = f.read()
    return {"response": content}
