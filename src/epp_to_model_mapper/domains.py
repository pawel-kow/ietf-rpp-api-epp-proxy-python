import xml.etree.ElementTree as ET
from models import *

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
    <?xml version="1.0" encoding="UTF-8" standalone="no"?>
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

    if domain.duration:
        domain_period = ET.SubElement(domain_create, "domain:period", {"unit": "y"})
        domain_period.text = str(domain.duration)


    if domain.ns:
        if domain.ns.host_objs:
            host_attr = ET.SubElement(domain_ns, "domain:hostObj")
            host_name = ET.SubElement(host_attr, "domain:hostName")
            host_name.text = host_attr_data.id
        if domain.ns.host_attrs:
            for host_attr_data in domain.ns.host_attrs:
                host_attr = ET.SubElement(domain_ns, "domain:hostObj")
                host_name = ET.SubElement(host_attr, "domain:hostName")
                host_name.text = host_attr_data.id

                if host_attr_data.ipv4:
                    host_addr_v4 = ET.SubElement(host_attr, "domain:hostAddr", {"ip": "v4"})
                    host_addr_v4.text = host_attr_data.ipv4
                if host_attr_data.ipv6:
                    host_addr_v6 = ET.SubElement(host_attr, "domain:hostAddr", {"ip": "v6"})
                    host_addr_v6.text = host_attr_data.ipv6

    if domain.registrant:
        if (len(domain.registrant) > 1):
            raise ValueError("Only one registrant is allowed in EPP")
        domain_registrant = ET.SubElement(domain_create, "domain:registrant")
        domain_registrant.text = domain.registrant[0].id

    if domain.contacts:
        contact_types = ["admin", "billing", "tech"]
        for contact_type in contact_types:
            if contact_type in domain.contacts:
                domain_contact = ET.SubElement(domain_create, "domain:contact", {"type": contact_type})
                domain_contact.text = domain.contacts[contact_type]

    if domain.authInfo and domain.authInfo.pw:
        domain_auth_info = ET.SubElement(domain_create, "domain:authInfo")
        domain_pw = ET.SubElement(domain_auth_info, "domain:pw")
        domain_pw.text = domain.authInfo.pw

    if client_request_id:
        cl_trid = ET.SubElement(command, "clTRID")
        cl_trid.text = client_request_id

    xml_string = ET.tostring(epp, encoding="unicode", method="xml")
    xml_string = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + xml_string

    return xml_string

def parse_domain_create_response(xml_string: str) -> DomainCreateResponse:
    """Parses an EPP domain create response XML string."""

    root = ET.fromstring(xml_string)
    namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'domain': 'urn:ietf:params:xml:ns:domain-1.0'}

    domain_name = root.find(".//domain:name", namespaces=namespace).text
    registrant = root.find(".//domain:registrant", namespaces=namespace).text
    cr_date = root.find(".//domain:crDate", namespaces=namespace).text
    ex_date = root.find(".//domain:exDate", namespaces=namespace).text
    up_date = root.find(".//domain:crDate", namespaces=namespace).text
    tr_date = root.find(".//domain:exDate", namespaces=namespace).text
    status = [x.attrib.get("s", None) for x in root.findall(".//domain:status", namespaces=namespace)]
    ns = root.find(".//domain:ns", namespaces=namespace)
    if ns:
        host_objs = [HostObj(x.text) for x in ns.findall(".//domain:hostObj", namespaces=namespace)]
        host_attrs = None
    else:
        host_objs = None
        host_attrs = None
    clid = root.find(".//domain:clID", namespaces=namespace).text
    crid = root.find(".//domain:crID", namespaces=namespace).text
    server_transaction_id = root.find(".//epp:svTRID", namespaces=namespace).text

    domain = Domain(name=domain_name, crDate=cr_date, exDate=ex_date, 
                    upDate=up_date, trDate=tr_date, status=status,
                    clID=clid, crID=crid,
                    ns=NS(host_objs=host_objs, host_attrs=None) if host_objs else NS(host_attrs=host_attrs, host_objs=None) if host_attrs else None)
    response = DomainCreateResponse(domain=domain, server_transaction_id=server_transaction_id)
    return response
