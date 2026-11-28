%%%
title = "DENIC RRI Profile for the RESTful Provisioning Protocol (RPP)"
abbrev = "RPP DENIC RRI Profile"
area = "Applications and Real-Time"
workgroup = "Network Working Group"
submissiontype = "IETF"
keyword = ["RPP", "provisioning", "registry", "profile", "RRI"]
TocDepth = 4
date = 2026-11-27

[seriesInfo]
name = "Internet-Draft"
value = "draft-kowalik-rpp-denic-rri-profile-00"
stream = "IETF"
status = "informational"

[[author]]
initials="P."
surname="Kowalik"
fullname="Pawel Kowalik"
organization = "DENIC"

%%%

.# Abstract

This document defines a private profile of the RESTful Provisioning Protocol (RPP) for a server whose registry operates the DENIC Registry Robot Interface (RRI) version 5.0. It constrains a domain name to its holders and its DNS data: a domain name has a registrant, refers to no host object, and has no contacts other than further holders. Host objects are not provisioned.

{mainmatter}

# Introduction {#introduction}

This section states the purpose of the profile, what it constrains, and its motivation.

The registry of a server that implements the DENIC RRI extension (`de.denic.rpp.rri`, [rri-extension](rri-extension.md)) holds no host objects: the name servers of a domain name are attributes of the domain name. The contacts of a domain name are its holders, one to five, and its request contacts, which the extension defines as data elements of their own. The base specifications permit more: Host Data Objects, references to them in the `nameservers` of a domain name, contact roles such as `admin` and `tech`, and a domain name without a registrant. The profile constrains a client to what the registry holds, so that a client can validate a request against the Preset Schema before it sends it, and a server refuses what the registry cannot hold in the same way for every constraint.

The profile constrains the Domain Name Data Object and the Host Data Object of [@!I-D.ietf-rpp-data-objects]. It requires the DENIC RRI extension, which defines the meaning of the label `registrant` in the `contacts` of a domain name.

The profile follows the Profile Specification Format of [@!I-D.wullink-rpp-extension-guidelines]. It only constrains: it defines no data element, operation, result code, header field, or endpoint. A request that breaks a constraint of the profile is refused with the result code 02308 and the Problem Detail field `profile` [@!I-D.ietf-rpp-core], and a request that does not conform to the preset is refused with 400 as without the profile.

## Conventions and Terminology {#terminology}

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [@!RFC2119] [@!RFC8174] when, and only when, they appear in all capitals, as shown here.

The terms Profile, Preset, Applicable Profiles, and Profile Binding are used as defined in [@!I-D.ietf-rpp-data-objects]. The terms Profile Schema, Constraints Mapper (`rpp:constraints`), Preset Schema, and Effective Schema are used as defined in [@!I-D.ietf-rpp-json]. The DENIC RRI extension is `de.denic.rpp.rri`.

The following terms are used in this document:

RRI
: The DENIC Registry Robot Interface, version 5.0 [@DENIC-RRI].

