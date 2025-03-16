from connexion import request
from eppclient.epp_domains import *
from models import *
from rpp_to_model_mapper import *
import json

def domains_Check(body):
    return {}, 500

def domains_Create(body):
    domain = rpp_to_domain(body)
    
    # Check if Expect header is set, if so return 100-continue
    if request.headers.get('Expect') == '100-continue':
        return None, 100
    
    # Call the eppclient function to create the domain
    domainresp = epp_domains_Create(domain)
    #HACK: this should be rather done with domain information from the response
    domain.update(domainresp.domain)
    
    # Convert the response to JSON
    response = domain_to_rpp(domain)
    
    return response, 201

def domains_Delete(id):
    return {}, 500


def domains_Get(id):
    return {}, 500


def domains_Update(id, body):
    return {}, 500