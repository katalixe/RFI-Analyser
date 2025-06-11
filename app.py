from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import PlainTextResponse
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
import yaml
import os
from azure.storage.blob import BlobServiceClient

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

@app.get("/azure-files")
def list_azure_files():
  # Replace with your Azure Storage connection string
  connection_string = os.getenv("CONNECTION_STRING")
  container_name = "resources"  # Update if your container name is different
  prefix = "data/"
  if not connection_string:
    return {"error": "AZURE_STORAGE_CONNECTION_STRING environment variable not set."}
  try:
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    files = [
      os.path.basename(blob.name)
      for blob in container_client.list_blobs(name_starts_with=prefix)
      if blob.name.startswith(prefix)
    ]
    return {"files": files.sort()}
  except Exception as e:
    return {"error": str(e)}

@app.get("/list-llm-files")
def list_llm_files():
    folder = "llm-response"
    files = [f for f in os.listdir(folder) if f.endswith('.json')]
    return {"files": sorted(files)}

@app.get("/llm-response/{filename}")
def get_llm_file(filename: str):
    folder = "llm-response"
    file_path = os.path.join(folder, filename)
    if not os.path.exists(file_path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    with open(file_path, "r") as f:
        import json
        data = json.load(f)
    return JSONResponse(data)

