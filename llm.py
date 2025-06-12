import os
import yaml
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient
import concurrent.futures
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import textwrap


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

def clear_llm_response_folder():
    """
    Clears the llm-response folder by removing all JSON files.
    """
    import os
    import glob
    folder = "./llm-response"
    files = glob.glob(os.path.join(folder, "*.json"))
    for file in files:
        try:
            print(f"Removing file: {file}")
            os.remove(file)
        except Exception as e:
            print(f"Error removing file {file}: {e}")

def main():
    vendors = list_unique_vendors()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for vendor in vendors:
            futures.append(executor.submit(process_vendor, vendor))
        concurrent.futures.wait(futures)
    # After processing all vendors, process summaries
    for vendor in vendors:    
        process_vendor_summary(vendor)
        generate_vendor_pdf_report(vendor)

def process_vendor(vendor):
    xls = load_xls(f"{vendor} - RFP.xlsx")
    if xls is None:
        print(f"No sheet for {vendor}")
        return
    vendor_results = []
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
            print(f"Processing prompt for {vendor} -- {uid}")
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
              import json
              try:
                result = json.loads(response.choices[0].message.content)
                result['ability'] = ability
                result['category'] = category.split('.')[1].strip('') if category and '.' in category else category
                result['capability'] = capability
                result['uid'] = uid
                result['offering'] = offering
                result['interfaces'] = intefaces
                vendor_results.append(result)
              except Exception as e:
                  print(f"Error writing JSON for {vendor} {uid}: {e}")
    # Write all results for this vendor to a single file
    if vendor_results:
        import json
        with open(f"./llm-response/{vendor}.json", "w") as f:
            json.dump(vendor_results, f, ensure_ascii=False, indent=2)

def process_vendor_summary(vendor):
    """
    Processes all responses for a vendor from the vendor's JSON file and prepares a summary using the 'offering' and 'interfaces' fields.
    The prompt is left empty for now.
    Returns a list of dicts with at least: uid, offering, interfaces, and any other fields you want to include.
    """
    import json
    vendor_file = f"./llm-response/{vendor}.json"
    if not os.path.exists(vendor_file):
        print(f"No JSON file for vendor: {vendor}")
        return []
    with open(vendor_file, "r") as f:
        responses = json.load(f)
    summary = []
    for obj in responses:
        summary.append({
            "uid": obj.get("uid"),
            "offering": obj.get("offering"),
            "interfaces": obj.get("interfaces"),
        })
    

    # Aggregate all offerings and interfaces into a single string for summary
    offerings = "\n".join(str(item.get("offering", "")) for item in summary if item.get("offering"))
    interfaces = "\n".join(str(item.get("interfaces", "")) for item in summary if item.get("interfaces"))

    prompt = f"""
You are a professional RFP analyst tasked with generating a concise and factual summary of a vendor's submission to an RFP. You will be provided with the vendor's complete set of responses to all RFP criteria.
Your job is to:
Summarize the vendor's offering, using their own terminology where possible.
Capture the main capabilities, key differentiators, and architectural or interface components they emphasize.
Reflect the intended use cases, benefits, and design philosophy as presented by the vendor.
Do not add interpretation, assumptions, or external context. Stick strictly to what is written.
Your summary should:
Be objective and neutral in tone.
Highlight only what the vendor has provided, without omissions or commentary.
Be written in maximum 200 words. Make it in pretty format.
Offerings: 
{offerings}
Interfaces:
{interfaces}
    """
    with open(f"./prompts/{vendor}-summary.prompt", "w") as out_f:
        out_f.write(f"{prompt}")
    
    print(f"Processing Summary for {vendor} ")
    response = client.chat.completions.create(
            stream=False,
            messages=[
                {"role": "user", "content": f"{prompt}"},
            ],
            max_tokens=4096,
            temperature=1.0,
            top_p=1.0,
            model=deployment,
            )
    if response.choices:
            with open(f"./llm-response/{vendor}-summary.md", "w") as f:
                f.write(response.choices[0].message.content)

def generate_vendor_pdf_report(vendor):
    """
    Generate a PDF report for a vendor, including summary and all UID responses.
    PDF is saved as 'Vendor X Report.pdf' in the root folder.
    Each UID entry is rendered as labeled paragraphs, not as a table.
    """
    import os, json
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.units import inch

    # Load summary (markdown)
    summary_path = f"./llm-response/{vendor}-summary.md"
    summary = ""
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = f.read()
    # Load all responses
    json_path = f"./llm-response/{vendor}.json"
    if not os.path.exists(json_path):
        print(f"No JSON file for vendor: {vendor}")
        return
    with open(json_path, "r", encoding="utf-8") as f:
        responses = json.load(f)
    # PDF setup
    pdf_path = f"./llm-response/{vendor} Report.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading1"]
    styleH2 = styles["Heading2"]
    styleH3 = styles["Heading3"]
    styleMono = ParagraphStyle('Mono', parent=styleN, fontName='Courier', fontSize=9, leading=12)
    styleLabel = ParagraphStyle('Label', parent=styleN, fontName='Helvetica-Bold', fontSize=9, leading=12)
    elements = []
    # Title
    elements.append(Paragraph(f"<b>{vendor} RFI/LLM Report</b>", styleH))
    elements.append(Spacer(1, 0.2*inch))
    # Summary
    if summary:
        elements.append(Paragraph("<b>Summary</b>", styleH2))
        for para in summary.split('\n\n'):
            elements.append(Paragraph(para.replace('\n', '<br/>'), styleN))
            elements.append(Spacer(1, 0.1*inch))
        elements.append(Spacer(1, 0.2*inch))
    # Detailed Responses as paragraphs
    elements.append(Paragraph("<b>Detailed Responses</b>", styleH2))
    for idx, obj in enumerate(responses):
        elements.append(Paragraph(f"<b>{obj.get('category', '')} - {obj.get('capability', '')} ({obj.get('uid', '')})</b>", styleH3))
        elements.append(Paragraph(f"<b>Requirment:</b> {obj.get('ability', '')}", styleN))
        elements.append(Paragraph(f"<b>Offering:</b> {obj.get('offering', '')}", styleN))
        elements.append(Paragraph(f"<b>Interfaces:</b> {obj.get('interfaces', '')}", styleN))
        elements.append(Paragraph(f"<b>AI Justification:</b> {obj.get('justification', '')}", styleN))
        elements.append(Paragraph(f"<b>Score:</b> {obj.get('score', '')}", styleN))
        elements.append(Spacer(1, 0.18*inch))
        if idx and idx % 8 == 0:
            elements.append(PageBreak())
    doc.build(elements)
    print(f"PDF report generated: {pdf_path}")

# CLI entry point
if __name__ == "__main__":
    clear_llm_response_folder()
    main()
