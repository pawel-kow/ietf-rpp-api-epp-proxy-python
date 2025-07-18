from connexion import request, ProblemException
from connexion.context import operation
from eppclient.epp_contacts import *
from models import *
from rpp_to_model_mapper import *
from .helper.rpp_response import *
import json
import asyncio
from .auth import get_epp_client

def contacts_Check(body):
    return {}, 500

#TODO: finish implementation contacts_Create
def contacts_Create(body):
    try:
        contact = rpp_to_contact(body)
    except Exception as e:
        raise ProblemException(status=400, title="Bad Request", detail=str(e))

    try:
        # Check if Expect header is set, if so return 100-continue
        if request.headers.get('Expect') == '100-continue':
            #TODO: implement EPP check call
            return None, 100
        # Call the eppclient function to get the domain information
        contactresp = epp_contacts_Create(get_epp_client(), contact, client_transaction_id=request.headers.get('RPP-clTRID'))
        if isinstance(contactresp, ContactCreateResponse):
            inforesp = epp_contacts_Info(get_epp_client(), contactresp.contact.id)
            # Convert the response to JSON
            response = contact_to_rpp(inforesp.contact)
            return response, 201, generate_rpp_response_headers(contactresp)
        elif isinstance(contactresp, ErrorResponse):
            if contactresp.code == OperationResponse.ResultCode.OBJECT_EXISTS:
                raise ProblemException(status=409, title=contactresp.code.value[1], detail=contactresp.msg, ext={"code": contactresp.code.value[0]}, headers=generate_rpp_response_headers(contactresp))
            else:
                raise ProblemException(status=400, title=contactresp.code.value[1], detail=contactresp.msg, ext={"code": contactresp.code.value[0]}, headers=generate_rpp_response_headers(contactresp))
        else:
            raise ValueError("Unexpected response type from EPP client")

    except ProblemException:
        raise
    except Exception as e:
        raise ProblemException(status=500, title="Internal Server Error", detail=str(e), headers=generate_rpp_response_headers_separate(request.headers.get('RPP-clTRID')))

#TODO: implement contacts_Delete
def contacts_Delete(id):
    try:
        x = asyncio.run(request.get_body())
        if x is not None and len(x) > 0:
            raise ProblemException(status=400, title="Bad Request", detail="Request body must be empty for DELETE method")
        # Call the eppclient function to delete  the contact
        contactresp = epp_contacts_Delete(get_epp_client(), id)
        # Convert the response to JSON
        if isinstance(contactresp, DomainDeleteResponse):
            if contactresp.code == OperationResponse.ResultCode.COMMAND_COMPLETED_SUCCESSFULLY:
                return None, 204, generate_rpp_response_headers(contactresp)
            elif contactresp.code == OperationResponse.ResultCode.COMMAND_COMPLETED_ACTION_PENDING:
                return None, 202, generate_rpp_response_headers(contactresp)
            else:
                # this code should not be ever reached
                raise ProblemException(status=400, title=contactresp.code.value[1], detail=contactresp.msg, ext={"code": contactresp.code.value[0]}, headers=generate_rpp_response_headers(contactresp))
        elif isinstance(contactresp, ErrorResponse):
            if contactresp.code == OperationResponse.ResultCode.OBJECT_DOES_NOT_EXIST:
                raise ProblemException(status=404, title=contactresp.code.value[1], detail=contactresp.msg, ext={"code": contactresp.code.value[0]}, headers=generate_rpp_response_headers(contactresp))
            else:
                raise ProblemException(status=400, title=contactresp.code.value[1], detail=contactresp.msg, ext={"code": contactresp.code.value[0]}, headers=generate_rpp_response_headers(contactresp))
        else:
            raise ValueError("Unexpected response type from EPP client")
    except ProblemException:
        raise
    except Exception as e:
        raise ProblemException(status=500, title="Internal Server Error", detail=str(e), headers=generate_rpp_response_headers_separate(request.headers.get('RPP-clTRID')))
    return response, 200

#TODO: implement contacts_Get
def contacts_Get(id):
    try:
        # Call the eppclient function to create the domain
        domainresp = epp_domains_Info(get_epp_client(), id)
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

#TODO: implement contacts_Update
def contacts_Update(id, body):
    return {}, 500