FROM python:3.11

WORKDIR /home/oaieval

COPY ./openai-evals /home/oaieval

RUN pip install -e .
