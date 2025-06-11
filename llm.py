import requests
import os

# Replace with your actual Azure API key
api_key = "D2kx7t7xZnvQdnrZ21Og1LYJDghunWN5FRbtUQgSy9DeHcHGenZMJQQJ99BFACHYHv6XJ3w3AAAAACOGzCGf"
endpoint = "https://rfi-analyser-resource.cognitiveservices.azure.com/openai/deployments/o4-mini/chat/completions?api-version=2025-01-01-preview"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "messages": [
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?"
        },
        {
            "role": "assistant",
            "content": (
                "Paris, the capital of France, is known for its stunning architecture, art museums, historical landmarks, "
                "and romantic atmosphere. Here are some of the top attractions to see in Paris:\n\n"
                "1. The Eiffel Tower: The iconic Eiffel Tower is one of the most recognizable landmarks in the world "
                "and offers breathtaking views of the city.\n"
                "2. The Louvre Museum: The Louvre is one of the world's largest and most famous museums, housing an "
                "impressive collection of art and artifacts, including the Mona Lisa.\n"
                "3. Notre-Dame Cathedral: This beautiful cathedral is one of the most famous landmarks in Paris and is "
                "known for its Gothic architecture and stunning stained glass windows.\n\n"
                "These are just a few of the many attractions that Paris has to offer. With so much to see and do, it's no "
                "wonder that Paris is one of the most popular tourist destinations in the world."
            )
        },
        {
            "role": "user",
            "content": "What is so great about #1?"
        }
    ],
    "max_completion_tokens": 100000,
    "model": "o4-mini"
}

response = requests.post(endpoint, headers=headers, json=data)

print(response.status_code)
print(response.json())