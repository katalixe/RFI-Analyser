import os
import yaml
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient
import concurrent.futures
import pandas as pd
from io import BytesIO


#endpoint = "https://foundry-ms.openai.azure.com/"
endpoint = 'https://foundry-ms.openai.azure.com/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview'
model_name = "gpt-4o"
deployment = "gpt-4o"

subscription_key = os.getenv("SUBSCRIPTION_KEY")
api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

# def query_category(category, prompts):
#     all_responses = []
#     for vendor in list_unique_vendors():
#       for prompt in prompts:
#           print("Processing {0} -- {1}".format(vendor, category))
#           #print(("Use '{0} - Executive Summary.docx' and '{0} - RFP.xlsx'. {1}").format(vendor, prompt))
#           response = client.chat.completions.create(
#               stream=False,
#               messages=[
#                   {"role": "user", "content": prompt},
#               ],
#               max_tokens=4096,
#               temperature=1.0,
#               top_p=1.0,
#               model=deployment,
#           )
#           if response.choices:
#               all_responses.append(response.choices[0].message.content)
#       with open(f"./llm-response/{category}-{vendor}.md", "w") as out_f:
#           for resp in all_responses:
#               out_f.write(resp + "\n\n")

# def list_azure_files():
#   # Replace with your Azure Storage connection string
#   connection_string = os.getenv("CONNECTION_STRING")
#   container_name = "resources"  # Update if your container name is different
#   prefix = "data/"
#   if not connection_string:
#     return {"error": "AZURE_STORAGE_CONNECTION_STRING environment variable not set."}
#   try:
#     blob_service_client = BlobServiceClient.from_connection_string(connection_string)
#     container_client = blob_service_client.get_container_client(container_name)
#     files = [
#       os.path.basename(blob.name)
#       for blob in container_client.list_blobs(name_starts_with=prefix)
#       if blob.name.startswith(prefix)
#     ]
#     return {"files": files}
#   except Exception as e:
#     return {"error": str(e)}

def list_unique_vendors():
    # Use the same logic as list_azure_files to get files
    connection_string = os.getenv("CONNECTION_STRING")
    container_name = "resources"
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
        vendors = sorted(set(f.split("-")[0].strip(" ") for f in files if "-" in f))
        return vendors
    except Exception as e:
        return {"error": str(e)}

def load_xls(filename):
    """
    Downloads the specified XLS/XLSX file from Azure Blob Storage,
    loads the 'CPT-V1' sheet, and returns it as a pandas DataFrame.
    """
    import pandas as pd
    from io import BytesIO
    connection_string = os.getenv("CONNECTION_STRING")
    container_name = "resources"
    prefix = "data/"
    if not connection_string:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING environment variable not set.")
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(f"{prefix}{filename}")
        blob_data = blob_client.download_blob().readall()
        excel_file = BytesIO(blob_data)
        try:
            sheet_names = pd.ExcelFile(excel_file).sheet_names
            if len(sheet_names) < 2:
              raise ValueError("Excel file does not have a second sheet.")
            df = pd.read_excel(excel_file, sheet_name=sheet_names[1])
            return df
        except Exception as e:
            print(f"Failed to load CPT-V1 from {filename}: {e}")
            return None
    except Exception as e:
        print(f"Azure error: {e}")
        return None


def main():
    vendors = list_unique_vendors()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for vendor in vendors:
            futures.append(executor.submit(process_vendor, vendor))
        concurrent.futures.wait(futures)

def process_vendor(vendor):
    xls = load_xls(f"{vendor} - RFP.xlsx")
    if xls is None:
        print(f"No sheet for {vendor}")
        return
    for idx, row in xls.iloc[5:].iterrows():  # Start from row 6 (index 5)
        category = row.iloc[0] if len(row) > 0 else None
        uid = row.iloc[1] if len(row) > 1 else None
        capability = row.iloc[2] if len(row) > 2 else None
        ability = row.iloc[3] if len(row) > 3 else None
        purpose = row.iloc[4] if len(row) > 4 else None
        offering = row.iloc[7] if len(row) > 7 else None
        intefaces = row.iloc[8] if len(row) > 8 else None
        if uid:
            prompt_prefix = f"This is about {vendor}"
            prompt_suffix = (f"Offering:\n{offering}\nInterfaces:\n{intefaces}\nAbility:\n{ability} {purpose}")
            prompt= """
You are an expert RFP analyst responsible for evaluating a vendor's response to a specific Request for Proposal (RFP) criterion. You will receive structured input consisting of the vendor's Offering, Interfaces and Ability. The Ability is supplied by the issuer and should be seen as the requirement as requested.
Your task is to:
Strictly analyze the input content without making assumptions or adding information that is not explicitly stated.
Factually evaluate how well the information supports the criterion (you will not be given the criterion explicitly, assume it is clear from context).
Provide a short explanation (max 100 words) justifying your evaluation, citing exact phrases or elements from the input.
Assign a score between 1 and 10, where:
1 = Does not address the requirement at all
5 = Partially addresses the requirement with limited evidence or vague statements
10 = Fully and clearly meets the requirement with strong, explicit support
But you need to be very strict here. The answers should follow a gaussian curve. If the answer is too perfect, that should be cause of suspicion as well.
Your output should be structured in JSON format as follows:
{"score": <integer between 1 and 10>,"justification": "<short explanation with direct references to vendor text>" }

            """
            with open(f"./prompts/{vendor}-{uid}.prompt", "w") as out_f:
                out_f.write(f"{prompt_prefix} {prompt} {prompt_suffix}")
            response = client.chat.completions.create(
                stream=False,
                messages=[
                    {"role": "user", "content": f"{prompt_prefix} {prompt} {prompt_suffix}"},
                ],
                max_tokens=4096,
                temperature=1.0,
                top_p=1.0,
                model=deployment,
            )
            if response.choices:
              # Add 'ability' to the output JSON
              import json
              try:
                result = json.loads(response.choices[0].message.content)
                result['ability'] = ability
                result['category'] = category.split('.')[1].strip('')
                result['capability'] = capability
                with open(f"./llm-response/{vendor}_{uid}.json", "w") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
              except Exception as e:
                  print(f"Error writing JSON for {vendor} {uid}: {e}")



if __name__ == "__main__":
    main()