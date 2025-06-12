FROM python:latest

WORKDIR /app
COPY requirements.txt  requirements.txt
COPY llm-response llm-response
COPY prompts prompts
COPY app.py app.py
COPY llm.py llm.py
COPY templates templates
COPY queries.yaml queries.yaml

RUN pip install -U pip
RUN pip install -r requirements.txt

EXPOSE 80
CMD [ "python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
