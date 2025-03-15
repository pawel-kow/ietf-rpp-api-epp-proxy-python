import xml.etree.ElementTree as ET
from models import Domain

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
        if "host_objs" in domain.ns:
            #TODO: implement host_objs
            pass
        if "host_attrs" in domain.ns:
            for host_attr_data in domain.ns["host_attrs"]:
                host_attr = ET.SubElement(domain_ns, "domain:hostAttr")
                host_name = ET.SubElement(host_attr, "domain:hostName")
                host_name.text = host_attr_data["host_name"]

                if "ipv4" in host_attr_data:
                    host_addr_v4 = ET.SubElement(host_attr, "domain:hostAddr", {"ip": "v4"})
                    host_addr_v4.text = host_attr_data["ipv4"]
                if "ipv6" in host_attr_data:
                    host_addr_v6 = ET.SubElement(host_attr, "domain:hostAddr", {"ip": "v6"})
                    host_addr_v6.text = host_attr_data["ipv6"]

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

