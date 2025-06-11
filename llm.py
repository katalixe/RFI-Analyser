from openai import OpenAI  # Example with OpenAI API

def get_llm_response(prompt: str):
    response = OpenAI().chat_completion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

@app.get("/category/{category_name}/llm_response")
def get_llm(category_name: str):
    queries = load_yaml_queries()
    for category in queries:
        if category["category"] == category_name:
            prompt = category["prompts"][0]
            return {"response": get_llm_response(prompt)}
    return {"error": "Category not found"}
