from fastapi import FastAPI
import yaml

app = FastAPI()

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
