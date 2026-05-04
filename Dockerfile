FROM python:3.12-slim

RUN pip install curl_cffi click rich requests

WORKDIR /app
COPY . .

RUN pip install -e .

ENTRYPOINT ["gpt-farm"]
