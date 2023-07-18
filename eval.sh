#!/usr/bin/env bash

EVAL=${1:-"test-match"}
RECORD_PATH=${OAIEVAL_RECORD_PATH:-"output.jsonl"}
REGISTRY_PATH=${OAIEVAL_REGISTRY_PATH:-"."}

pipenv run \
  oaieval unweave \
    --registry_path="$REGISTRY_PATH" \
    --record_path="$RECORD_PATH" \
    $EVAL
