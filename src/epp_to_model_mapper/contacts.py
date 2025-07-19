import xml.etree.ElementTree as ET
from lxml import etree
from models import *
import re
from helpers import decode_xml
import uuid
from .epp_core import *
from typing import Union

#TODO: not tested yet create_contact_xml
def create_contact_xml(contact: Contact, client_request_id=None) -> str:
    """
    Creates an EPP XML payload for domain creation with optional parameters.

    Args:
        contact (Contact): The contact object containing the contact data.
        request_id (str, optional): The request ID.

    Returns:
        str: The XML payload as a string.
    """

    '''
    Needed output:
   <?xml version="1.0" encoding="UTF-8" standalone="no"?>
   <epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
     <command>
       <create>
         <contact:create
          xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
           <contact:id>sh8013</contact:id>
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
           <contact:authInfo>
             <contact:pw>2fooBAR</contact:pw>
           </contact:authInfo>
           <contact:disclose flag="0">
             <contact:voice/>
             <contact:email/>
           </contact:disclose>
         </contact:create>
       </create>
       <clTRID>ABC-12345</clTRID>
     </command>
   </epp>'''
    epp = ET.Element("epp", {"xmlns": "urn:ietf:params:xml:ns:epp-1.0"})
    command = ET.SubElement(epp, "command")
    create = ET.SubElement(command, "create")
    contact_create = ET.SubElement(create, "contact:create", {"xmlns:contact": "urn:ietf:params:xml:ns:contact-1.0"})

    if contact.id:
        contact_id_element = ET.SubElement(contact_create, "contact:id")
        contact_id_element.text = contact.id.upper()

    if contact.name or contact.address or contact.organisationName and contact.type == ContactType.ORG:
        postal_info = ET.SubElement(contact_create, "contact:postalInfo", {"type": "int"})
        if contact.name:
            name_element = ET.SubElement(postal_info, "contact:name")
            name_element.text = contact.name
        if contact.organisationName and contact.type == ContactType.ORG:
            org_element = ET.SubElement(postal_info, "contact:org")
            org_element.text = contact.organisationName
                
        if contact.address:
            address_element = ET.SubElement(postal_info, "contact:addr")
            if contact.address.street:
                for street in contact.address.street:
                    street_element = ET.SubElement(address_element, "contact:street")
                    street_element.text = street
            if contact.address.city:
                city_element = ET.SubElement(address_element, "contact:city")
                city_element.text = contact.address.city
            if contact.address.stateProvince:
                state_element = ET.SubElement(address_element, "contact:sp")
                state_element.text = contact.address.stateProvince
            if contact.address.postalCode:
                postal_code_element = ET.SubElement(address_element, "contact:pc")
                postal_code_element.text = contact.address.postalCode
            if contact.address.country:
                country_element = ET.SubElement(address_element, "contact:cc")
                country_element.text = contact.address.country
    if contact.email and len(contact.email) > 0:
        email_element = ET.SubElement(contact_create, "contact:email")
        email_element.text = contact.email[0]
        
    if contact.phone and len(contact.phone) > 0:
        phone = contact.phone[0]
        match = re.search(r"x(\d+)", phone)
        if match:
            extension = match.group(1)
            # Remove 'x' and extension from phone number
            phone_number = re.sub(r"x\d+", "", phone)
            voice_element = ET.SubElement(contact_create, "contact:voice", {"x": extension})
            voice_element.text = phone_number.strip()
        else:
            voice_element = ET.SubElement(contact_create, "contact:voice")
            voice_element.text = phone

    if contact.fax and len(contact.fax) > 0:
        fax = contact.fax[0]
        match = re.search(r"x(\d+)", fax)
        if match:
            extension = match.group(1)
            # Remove 'x' and extension from fax number
            phone_number = re.sub(r"x\d+", "", fax)
            voice_element = ET.SubElement(contact_create, "contact:fax", {"x": extension})
            voice_element.text = phone_number.strip()
        else:
            voice_element = ET.SubElement(contact_create, "contact:fax")
            voice_element.text = fax

    if contact.authInfo and contact.authInfo.pw:
        contact_auth_info = ET.SubElement(contact_create, "contact:authInfo")
        contact_pw = ET.SubElement(contact_auth_info, "contact:pw")
        contact_pw.text = contact.authInfo.pw
            
    if not client_request_id:
        client_request_id = str(uuid.uuid4())
    cl_trid = ET.SubElement(command, "clTRID")
    cl_trid.text = client_request_id

    xml_string = ET.tostring(epp, encoding="unicode", method="xml")
    xml_string = '<?xml version="1.0" standalone="no"?>\n' + xml_string

    return xml_string


