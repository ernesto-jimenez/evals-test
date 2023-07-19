FROM golang:1.19 AS builder

WORKDIR /home/unweave-openai-evals

COPY go.mod .
# COPY go.sum .

RUN go mod download

COPY ./evalmock ./evalmock

RUN go build -o eval-server ./evalmock

FROM python:3.11

RUN pip install pipenv

WORKDIR /root
ENV PYTHONPATH=/root

COPY . /root
COPY --from=builder /home/unweave-openai-evals/eval-server /usr/local/bin/eval-server

RUN pipenv install

CMD [ "./eval.sh" ]
