from connexion import request, ProblemException
from connexion.context import operation
from eppclient.epp_domains import *
from models import *
from rpp_to_model_mapper import *
from .helper.rpp_response import *
import json
import asyncio

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
            #TODO: implement EPP check call
            return None, 100
        # Call the eppclient function to get the domain information
        domainresp = epp_domains_Create(domain, client_transaction_id=request.headers.get('RPP-clTRID'))
        if isinstance(domainresp, DomainCreateResponse):
            inforesp = epp_domains_Info(domainresp.domain.name)
            # Convert the response to JSON
            response = domain_to_rpp(inforesp.domain)
            return response, 201, generate_rpp_response_headers(domainresp)
        elif isinstance(domainresp, ErrorResponse):
            if domainresp.code == OperationResponse.ResultCode.OBJECT_EXISTS:
                raise ProblemException(status=409, title=domainresp.code.value[1], detail=domainresp.msg, ext={"code": domainresp.code.value[0]}, headers=generate_rpp_response_headers(domainresp))
            else:
                raise ProblemException(status=400, title=domainresp.code.value[1], detail=domainresp.msg, ext={"code": domainresp.code.value[0]}, headers=generate_rpp_response_headers(domainresp))
        else:
            raise ValueError("Unexpected response type from EPP client")
    except ProblemException:
        raise
    except Exception as e:
        raise ProblemException(status=500, title="Internal Server Error", detail=str(e), headers=generate_rpp_response_headers_separate(request.headers.get('RPP-clTRID')))

def domains_Delete(id):
    try:
        x = asyncio.run(request.get_body())
        if x is not None and len(x) > 0:
            raise ProblemException(status=400, title="Bad Request", detail="Request body must be empty for DELETE method")
        # Call the eppclient function to delete  the domain
        domainresp = epp_domains_Delete(id)
        # Convert the response to JSON
        if isinstance(domainresp, DomainDeleteResponse):
            if domainresp.code == OperationResponse.ResultCode.COMMAND_COMPLETED_SUCCESSFULLY:
                return None, 204, generate_rpp_response_headers(domainresp)
            elif domainresp.code == OperationResponse.ResultCode.COMMAND_COMPLETED_ACTION_PENDING:
                return None, 202, generate_rpp_response_headers(domainresp)
            else:
                # this code should not be ever reached
                raise ProblemException(status=400, title=domainresp.code.value[1], detail=domainresp.msg, ext={"code": domainresp.code.value[0]}, headers=generate_rpp_response_headers(domainresp))
        elif isinstance(domainresp, ErrorResponse):
            if domainresp.code == OperationResponse.ResultCode.OBJECT_DOES_NOT_EXIST:
                raise ProblemException(status=404, title=domainresp.code.value[1], detail=domainresp.msg, ext={"code": domainresp.code.value[0]}, headers=generate_rpp_response_headers(domainresp))
            else:
                raise ProblemException(status=400, title=domainresp.code.value[1], detail=domainresp.msg, ext={"code": domainresp.code.value[0]}, headers=generate_rpp_response_headers(domainresp))
        else:
            raise ValueError("Unexpected response type from EPP client")
    except ProblemException:
        raise
    except Exception as e:
        raise ProblemException(status=500, title="Internal Server Error", detail=str(e), headers=generate_rpp_response_headers_separate(request.headers.get('RPP-clTRID')))
    return response, 200

def domains_Get(id):
    try:
        # Call the eppclient function to create the domain
        domainresp = epp_domains_Info(id)
        if isinstance(domainresp, DomainCreateResponse):
            response = domain_to_rpp(domainresp.domain)
            return response, 200
        elif isinstance(domainresp, ErrorResponse):
            if domainresp.code == OperationResponse.ResultCode.OBJECT_DOES_NOT_EXIST:
                raise ProblemException(status=404, title=domainresp.code.value[1], detail=domainresp.msg, ext={"code": domainresp.code.value[0]})
            else:
                raise ProblemException(status=400, title=domainresp.code.value[1], detail=domainresp.msg, ext={"code": domainresp.code.value[0]})
        else:
            raise ValueError("Unexpected response type from EPP client")
    except ProblemException:
        raise
    except Exception as e:
        raise ProblemException(status=500, title="Internal Server Error", detail=str(e))
    return response, 200

def domains_Update(id, body):
    return {}, 500