#TODO: implement parse_contact_delete_response
def parse_contact_delete_response(xml_string: str, client_transaction_id: str) -> Union[ContactDeleteResponse, ErrorResponse]:
    """Parses an EPP domain delete response XML string."""
    root = decode_xml(xml_string)
    namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'domain': 'urn:ietf:params:xml:ns:contact-1.0'}

    response = DomainDeleteResponse(
        server_transaction_id=get_epp_svTRID(root), 
        client_transaction_id=get_epp_clTRID(root) if client_transaction_id is not None else None, 
        code=get_epp_code(root),
        msg=get_epp_msg(root))
    return response


#TODO: test parse_contact_response
def parse_contact_response(xml_string: str, client_transaction_id: str) -> Union[ContactCreateResponse, ErrorResponse]:
    """Parses an EPP domain create response XML string."""
    root = decode_xml(xml_string)
    namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'contact': 'urn:ietf:params:xml:ns:contact-1.0'}

    id = root.find(".//contact:id", namespaces=namespace).text

    postalInfo = root.find(".//contact:postalInfo", namespaces=namespace)
    if postalInfo is not None:
        name = postalInfo.find(".//contact:name", namespaces=namespace).text if postalInfo.find(".//contact:name", namespaces=namespace) is not None else None
        org = postalInfo.find(".//contact:org", namespaces=namespace).text if postalInfo.find(".//contact:org", namespaces=namespace) is not None else None
        address = Address(
            street=[x.text for x in postalInfo.findall(".//contact:street", namespaces=namespace)] if postalInfo.findall(".//contact:street", namespaces=namespace) else None,
            city=postalInfo.find(".//contact:city", namespaces=namespace).text if postalInfo.find(".//contact:city", namespaces=namespace) is not None else None,
            stateProvince=postalInfo.find(".//contact:sp", namespaces=namespace).text if postalInfo.find(".//contact:sp", namespaces=namespace) is not None else None,
            postalCode=postalInfo.find(".//contact:pc", namespaces=namespace).text if postalInfo.find(".//contact:pc", namespaces=namespace) is not None else None,
            country=postalInfo.find(".//contact:cc", namespaces=namespace).text if postalInfo.find(".//contact:cc", namespaces=namespace) is not None else None,
        )
    else:
        name = None
        address = None
        org = None

    email = [root.find(".//contact:email", namespaces=namespace).text if root.find(".//contact:email", namespaces=namespace) is not None else None]
    voice_elem = root.find(".//contact:voice", namespaces=namespace)
    if voice_elem is not None and voice_elem.text is not None:
        phone_number = voice_elem.text
        extension = voice_elem.attrib.get("x")
        if extension:
            phone = [f"{phone_number}x{extension}"]
        else:
            phone = [phone_number]
    else:
        phone = None
    
    fax_elem = root.find(".//contact:fax", namespaces=namespace)
    if fax_elem is not None and fax_elem.text is not None:
        fax_number = fax_elem.text
        extension = fax_elem.attrib.get("x")
        if extension:
            fax = [f"{fax_number}x{extension}"]
        else:
            fax = [fax_number]
    else:
        fax = None
    
    cr_date = root.find(".//contact:crDate", namespaces=namespace).text if root.find(".//contact:crDate", namespaces=namespace) is not None else None
    ex_date = root.find(".//contact:exDate", namespaces=namespace).text if root.find(".//contact:exDate", namespaces=namespace) is not None else None
    up_date = root.find(".//contact:upDate", namespaces=namespace).text if root.find(".//contact:upDate", namespaces=namespace) is not None else None
    tr_date = root.find(".//contact:trDate", namespaces=namespace).text if root.find(".//contact:trDate", namespaces=namespace) is not None else None
    clid = root.find(".//contact:clID", namespaces=namespace).text if root.find(".//contact:clID", namespaces=namespace) is not None  else None
    crid = root.find(".//contact:crID", namespaces=namespace).text if root.find(".//contact:crID", namespaces=namespace) is not None else None
    
    status = [x.attrib.get("s", None) for x in root.findall(".//contact:status", namespaces=namespace)]


    authInfo = root.find(".//contact:authInfo", namespaces=namespace)
    pw = None
    hash = None
    if authInfo is not None:
        pw = authInfo.find("./contact:pw", namespaces=namespace).text if authInfo.find("./contact:pw", namespaces=namespace) is not None else None
        hash = authInfo.find("./contact:hash", namespaces=namespace).text if authInfo.find("./contact:hash", namespaces=namespace) is not None else None
    
    contact = Contact(
        id = id,
        name = name,
        organisationName= org,
        type = ContactType.ORG if org is not None
            else ContactType.PERSON if name is not None
            else ContactType.UNDEFINED,
        email = email,
        phone = phone,
        fax = fax,
        address = address,
        #common fields
        status = status,
        crDate = cr_date,
        exDate = ex_date,
        upDate = up_date,
        trDate = tr_date,
        clID = clid,
        crID = crid,
        authInfo = AuthInfo(
            pw = pw,
            hash = hash
        ) if pw is not None or hash is not None else None
    )
    
    resp = ContactCreateResponse(contact=contact, server_transaction_id=get_epp_svTRID(root), client_transaction_id=get_epp_clTRID(root) if client_transaction_id is not None else None, code=get_epp_code(root), msg=get_epp_msg(root))
    return resp



