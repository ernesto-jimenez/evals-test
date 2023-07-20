FROM python:3.11

RUN pip install pipenv

WORKDIR /root
ENV PYTHONPATH=/root
ENV PORT="8080"

COPY . /root

RUN pipenv install
