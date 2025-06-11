import os
import yaml
from openai import AzureOpenAI
import concurrent.futures

endpoint = "https://rfi-analyser-resource.cognitiveservices.azure.com/"
model_name = "gpt-4o"
deployment = "gpt-4o"

subscription_key = "3ZKsWfold1xEyHPOLADYYDTRlsTUhjqPLIYE4NKd6MW1KhJXdo7sJQQJ99BFAC5RqLJXJ3w3AAAAACOGUZPH"
api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

def query_category(category, prompts):
    all_responses = []
    for prompt in prompts:
        response = client.chat.completions.create(
            stream=False,
            messages=[
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=1.0,
            top_p=1.0,
            model=deployment,
        )
        if response.choices:
            all_responses.append(response.choices[0].message.content)
    with open(f"{category}.md", "w") as out_f:
        for resp in all_responses:
            out_f.write(resp + "\n\n")

def main():
    # Load queries.yaml
    with open("queries.yaml", "r") as f:
        queries = yaml.safe_load(f)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(query_category, entry["category"], entry["prompts"])
            for entry in queries
        ]
        concurrent.futures.wait(futures)

    client.close()

if __name__ == "__main__":
    main()