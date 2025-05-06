import xml.etree.ElementTree as ET
from lxml import etree
from models import *
import re
from helpers import decode_xml
import uuid
from .epp_core import *
from typing import Union

def create_domain_xml(domain: Domain, client_request_id=None) -> str:
    """
    Creates an EPP XML payload for domain creation with optional parameters.

    Args:
        domain (Domain): The domain object containing the domain data.
        request_id (str, optional): The request ID.

    Returns:
        str: The XML payload as a string.
    """

    '''
    Needed output:
    <?xml version="1.0" standalone="no"?>
    <epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
    <command>
        <create>
        <domain:create xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
            <domain:name>example.com</domain:name>
            <domain:period unit="y">1</domain:period>
            <domain:ns>
            <domain:hostObj>ns1.example.com</domain:hostObj>
            <domain:hostObj>ns2.example.net</domain:hostObj>
            <domain:hostAttr>
                <domain:hostName>ns3.example.org</domain:hostName>
                <domain:hostAddr ip="v4">127.0.0.1</domain:hostAddr>
                <domain:hostAddr ip="v6">::1</domain:hostAddr>
            </domain:hostAttr>
            </domain:ns>
            <domain:registrant>example-contact-id</domain:registrant>
            <domain:contact type="admin">example-contact-id</domain:contact>
            <domain:contact type="billing">example-contact-id</domain:contact>
            <domain:contact type="tech">example-contact-id</domain:contact>
            <domain:authInfo>
            <domain:pw>password</domain:pw>
            </domain:authInfo>
        </domain:create>
        </create>
        <clTRID>TEST-REQUEST-ID</clTRID>
    </command>
    </epp>'''
    epp = ET.Element("epp", {"xmlns": "urn:ietf:params:xml:ns:epp-1.0"})
    command = ET.SubElement(epp, "command")
    create = ET.SubElement(command, "create")
    domain_create = ET.SubElement(create, "domain:create", {"xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0"})

    domain_name_element = ET.SubElement(domain_create, "domain:name")
    domain_name_element.text = domain.name

    if domain.processes and domain.processes.get("creation"):
        duration = domain.processes["creation"].duration
        match = re.match(r"P([0-9]+)([MY])", duration)
        if match:
            value, unit = match.groups()
            unit = unit.lower()
        else:
            raise ValueError("Unsupported duration format. Only whole years (Y) or months (M) are allowed.")
        domain_period = ET.SubElement(domain_create, "domain:period", {"unit": unit})
        domain_period.text = value

    if domain.ns:
        domain_ns = ET.SubElement(domain_create, "domain:ns")
        if domain.ns.host_objs:
            for host_obj_data in domain.ns.host_objs:
                host_obj = ET.SubElement(domain_ns, "domain:hostObj")
                host_obj.text = host_obj_data.id
        if domain.ns.host_attrs:
            for host_attr_data in domain.ns.host_attrs:
                host_attr = ET.SubElement(domain_ns, "domain:hostAttr")
                host_name = ET.SubElement(host_attr, "domain:hostName")
                host_name.text = host_attr_data.id

                if host_attr_data.ipv4:
                    for ip in host_attr_data.ipv4:
                        host_addr_v4 = ET.SubElement(host_attr, "domain:hostAddr", {"ip": "v4"})
                        host_addr_v4.text = ip
                if host_attr_data.ipv6:
                    for ip in host_attr_data.ipv6:
                        host_addr_v6 = ET.SubElement(host_attr, "domain:hostAddr", {"ip": "v6"})
                        host_addr_v6.text = ip

    if domain.contacts:
        registrant_generated = False
        for contact in domain.contacts:
            if "registrant" in contact.types:
                if not registrant_generated:
                    domain_registrant = ET.SubElement(domain_create, "domain:registrant")
                    domain_registrant.text = contact.id
                    registrant_generated = True
                else:
                    raise ValueError("Only one registrant is allowed in EPP")

        for contact in domain.contacts:
            for t in contact.types:
                if not t == "registrant":
                    domain_contact = ET.SubElement(domain_create, "domain:contact", {"type": t})
                    domain_contact.text = contact.id

    if domain.authInfo and domain.authInfo.pw:
        domain_auth_info = ET.SubElement(domain_create, "domain:authInfo")
        domain_pw = ET.SubElement(domain_auth_info, "domain:pw")
        domain_pw.text = domain.authInfo.pw

    if not client_request_id:
        client_request_id = str(uuid.uuid4())
    cl_trid = ET.SubElement(command, "clTRID")
    cl_trid.text = client_request_id

    xml_string = ET.tostring(epp, encoding="unicode", method="xml")
    xml_string = '<?xml version="1.0" standalone="no"?>\n' + xml_string

    return xml_string

def parse_domain_delete_response(xml_string: str, client_transaction_id: str) -> Union[DomainDeleteResponse, ErrorResponse]:
    """Parses an EPP domain delete response XML string."""
    root = decode_xml(xml_string)
    namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'domain': 'urn:ietf:params:xml:ns:domain-1.0'}

    response = DomainDeleteResponse(
        server_transaction_id=get_epp_svTRID(root), 
        client_transaction_id=get_epp_clTRID(root) if client_transaction_id is not None else None, 
        code=get_epp_code(root),
        msg=get_epp_msg(root))
    return response

