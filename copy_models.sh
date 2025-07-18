#!/bin/sh
TYPESPEC_FOLDER=ietf-rpp-api-typespec

cp -v ../$TYPESPEC_FOLDER/tsp-output/@typespec/openapi3/openapi.yaml ./src/openapi.yaml
cp -v ../$TYPESPEC_FOLDER/tsp-output/@typespec/json-schema/*.json ./src/rpp_schema_validator/schemas