#TODO: test info_contact_xml
def info_contact_xml(id: str, client_request_id=None) -> str:
    """
    Creates an EPP XML payload for domain info with optional parameters.

    Args:
        id (str): The contact id.
        request_id (str, optional): The request ID.

    Returns:
        str: The XML payload as a string.
    """

    epp = ET.Element("epp", {"xmlns": "urn:ietf:params:xml:ns:epp-1.0"})
    command = ET.SubElement(epp, "command")
    info = ET.SubElement(command, "info")
    contact_info = ET.SubElement(info, "contact:info", {"xmlns:contact": "urn:ietf:params:xml:ns:contact-1.0"})

    contact_id_element = ET.SubElement(contact_info, "contact:id")
    contact_id_element.text = id

    if not client_request_id:
        client_request_id = str(uuid.uuid4())
    cl_trid = ET.SubElement(command, "clTRID")
    cl_trid.text = client_request_id

    xml_string = ET.tostring(epp, encoding="unicode", method="xml")
    xml_string = '<?xml version="1.0" standalone="no"?>\n' + xml_string

    return xml_string

#TODO: test delete_domain_xml
def delete_contact_xml(id: str, client_request_id=None) -> str:
    """
    Creates an EPP XML payload for domain delete with optional parameters.

    Args:
        id (str): The contact id name.
        request_id (str, optional): The request ID.

    Returns:
        str: The XML payload as a string.
    """

    epp = ET.Element("epp", {"xmlns": "urn:ietf:params:xml:ns:epp-1.0"})
    command = ET.SubElement(epp, "command")
    info = ET.SubElement(command, "delete")
    contact_info = ET.SubElement(info, "contact:delete", {"xmlns:contact": "urn:ietf:params:xml:ns:contact-1.0"})

    contact_id_element = ET.SubElement(contact_info, "contact:id")
    contact_id_element.text = id

    if not client_request_id:
        client_request_id = str(uuid.uuid4())
    cl_trid = ET.SubElement(command, "clTRID")
    cl_trid.text = client_request_id

    xml_string = ET.tostring(epp, encoding="unicode", method="xml")
    xml_string = '<?xml version="1.0" standalone="no"?>\n' + xml_string

    return xml_string
