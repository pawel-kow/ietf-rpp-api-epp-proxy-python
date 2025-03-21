from connexion import request, ProblemException
from eppclient.epp_domains import *
from models import *
from rpp_to_model_mapper import *
import json

def domains_Check(body):
    return {}, 500

def domains_Create(body):
    try:
        domain = rpp_to_domain(body)
    except Exception as e:
        raise ProblemException(status=400, title="Bad Request", detail=str(e))

    try:
        # Check if Expect header is set, if so return 100-continue
        if request.headers.get('Expect') == '100-continue':
            return None, 100
        
        # Call the eppclient function to create the domain
        domainresp = epp_domains_Create(domain)
        #HACK: this should be rather done with domain info reponse
        domain.update(domainresp.domain)
        
        # Convert the response to JSON
        response = domain_to_rpp(domain)
    except Exception as e:
        raise ProblemException(status=500, title="Internal Server Error", detail=str(e))
    return response, 201

def domains_Delete(id):
    return {}, 500


def domains_Get(id):
    try:
        # Call the eppclient function to create the domain
        domainresp = epp_domains_Info(id)
        # Convert the response to JSON
        response = domain_to_rpp(domainresp.domain)
    except Exception as e:
        raise ProblemException(status=500, title="Internal Server Error", detail=str(e))
    return response, 200

def domains_Update(id, body):
    return {}, 500