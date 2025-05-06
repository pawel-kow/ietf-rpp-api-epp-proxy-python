from models import *
from epp_to_model_mapper import *
from .eppclient import EPPClient
import os
from typing import Union

MOCK_REAL_EPP_SERVER=os.getenv('MOCK_REAL_EPP_SERVER', 'False').lower() == 'true'

def epp_domains_Create(epp_client: EPPClient, domain: Domain, client_transaction_id=None) -> Union[DomainCreateResponse, ErrorResponse]:
    """
    Creates a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain (Domain): The domain object to be created.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainCreateResponse: The response from the EPP server.
    """
    eppxml = create_domain_xml(domain, client_request_id=client_transaction_id)
    if MOCK_REAL_EPP_SERVER == False:
        success, code, response = epp_client.send_and_get_response(eppxml)
    else:
        success, code, response = True, '1000', '''<?xml version="1.0" standalone="no"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <response>
    <result code="1000">
      <msg>Command completed successfully</msg>
    </result>
    <resData>
      <domain:infData
       xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
        <domain:name>example.com</domain:name>
        <domain:roid>EXAMPLE1-REP</domain:roid>
        <domain:status s="ok"/>
        <domain:registrant>jd1234</domain:registrant>
        <domain:contact type="admin">sh8013</domain:contact>
        <domain:contact type="tech">sh8013</domain:contact>
        <domain:ns>
          <domain:hostObj>ns1.example.com</domain:hostObj>
          <domain:hostObj>ns1.example.net</domain:hostObj>
        </domain:ns>
        <domain:host>ns1.example.com</domain:host>
        <domain:host>ns2.example.com</domain:host>
        <domain:clID>ClientX</domain:clID>
        <domain:crID>ClientY</domain:crID>
        <domain:crDate>1999-04-03T22:00:00.0Z</domain:crDate>
        <domain:upID>ClientX</domain:upID>
        <domain:upDate>1999-12-03T09:00:00.0Z</domain:upDate>
        <domain:exDate>2005-04-03T22:00:00.0Z</domain:exDate>
        <domain:trDate>2000-04-08T09:00:00.0Z</domain:trDate>
        <domain:authInfo>
          <domain:pw>2fooBAR</domain:pw>
        </domain:authInfo>
      </domain:infData>
    </resData>
    <trID>
      <clTRID>ABC-12345</clTRID>
      <svTRID>54322-XYZ</svTRID>
    </trID>
  </response>
</epp>
'''
    if success == True:
        domainresp = parse_domain_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

def epp_domains_Info(epp_client: EPPClient, domain_name: str, client_transaction_id=None) -> Union[DomainInfoResponse, ErrorResponse]:
    """
    Retrieves information about a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain to be retrieved.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainInfoResponse: The response from the EPP server.
    """
    eppxml = info_domain_xml(domain_name, client_request_id=client_transaction_id)
    if MOCK_REAL_EPP_SERVER == False:
        success, code, response = epp_client.send_and_get_response(eppxml)
    else:
        success, code, response = True, '1000', '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>

<epp xmlns="urn:ietf:params:xml:ns:epp-1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:ietf:params:xml:ns:epp-1.0 epp-1.0.xsd">
    <response>
        <result code="1000">
            <msg>Command completed successfully</msg>
        </result>
        <resData>
            <domain:infData xmlns:domain="urn:ietf:params:xml:ns:domain-1.0" xsi:schemaLocation="urn:ietf:params:xml:ns:domain-1.0 domain-1.0.xsd">
                <domain:name>TEST5-BC4F8215-6118-47D6-B25B-CB12399AEEF4.EXAMPLE</domain:name>
                <domain:roid>D_155-EXAMPLESRV</domain:roid>
                <domain:status s="ok" lang="en-US">ok</domain:status>
                <domain:ns>
                    <domain:hostObj>NS1.FOO.NET</domain:hostObj>
                    <domain:hostObj>NS1.TEST5-BC4F8215-6118-47D6-B25B-CB12399AEEF4.EXAMPLE</domain:hostObj>
                </domain:ns>
                <domain:host>NS1.TEST5-BC4F8215-6118-47D6-B25B-CB12399AEEF4.EXAMPLE</domain:host>
                <domain:clID>foo</domain:clID>
                <domain:crID>foo</domain:crID>
                <domain:crDate>2025-04-28T21:48:25.0Z</domain:crDate>
                <domain:exDate>2026-04-28T21:48:25.0Z</domain:exDate>
                <domain:authInfo>
                    <domain:pw>Password1!@</domain:pw>
                </domain:authInfo>
            </domain:infData>
        </resData>
        <extension>
            <rgp:infData xmlns:rgp="urn:ietf:params:xml:ns:rgp-1.0" xsi:schemaLocation="urn:ietf:params:xml:ns:rgp-1.0 rgp-1.0.xsd">
                <rgp:rgpStatus s="addPeriod" />
            </rgp:infData>
        </extension>
        <trID>
            <clTRID>3c7e2a3e-5e3c-4fea-aeb3-ac84e72f9ede</clTRID>
            <svTRID>2025042821482547422-clID:4-domain:info</svTRID>
        </trID>
    </response>
</epp>
'''
    if success == True:
        domainresp = parse_domain_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

def epp_domains_Delete(epp_client: EPPClient, domain_name: str, client_transaction_id=None) -> Union[DomainDeleteResponse, ErrorResponse]:
    """
    Deletes a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain to be deleted.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainDeleteResponse: The response from the EPP server.
    """
    eppxml = delete_domain_xml(domain_name, client_request_id=client_transaction_id)
    if MOCK_REAL_EPP_SERVER == False:
        success, code, response = epp_client.send_and_get_response(eppxml)
    else:
        success, code, response = True, '1000','''
'''
#TODO: implement here mock as well
    if success == True:
        domainresp = parse_domain_delete_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