def parse_domain_response(xml_string: str, client_transaction_id: str) -> Union[DomainCreateResponse, ErrorResponse]:
    """Parses an EPP domain create response XML string."""
    root = decode_xml(xml_string)
    namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'domain': 'urn:ietf:params:xml:ns:domain-1.0'}

    domain_name = root.find(".//domain:name", namespaces=namespace).text
    registrant = root.find(".//domain:registrant", namespaces=namespace).text if root.find(".//domain:registrant", namespaces=namespace) is not None else None
    cr_date = root.find(".//domain:crDate", namespaces=namespace).text if root.find(".//domain:crDate", namespaces=namespace) is not None else None
    ex_date = root.find(".//domain:exDate", namespaces=namespace).text if root.find(".//domain:exDate", namespaces=namespace) is not None else None
    up_date = root.find(".//domain:upDate", namespaces=namespace).text if root.find(".//domain:upDate", namespaces=namespace) is not None else None
    tr_date = root.find(".//domain:trDate", namespaces=namespace).text if root.find(".//domain:trDate", namespaces=namespace) is not None else None
    status = [x.attrib.get("s", None) for x in root.findall(".//domain:status", namespaces=namespace)]
    ns = root.find(".//domain:ns", namespaces=namespace)
    if ns is not None:
        host_objs = [HostObj(x.text) for x in ns.findall(".//domain:hostObj", namespaces=namespace)]
        host_attrs = None
    else:
        host_objs = None
        host_attrs = None
        #TODO: parse host attributes
    clid = root.find(".//domain:clID", namespaces=namespace).text if root.find(".//domain:clID", namespaces=namespace) is not None  else None
    crid = root.find(".//domain:crID", namespaces=namespace).text if root.find(".//domain:crID", namespaces=namespace) is not None else None
    authInfo = root.find(".//domain:authInfo", namespaces=namespace)
    pw = None
    hash = None
    if authInfo is not None:
        pw = authInfo.find("./domain:pw", namespaces=namespace).text if authInfo.find("./domain:pw", namespaces=namespace) is not None else None
        hash = authInfo.find("./domain:hash", namespaces=namespace).text if authInfo.find("./domain:hash", namespaces=namespace) is not None else None
    contact_nodes = root.findall(".//domain:contact", namespaces=namespace)
    contacts_dict = {}
    contacts = None
    for c in contact_nodes:
        contact_id = c.text
        contact_role = c.attrib["type"]
        if contact_id in contacts_dict:
            contacts_dict[contact_id] += [contact_role]
        else:
            contacts_dict[contact_id] = [contact_role]

    if registrant:
        if registrant in contacts_dict:
            contacts_dict[registrant] += ["registrant"]
        else:
            contacts_dict[registrant] = ["registrant"]
    
    if len(contacts_dict) != 0:
        contacts = [ContactReference(types=contacts_dict[x], id=x) for x in contacts_dict]
    domain = Domain(name=domain_name, crDate=cr_date, exDate=ex_date, 
                    upDate=up_date, trDate=tr_date, status=status,
                    clID=clid, crID=crid,
                    ns=NS(host_objs=host_objs, host_attrs=None) if host_objs else NS(host_attrs=host_attrs, host_objs=None) if host_attrs else None,
                    authInfo=AuthInfo(pw, None) if pw is not None else AuthInfo(None, hast) if hash is not None else None, contacts=contacts, dnsSEC=None)
    response = DomainCreateResponse(domain=domain, server_transaction_id=get_epp_svTRID(root), client_transaction_id=get_epp_clTRID(root) if client_transaction_id is not None else None, code=get_epp_code(root), msg=get_epp_msg(root))
    return response

def info_domain_xml(domain_name: str, client_request_id=None) -> str:
    """
    Creates an EPP XML payload for domain info with optional parameters.

    Args:
        domain_name (str): The domain name.
        request_id (str, optional): The request ID.

    Returns:
        str: The XML payload as a string.
    """

    epp = ET.Element("epp", {"xmlns": "urn:ietf:params:xml:ns:epp-1.0"})
    command = ET.SubElement(epp, "command")
    info = ET.SubElement(command, "info")
    domain_info = ET.SubElement(info, "domain:info", {"xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0"})

    domain_name_element = ET.SubElement(domain_info, "domain:name")
    domain_name_element.text = domain_name

    if not client_request_id:
        client_request_id = str(uuid.uuid4())
    cl_trid = ET.SubElement(command, "clTRID")
    cl_trid.text = client_request_id

    xml_string = ET.tostring(epp, encoding="unicode", method="xml")
    xml_string = '<?xml version="1.0" standalone="no"?>\n' + xml_string

    return xml_string

def delete_domain_xml(domain_name: str, client_request_id=None) -> str:
    """
    Creates an EPP XML payload for domain delete with optional parameters.

    Args:
        domain_name (str): The domain name.
        request_id (str, optional): The request ID.

    Returns:
        str: The XML payload as a string.
    """

    epp = ET.Element("epp", {"xmlns": "urn:ietf:params:xml:ns:epp-1.0"})
    command = ET.SubElement(epp, "command")
    info = ET.SubElement(command, "delete")
    domain_info = ET.SubElement(info, "domain:delete", {"xmlns:domain": "urn:ietf:params:xml:ns:domain-1.0"})

    domain_name_element = ET.SubElement(domain_info, "domain:name")
    domain_name_element.text = domain_name

    if not client_request_id:
        client_request_id = str(uuid.uuid4())
    cl_trid = ET.SubElement(command, "clTRID")
    cl_trid.text = client_request_id

    xml_string = ET.tostring(epp, encoding="unicode", method="xml")
    xml_string = '<?xml version="1.0" standalone="no"?>\n' + xml_string

    return xml_string