Holder
: A contact of the registry that holds a domain name. The first holder of a domain name is its `registrant`, and each further holder is an entry of its `contacts` with the label `registrant`, as defined in [rri-extension](rri-extension.md#domain-name-data-elements).

# Profile Overview {#overview}

| Field | Value |
| ----- | ----- |
| Name | DENIC RRI profile |
| Identifier | `de.denic.rpp.profile.rri` |
| Version | 1.0 |
| RPP version | 1.0 |
| Required extensions | `de.denic.rpp.rri` 0.4.0 |
| Base profiles | None |
| Profile Schema `$id` | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/rri-profile.schema.json> |
| Specification | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/docs/rri/rri-profile.md> |
Table: Profile Overview

The preset that applies the profile MUST contain every extension the profile requires, directly or through its base profiles [@!I-D.ietf-rpp-data-objects].

# Constrained Data Objects {#constrained-data-objects}

## Domain Name Data Object {#domain-name}

* Identifier: domainName

### Data Elements

* Registrant
  * Identifier: registrant
  * Cardinality: 1
  * Constraints:
    * The data element is required in the input of the Create operation and of a full update. A partial update MUST NOT remove it.
* Contacts
  * Identifier: contacts
  * Label Constraints:
    * The value MUST be `registrant`.
* Nameservers
  * Identifier: nameservers
  * Cardinality: 0
  * Constraints:
    * The input of the Create and Update operations MUST NOT contain the data element. A client states the name servers of the domain name as records of type `ns` in the DNS Data (`dns`).

### Operations

None. The constraints apply to the input of the Create and Update operations, and so to a full and a partial update. A server that cannot hold an operation of a partial update at all, such as the addition of a reference to a Host Data Object or of a contact with a label other than `registrant`, refuses it as it does without the profile, before it checks the profile. The removal of the registrant by a partial update is refused with 02308.

## Host Data Object {#host}

* Identifier: host

### Data Elements

None.

### Operations

The Availability, Create, Read, Update, and Delete operations are unavailable. No Host Data Object is provisioned, so no domain name refers to one. A server that does not offer the Host Data Object refuses its operations with 501 as without the profile.

# Constrained Process Objects {#constrained-process-objects}

None.

# Server Requirements {#server-requirements}

None.

# JSON Schema {#json-schema}

The Profile Schema of the profile, in the file `.spec/rri-profile.schema.json`. The profile constrains the definitions `domainName.create` and `domainName.update` of [@!I-D.ietf-rpp-json], which it names by the identifier `urn:ietf:params:rpp:schema:json-1.0` of the base JSON Schema document. Both definitions take the same constraint. A read is not validated against it.

<!-- profile-schema -->
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/rri-profile.schema.json",
  "rpp:profile": {
    "id": "de.denic.rpp.profile.rri",
    "version": "1.0"
  },
  "rpp:constraints": {
    "urn:ietf:params:rpp:schema:json-1.0#/$defs/domainName.create": "#/$defs/profile.rri.domainName",
    "urn:ietf:params:rpp:schema:json-1.0#/$defs/domainName.update": "#/$defs/profile.rri.domainName"
  },
  "$defs": {
    "profile.rri.domainName": {
      "required": [
        "registrant"
      ],
      "properties": {
        "contacts": {
          "items": {
            "properties": {
              "label": {
                "enum": [
                  "registrant"
                ]
              }
            }
          }
        },
        "nameservers": false
      }
    }
  }
}
```

# Constraints Not Expressed in JSON Schema {#constraints-not-expressed}

The following constraints are not expressed in the Profile Schema and MUST be enforced by implementations:

* The unavailable operations of the Host Data Object, see (#host).

# Examples {#examples}

Each example that is valid is valid with and without the profile. Each example that violates the profile is valid under a preset that contains the required extensions and not the profile, and is refused with 02308 under the preset that applies the profile. This section is non-normative.

Example domain create request with two holders and the name servers in the DNS data:

<!-- example valid domainName.create -->
```json
{
    "@type": "domainName",
    "name": "foo.example",
    "registrant": { "@type": "contact", "id": "DENIC-1000022-HOLDER" },
    "contacts": [
        { "label": "registrant", "object": { "@type": "contact", "id": "DENIC-1000022-HOLDER2" } }
    ],
    "dns": {
        "@type": "dnsData",
        "records": [
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns1.example.com." } },
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns2.example.com." } }
        ]
    }
}
```

Example domain create request without a registrant:

<!-- example violates domainName.create -->
```json
{
    "@type": "domainName",
    "name": "foo.example",
    "dns": {
        "@type": "dnsData",
        "records": [
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns1.example.com." } },
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns2.example.com." } }
        ]
    }
}
```

Example domain create request with a technical contact:

<!-- example violates domainName.create -->
```json
{
    "@type": "domainName",
    "name": "foo.example",
    "registrant": { "@type": "contact", "id": "DENIC-1000022-HOLDER" },
    "contacts": [
        { "label": "tech", "object": { "@type": "contact", "id": "DENIC-1000022-TECH" } }
    ],
    "dns": {
        "@type": "dnsData",
        "records": [
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns1.example.com." } },
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns2.example.com." } }
        ]
    }
}
```

Example domain create request with host references:

<!-- example violates domainName.create -->
```json
{
    "@type": "domainName",
    "name": "foo.example",
    "registrant": { "@type": "contact", "id": "DENIC-1000022-HOLDER" },
    "nameservers": [
        { "@type": "host", "hostName": "ns1.example.com" },
        { "@type": "host", "hostName": "ns2.example.com" }
    ]
}
```

Example domain full update request with a registrant:

<!-- example valid domainName.update -->
```json
{
    "@type": "domainName",
    "registrant": { "@type": "contact", "id": "DENIC-1000022-HOLDER" },
    "dns": {
        "@type": "dnsData",
        "records": [
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns1.example.com." } },
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns2.example.com." } }
        ]
    }
}
```

Example domain full update request without a registrant:

<!-- example violates domainName.update -->
```json
{
    "@type": "domainName",
    "dns": {
        "@type": "dnsData",
        "records": [
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns1.example.com." } },
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns2.example.com." } }
        ]
    }
}
```

A partial update that removes the registrant, with the operation `remove` at `/registrant`, is refused with 02308.

# IANA Considerations {#iana}

This document has no IANA actions. The profile is a private profile, and its identifier is formed by reverse domain name notation under the domain `denic.de` [@!I-D.wullink-rpp-extension-guidelines]. It is not registered in the RPP Profiles registry, and its Profile Schema is not registered in the RPP JSON Schema Profiles registry.

# Security Considerations {#security}

A profile constrains and cannot relax a constraint of the specifications it constrains. A server enforces the constraints on every request, whether or not the client validated the request against the Preset Schema.

# Privacy Considerations {#privacy}

The profile requires a registrant for every domain name, which the registry requires as well. It adds no data element, and a client provides no personal data under the profile that it does not provide without it.

{removeInRFC="true"}
{toc="exclude"}
# Changes History

{toc="exclude"}
{numbered="false"}
## 1.0

* initial version #183
* require the extension de.denic.rpp.rri 0.3.0 #248
* require the extension de.denic.rpp.rri 0.4.0 #261

{backmatter}

<reference anchor="DENIC-RRI" target="https://www.denic.de/">
  <front>
    <title>Registry Robot Interface (RRI), Version 5.0</title>
    <author>
      <organization>DENIC eG</organization>
    </author>
  </front>
</reference>
