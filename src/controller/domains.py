from connexion import request
from eppgen import *
from models import *
import json

def domains_Check(body):
    return {}, 500

def domains_Create(body):
    # Create a Domain object from the request body
    domain = Domain(
        name=body["name"],
        duration=body.get("duration", None),
        registrant=[Registrant(id=x) for x in body["registrant"]] if "registrant" in body else None,
        authInfo=AuthInfo(pw=body["authInfo"].get("pw", None), hash=body["authInfo"].get("hash", None)) if "authInfo" in
        body else None,
        ns=body.get("ns", None),
        contacts=body.get("contacts", None),
        dnsSEC=body.get("dnsSEC", None)
    )
    
    # Check if Expect header is set, if so return 100-continue
    if request.headers.get('Expect') == '100-continue':
        return None, 100
    
    # Generate the EPP XML payload for domain creation
    eppxml = create_domain_xml(domain)
    print(eppxml)
    return eppxml, 200

def domains_Delete(id):
    return {}, 500


def domains_Get(id):
    return {}, 500


def domains_Update(id, body):
    return {}, 500