#!/bin/sh
# Copies the generated contract from the draft set into the application.
SPEC_FOLDER=.spec/auto

cp -v $SPEC_FOLDER/openapi3/openapi.yaml ./src/rpp/openapi.yaml
cp -v $SPEC_FOLDER/json-schema/rpp.schema.normalized.json ./src/rpp/schema/schemas/
cp -v .spec/draft-ietf-rpp-data-objects.yaml ./src/rpp/schema/schemas/
# The RRI extension, described in docs/rri/rri-extension.md.
cp -v .spec/rri-extension.schema.json .spec/rri-profile.schema.json ./src/extensions/rri/rpp/schema/
# The Profile Schema of the EPP Compatibility Profile, from draft-kowalik-rpp-epp-compatibility.
cp -v .spec/epp-compatibility-profile.schema.json ./src/rpp/schema/schemas/profiles/epp-compatibility.schema.json
# The demo extension of the SQLite backend, described in docs/demo/planets-extension.md.
cp -v .spec/planets-extension.schema.json ./src/extensions/planets/rpp/schema/
# The profiles of the planets extension, described in docs/demo/<key>-profile.md.
cp -v .spec/rocky-planets-profile.schema.json .spec/catalogued-satellites-profile.schema.json ./src/extensions/planets/rpp/schema/
# The demo extension that adds an atmosphere to a planet, and the profiles that need it.
cp -v .spec/planet-atmosphere-extension.schema.json .spec/habitable-atmospheres-profile.schema.json \
  .spec/habitable-rocky-planets-profile.schema.json ./src/extensions/planet_atmosphere/rpp/schema/
# The demo extension that adds an orbit to a satellite.
cp -v .spec/satellite-orbit-extension.schema.json ./src/extensions/satellite_orbit/rpp/schema/
