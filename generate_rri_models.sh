#!/bin/sh
# Generates the xsdata dataclasses of the DENIC RRI 5.0 XML schemas (docs/rri/xsd) into the RRI adapter.
# Needs xsdata[cli] in the virtualenv: pip install "xsdata[cli]==25.7"
set -e
cd src
xsdata generate ../docs/rri/xsd --package registry_adapter.rri.xml.generated --structure-style filenames
