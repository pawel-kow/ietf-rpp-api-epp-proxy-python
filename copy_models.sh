#!/bin/sh

cp -v ../typespec/tsp-output/@typespec/openapi3/openapi.yaml ./src/openapi.yaml
cp -v ../typespec/tsp-output/@typespec/json-schema/*.json ./src/rpp_schema_validator/schemas