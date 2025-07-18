from models import *
from epp_to_model_mapper import *
from .eppclient import EPPClient
import os
from typing import Union

MOCK_REAL_EPP_SERVER=os.getenv('MOCK_REAL_EPP_SERVER', 'False').lower() == 'true'

#TODO: not tested yet epp_contacts_Create
def epp_contacts_Create(epp_client: EPPClient, contact: Contact, client_transaction_id=None) -> Union[ContactCreateResponse, ErrorResponse]:
    """
    Creates a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        contact (Contact): The contact object to be created.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        ContactCreateResponse: The response from the EPP server.
    """
    eppxml = create_contact_xml(contact, client_request_id=client_transaction_id)
    if MOCK_REAL_EPP_SERVER == False:
        success, code, response = epp_client.send_and_get_response(eppxml)
    else:
        success, code, response = True, '1000', '''S:<?xml version="1.0" encoding="UTF-8" standalone="no"?>
   <epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
     <response>
       <result code="1000">
         <msg>Command completed successfully</msg>
       </result>
       <resData>
         <contact:infData
          xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
           <contact:id>sh8013</contact:id>
           <contact:roid>SH8013-REP</contact:roid>
           <contact:status s="linked"/>
           <contact:status s="clientDeleteProhibited"/>
           <contact:postalInfo type="int">
             <contact:name>John Doe</contact:name>
             <contact:org>Example Inc.</contact:org>
             <contact:addr>
               <contact:street>123 Example Dr.</contact:street>
               <contact:street>Suite 100</contact:street>
               <contact:city>Dulles</contact:city>
               <contact:sp>VA</contact:sp>
               <contact:pc>20166-6503</contact:pc>
               <contact:cc>US</contact:cc>
             </contact:addr>
           </contact:postalInfo>
           <contact:voice x="1234">+1.7035555555</contact:voice>
           <contact:fax>+1.7035555556</contact:fax>
           <contact:email>jdoe@example.com</contact:email>
           <contact:clID>ClientY</contact:clID>
           <contact:crID>ClientX</contact:crID>
           <contact:crDate>1999-04-03T22:00:00.0Z</contact:crDate>
           <contact:upID>ClientX</contact:upID>
           <contact:upDate>1999-12-03T09:00:00.0Z</contact:upDate>
           <contact:trDate>2000-04-08T09:00:00.0Z</contact:trDate>
           <contact:authInfo>
             <contact:pw>2fooBAR</contact:pw>
           </contact:authInfo>
           <contact:disclose flag="0">
             <contact:voice/>
             <contact:email/>
           </contact:disclose>
         </contact:infData>
       </resData>
       <trID>
         <clTRID>ABC-12345</clTRID>
         <svTRID>54322-XYZ</svTRID>
       </trID>
     </response>
   </epp>
'''
    if success == True:
        contactresp = parse_contact_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

#TODO: implement epp_contacts_Info
def epp_contacts_Info(epp_client: EPPClient, id: str, client_transaction_id=None) -> Union[ContactInfoResponse, ErrorResponse]:
    """
    Retrieves information about a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        id (str): The id of the contact to be retrieved.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainInfoResponse: The response from the EPP server.
    """
    eppxml = info_contact_xml(id, client_request_id=client_transaction_id)
    if MOCK_REAL_EPP_SERVER == False:
        success, code, response = epp_client.send_and_get_response(eppxml)
    else:
        #TODO: mock response
        success, code, response = True, '1000', ''''''
    if success == True:
        contactresp = parse_contact_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

#TODO: implement epp_contacts_Delete
def epp_contacts_Delete(epp_client: EPPClient, id: str, client_transaction_id=None) -> Union[ContactDeleteResponse, ErrorResponse]:
    """
    Deletes a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        id (str): The id of the contact to be deleted.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainDeleteResponse: The response from the EPP server.
    """
    eppxml = delete_contact_xml(id, client_request_id=client_transaction_id)
    if MOCK_REAL_EPP_SERVER == False:
        success, code, response = epp_client.send_and_get_response(eppxml)
    else:
        success, code, response = True, '1000','''
'''
#TODO: implement here mock as well
    if success == True:
        contactresp = parse_contact_delete_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
