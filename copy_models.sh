#!/bin/sh
# Copies the generated contract from the draft set into the application.
SPEC_FOLDER=.spec/auto

cp -v $SPEC_FOLDER/openapi3/openapi.yaml ./src/openapi.yaml
cp -v $SPEC_FOLDER/json-schema/rpp.schema.normalized.json ./src/rpp_schema_validator/schemas/
