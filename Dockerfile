FROM python:3.11

RUN pip install pipenv

WORKDIR /home/unweave-openai-evals
ENV PYTHONPATH=/home/unweave-openai-evals

COPY . /home/unweave-openai-evals

RUN pipenv install

CMD [ "./eval.sh" ]
