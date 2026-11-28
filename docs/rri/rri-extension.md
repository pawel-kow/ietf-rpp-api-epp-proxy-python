%%%
title = "DENIC RRI Extension for the RESTful Provisioning Protocol (RPP)"
abbrev = "RPP DENIC RRI Extension"
area = "Applications and Real-Time"
workgroup = "Network Working Group"
submissiontype = "IETF"
keyword = ["RPP", "provisioning", "registry", "extension", "RRI"]
TocDepth = 4
date = 2026-11-14

[seriesInfo]
name = "Internet-Draft"
value = "draft-kowalik-rpp-denic-rri-00"
stream = "IETF"
status = "informational"

[[author]]
initials="P."
surname="Kowalik"
fullname="Pawel Kowalik"
organization = "DENIC"

%%%

.# Abstract

This document defines a private extension of the RESTful Provisioning Protocol (RPP) for a server whose registry operates the DENIC Registry Robot Interface (RRI) version 5.0. The extension defines the Request Contact Data Object, adds the General Request and Abuse contacts to the Domain Name Data Object, and adds the data of the domain to the Create operation of the Domain Transfer Process Object.

{mainmatter}

# Introduction {#introduction}

This section states the purpose of the extension, the specifications it builds upon, and the reasons for the extension points it uses.

The RESTful Provisioning Protocol (RPP) is defined by [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], and [@!I-D.ietf-rpp-json]. This document extends these base specifications for a server that provisions objects in a registry operating the DENIC Registry Robot Interface (RRI) version 5.0 [@DENIC-RRI]. It follows the extension specification format of [@!I-D.wullink-rpp-extension-guidelines, section 9].

The registry holds data for which the base specifications define no data element:

Request contacts
: A domain name has, in addition to its holders, at most one General Request contact and at most one Abuse contact. Both are registry contacts of type `REQUEST`, which consist of a handle and a URI Template [@!RFC6570] that states where requests about the domain name are sent. A request contact has no name, no postal address, and no status. It therefore cannot be represented as a Contact Data Object [@!I-D.ietf-rpp-data-objects, section 12], whose Contact Information (`contactInfo`) and Status (`status`) data elements are required.

Transfer data
: The only transfer of the registry (CHPROV) is requested by the gaining client together with the complete data of the domain name: its holders, its request contacts, and its DNS data, all of which belong to the gaining client. The Domain Transfer Process Object has no data element for this data.

The registry also limits what a client provisions with the data elements of the base specifications: it holds no host objects, a domain name has at least one holder, and the contacts of a domain name are its holders and its request contacts. These limits only constrain, so they are not part of the extension. They are specified as the DENIC RRI profile (`de.denic.rpp.profile.rri`, [rri-profile](rri-profile.md)). The preset `de.denic.rpp.preset.rri` ([rri-preset](rri-preset.md)) contains the extension without the profile, and the preset `de.denic.rpp.preset.rri-strict` ([rri-strict-preset](rri-strict-preset.md)) applies the profile as well.

## Conventions and Terminology {#terminology}

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [@!RFC2119] [@!RFC8174] when, and only when, they appear in all capitals, as shown here.

Terms of the RPP data model, such as Data Object, Component Object, Process Object, data element, cardinality, mutability, Identifier, Unique Identifier, Input Data Element, Reference, Owner Data Object, and This Object, are used as defined in [@!I-D.ietf-rpp-data-objects]. The terms Extension Mapper (`rpp:extends`) and Effective Schema are used as defined in [@!I-D.ietf-rpp-json].

The following terms are used in this document:

RRI
: The DENIC Registry Robot Interface, version 5.0 [@DENIC-RRI].

RegAcc
: A registrar account of the registry. A client of an RPP server that implements this extension acts for one RegAcc, identified by its RegAccId (for example `DENIC-1000022`).

Handle
: The identifier of a contact in the registry, of the form `DENIC-<RegAccId number>-<suffix>`, with 9 to 32 characters. Contacts of all types share one namespace of handles.

Request contact
: A contact of the registry of type `REQUEST`, represented by the Request Contact Data Object (#request-contact).

## Choice of Extension Points {#choice}

This section is non-normative.

A request contact is defined as a new Data Object and not as an object that extends the Contact Data Object by inheritance [@!I-D.ietf-rpp-data-objects, section 2.5]. A derived object inherits every data element of its base object with its cardinality and cannot relax it. A Request Contact derived from the Contact Data Object would therefore carry an empty Contact Information and a status that the registry does not hold. The URI Template cannot be carried in the `links` of the Contact Information either, as a template with a variable such as `{Alabel}` is not a URI. Adding a URI Template data element to the Contact Data Object leaves Contact Information required as well. The new Data Object repeats only the Handle ID and the Provisioning Metadata of the Contact Data Object, see [@!I-D.wullink-rpp-extension-guidelines, section 6].

The General Request and Abuse contacts are defined as data elements of their own and not as labels of the `contacts` data element of the Domain Name Data Object, because they refer to Request Contact Data Objects and not to Contact Data Objects.

# Extension Overview {#overview}

This section identifies the extension.

| Field                | Value                                                                                         |
| -------------------- | --------------------------------------------------------------------------------------------- |
| Name                 | DENIC RRI                                                                                     |
| Identifier           | `de.denic.rpp.rri`                                                                            |
| Version              | 0.2.0                                                                                         |
| RPP version          | [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], [@!I-D.ietf-rpp-json]                   |
| Schema `$id`         | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/rri-extension.schema.json> |
| Changed base objects | `domainName`, `domainTransferProcess`                                                         |
| New objects          | `requestContact`, `requestContactAvailability`                                                |
Table: Extension Overview

# External Data Types {#external-data-types}

None.

# Result Codes {#result-codes}

None. The extension uses the result codes of [@!I-D.ietf-rpp-core, section 18].

# Problem Details {#problem-details}

None.

# HTTP Headers {#http-headers}

None. The Object Authorisation of a transfer request is conveyed in the `RPP-Authorization` header field [@!I-D.ietf-rpp-core, section 6.1], as for any transfer request.

# Discovery Document {#discovery}

This section states the additions of the extension to the Discovery document.

A server that supports the extension lists it in the `extensions` of its Discovery document with the values of (#overview).

A server that supports the extension lists `requestContact` in the `objects` of its Discovery document.

# Updated Data Objects {#updated-data-objects}

This section defines the data elements that the extension adds to existing Data Objects.

## Domain Name Data Object {#domain-name}

* Identifier: domainName

### Data Elements {#domain-name-data-elements}

The following data elements are added to the Domain Name Data Object.

* General Request Contact
  * Identifier: generalRequest
  * Cardinality: 0-1
  * Mutability: read-write
  * Data Type: Aggregation[Request Contact Data Object]
  * Description: The request contact to which general requests about the domain name are sent.
  * Constraints:
    * The relation MUST correspond to a Request Contact Data Object of the sponsoring client.
* Abuse Contact
  * Identifier: abuse
  * Cardinality: 0-1
  * Mutability: read-write
  * Data Type: Aggregation[Request Contact Data Object]
  * Description: The request contact to which reports of abuse of the domain name are sent.
  * Constraints:
    * The relation MUST correspond to a Request Contact Data Object of the sponsoring client.

The roles of these data elements are not labels of the `contacts` data element. A server that supports the extension MUST reject a `contacts` entry with the label `generalRequest` or `abuse`.

On a server that supports the extension, the `contacts` data element holds only the holders after the first, labelled `registrant`.

The Create, Read, and Update operations [@!I-D.ietf-rpp-data-objects, section 11.3] process these data elements as any other read-write data element. A full update that omits one of them removes it from the domain name.

### Operations {#domain-name-operations}

None.

# New Data Objects {#new-data-objects}

This section defines the Data Objects and Component Objects that the extension introduces.

## Request Contact Data Object {#request-contact}

### Object Description

* Name: Request Contact Data Object
* Identifier: requestContact
* Unique Identifier: id
* Description: A Request Contact Data Object represents a URI Template to which requests about the domain names that refer to it are sent. The server expands the template for a domain name where it publishes it, for example in a registration data directory service.

### Data Elements {#request-contact-data-elements}

The following data elements are defined for the Request Contact Data Object.

* Handle ID
  * Identifier: id
  * Cardinality: 1
  * Mutability: create-only
  * Data Type: Identifier
  * Description: External unique identifier of the request contact.
  * Constraints:
    * This value MUST be provided by the client.
    * Request contacts and Contact Data Objects share one namespace of identifiers.
* Provisioning Metadata
  * Identifier: provMetadata
  * Cardinality: 1
  * Mutability: read-only
  * Data Type: Provisioning Metadata Object
  * Description: Standard metadata about the object's lifecycle and ownership.
  * Constraints: (None)
* URI Template
  * Identifier: uriTemplate
  * Cardinality: 1
  * Mutability: read-write
  * Data Type: String
  * Description: A URI Template [@!RFC6570] that states where requests are sent. The variables `{Alabel}` and `{Ulabel}` stand for the domain name in its A-label and U-label form.
  * Constraints:
    * The value MUST contain between 8 and 1024 characters.
    * The value MUST be a URI Template of level 1 [@!RFC6570, section 1.2] with the scheme `http`, `https`, or `mailto`.
    * The value MUST NOT contain variables other than `{Alabel}` and `{Ulabel}`. Variable names are case-sensitive.

The Request Contact Data Object has no status and no authorisation information.

### Operations {#request-contact-operations}

#### Availability Operation

* Identifier: availability

The Availability operation allows a client to determine whether a Request Contact resource with the given Handle ID can be created.

The operation has no input data elements and takes no object representation as input. The client identifies the resource by its Reference only.

* Authorisation:
  * Any authenticated client is authorised to perform this operation.

* Output:
  * Object: Request Contact Availability Object

A Handle ID of a Contact Data Object is not available for a Request Contact Data Object, and vice versa.

#### Create Operation

* Identifier: create

The Create operation allows a client to provision a new Request Contact resource. The operation accepts as input all create-only and read-write data elements defined for the Request Contact Data Object.

* Authorisation:
  * Each client is authorised to create new request contact objects, becoming their sponsoring client.

* Input:
  * Object: This Object
* Output:
  * Object: This Object

The server MUST reject a URI Template that does not satisfy the constraints of (#request-contact-data-elements).

#### Read Operation

* Identifier: read

The Read operation allows a client to retrieve the data elements of a Request Contact resource.

* Authorisation:
  * Only the sponsoring client is authorised to perform this operation.

* Input:
  * Reference: This Object
* Output:
  * Object: This Object

The server MUST respond to a Read operation for the Handle ID of a Contact Data Object as for an object that does not exist. Likewise, the server MUST respond to a Read operation on a Contact Data Object for the Handle ID of a Request Contact Data Object as for an object that does not exist.

#### Update Operation

* Identifier: update

The Update operation allows a client to modify the URI Template of an existing Request Contact resource.

* Authorisation:
  * Only the sponsoring client is authorised to perform this operation.

* Input:
  * Reference: This Object
  * Object: This Object
* Output:
  * Object: This Object

An update that does not change the URI Template completes successfully without a change.

#### Delete Operation

* Identifier: delete

The Delete operation is not supported. The registry deletes request contacts that are not referred to by any domain name itself, after a retention period [@DENIC-RRI].

### Processes

The Request Contact Data Object supports no Process Objects.

## Request Contact Availability Object {#request-contact-availability}

* Name: Request Contact Availability Object
* Identifier: requestContactAvailability
* Extends: Base Availability Object
* Description: The result of an Availability operation on a Request Contact Data Object.
* Data Elements: (None)

# Updated Process Objects {#updated-process-objects}

This section defines the additions of the extension to existing Process Objects.

## Domain Transfer Process Object {#domain-transfer-process}

* Identifier: domainTransferProcess

### Data Elements

None.

### Operations

#### Create (Transfer Request) {#transfer-create}

* Identifier: transferCreate

The extension adds the following Input Data Elements to the Create operation [@!I-D.ietf-rpp-data-objects, section 10.1.1.1]. They state the domain name as the gaining client holds it after the transfer.

* Input:
  * Reference: Owner Data Object
  * Object: Domain Transfer Process Object
  * Input Data Elements:
    * Registrant
      * Identifier: registrant
      * Cardinality: 1
      * Data Type: Aggregation[Contact Data Object]
      * Description: The first holder of the domain name.
      * Constraints:
        * The relation MUST correspond to a Contact Data Object of the gaining client.
    * Contacts
      * Identifier: contacts
      * Cardinality: 0+
      * Data Type: LabelledAggregation[Contact Data Object]
        * Label Description: The role of the associated contact.
        * Label Constraints:
          * The value MUST be `registrant`.
      * Description: The holders of the domain name after the first.
      * Constraints:
        * Each relation MUST correspond to a Contact Data Object of the gaining client.
    * General Request Contact
      * Identifier: generalRequest
      * Cardinality: 0-1
      * Data Type: Aggregation[Request Contact Data Object]
      * Description: As defined in (#domain-name-data-elements).
      * Constraints:
        * The relation MUST correspond to a Request Contact Data Object of the gaining client.
    * Abuse Contact
      * Identifier: abuse
      * Cardinality: 0-1
      * Data Type: Aggregation[Request Contact Data Object]
      * Description: As defined in (#domain-name-data-elements).
      * Constraints:
        * The relation MUST correspond to a Request Contact Data Object of the gaining client.
    * DNS
      * Identifier: dns
      * Cardinality: 1
      * Data Type: DNS Data Object
      * Description: The DNS data of the domain name.
      * Constraints:
        * The records MUST be of the types `ns`, `a`, `aaaa`, `mx`, or `dnskey`.
* Output:
  * Object: Domain Transfer Process Object

The transfer is completed immediately. The server MUST respond with the Domain Transfer Process Object in the state `serverApproved`, with `reqClientId` and `actClientId` set to the identifier of the gaining client, and `requestDate` and `actionDate` set to the time of completion. The server informs the losing client with a message.

The server MUST reject a transfer request without Object Authorisation, and a transfer request whose Input Data Elements refer to an object of another client.

The Read (Transfer Query), Delete (Transfer Cancel), Approve, and Reject operations are not supported. A push transfer is not supported.

# New Process Objects {#new-process-objects}

None.

# Endpoints {#endpoints}

This section lists the endpoints that result from the new Data Object, derived by the rules of [@!I-D.ietf-rpp-core, section 16.1]. The `plural()` function applied to the Identifier `requestContact` gives the collection path segment `requestContacts`. This section is non-normative.

| Operation                     | HTTP Method | URL path                             |
| ----------------------------- | ----------- | ------------------------------------ |
| Request Contact: read         | GET         | /requestContacts/{id}                |
| Request Contact: create       | POST        | /requestContacts                     |
| Request Contact: update       | PUT or PATCH | /requestContacts/{id}               |
| Request Contact: delete       | DELETE      | /requestContacts/{id}                |
| Request Contact: availability | HEAD or GET | /requestContacts/{id}/availability   |
Table: Endpoints of the Request Contact Data Object

The data elements that the extension adds to the Domain Name Data Object and the Domain Transfer Process Object do not have Direct Access and add no endpoints.

The endpoints behave as defined for the corresponding operations in [@!I-D.ietf-rpp-core, section 16]:

* Availability for Creation [@!I-D.ietf-rpp-core, section 16.4]
  * Request: HEAD|GET /requestContacts/{id}/availability
  * Request message: None
  * Response message: Request Contact Availability Object (GET only)
* Resource Information [@!I-D.ietf-rpp-core, section 16.5]
  * Request: GET /requestContacts/{id}
  * Request message: None
  * Response message: Request Contact Data Object
* Create Resource [@!I-D.ietf-rpp-core, section 16.6]
  * Request: POST /requestContacts
  * Request message: Request Contact Data Object
  * Response message: Request Contact Data Object
* Update Resource [@!I-D.ietf-rpp-core, section 16.8]
  * Request: PUT|PATCH /requestContacts/{id}
  * Request message: Request Contact Data Object (PUT) or partial update (PATCH)
  * Response message: Request Contact Data Object
* Delete Resource [@!I-D.ietf-rpp-core, section 16.7]
  * Request: DELETE /requestContacts/{id}
  * Response: HTTP status code 501 (Not Implemented), RPP result code 02101

Example Request Contact Create request:

```http
POST /requestContacts HTTP/1.1
Host: rpp.example
Authorization: Bearer <token>
Accept: application/rpp+json
Content-Type: application/rpp+json
RPP-Cltrid: ABC-12345
Content-Length: 104
```

Example Request Contact Create response:

```http
HTTP/1.1 201 Created
Date: Sat, 14 Nov 2026 12:00:00 GMT
Content-Type: application/rpp+json
Location: https://rpp.example/rpp/requestContacts/DENIC-1000022-GR
RPP-Svtrid: XYZ-12345
RPP-Cltrid: ABC-12345
RPP-Code: 01000
```

Example Domain Transfer request with the Input Data Elements of the extension and Object Authorisation:

```http
POST /domainNames/foo.example/processes/transferProcesses HTTP/1.1
Host: rpp.example
Authorization: Bearer <token>
Accept: application/rpp+json
Content-Type: application/rpp+json
RPP-Cltrid: ABC-12346
RPP-Authorization: authinfo value=QWJjMjM0NTY3OA==
Content-Length: 420
```

Example Domain Transfer response for a transfer that is completed immediately [@!I-D.ietf-rpp-core, section 16.1.4]:

```http
HTTP/1.1 200 OK
Date: Sat, 14 Nov 2026 12:00:00 GMT
Content-Type: application/rpp+json
RPP-Svtrid: XYZ-12346
RPP-Cltrid: ABC-12346
RPP-Code: 01000
```

# JSON Schema {#json-schema}

This section defines the JSON representation of the new and updated objects, following the rules of [@!I-D.ietf-rpp-json, section 4] and the Extension Framework of [@!I-D.ietf-rpp-json, section 7].

The extension defines one JSON Schema document, <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/rri-extension.schema.json>. Its definitions are shown below. Every definition of the extension has the prefix `ext.rri.`.

## Extension Mapping {#extension-mapping}

The Extension Mapper maps the base definitions to the definitions of the extension:

```json
{
  "rpp:extends": {
    "#/$defs/domainName.create": "#/$defs/ext.rri.domainName.create",
    "#/$defs/domainName.read": "#/$defs/ext.rri.domainName.read",
    "#/$defs/domainName.update": "#/$defs/ext.rri.domainName.update",
    "#/$defs/domainTransferProcess.create": "#/$defs/ext.rri.domainTransferProcess.create"
  }
}
```

The keys of the Extension Mapper and the `$ref` values refer to the base definitions by their keys in the shared `$defs` object [@!I-D.ietf-rpp-json, section 4.10], because the JSON Schema document of the base specifications has no `$id` yet.

The schema document states the Name, Identifier, Version, and New objects of (#overview) in the property `rpp:extension`:

```json
{
  "rpp:extension": {
    "name": "DENIC RRI",
    "id": "de.denic.rpp.rri",
    "version": "0.2.0",
    "objects": ["requestContact"]
  }
}
```

## Domain Name Data Object {#json-domain-name}

Create request schema:

<!-- definition ext.rri.domainName.create -->
```json
{
  "$defs": {
    "ext.rri.domainName.create": {
      "type": "object",
      "properties": {
        "generalRequest": { "$ref": "#/$defs/ext.rri.requestContact.reference" },
        "abuse": { "$ref": "#/$defs/ext.rri.requestContact.reference" }
      }
    }
  }
}
```

Read response schema:

<!-- definition ext.rri.domainName.read -->
```json
{
  "$defs": {
    "ext.rri.domainName.read": {
      "type": "object",
      "properties": {
        "generalRequest": { "$ref": "#/$defs/ext.rri.requestContact.reference" },
        "abuse": { "$ref": "#/$defs/ext.rri.requestContact.reference" }
      }
    }
  }
}
```

Update request schema:

<!-- definition ext.rri.domainName.update -->
```json
{
  "$defs": {
    "ext.rri.domainName.update": {
      "type": "object",
      "properties": {
        "generalRequest": { "$ref": "#/$defs/ext.rri.requestContact.reference" },
        "abuse": { "$ref": "#/$defs/ext.rri.requestContact.reference" }
      }
    }
  }
}
```

## Request Contact Data Object {#json-request-contact}

### Availability

The response of the Availability operation is the Request Contact Availability Object:

<!-- definition ext.rri.requestContactAvailability.read -->
```json
{
  "$defs": {
    "ext.rri.requestContactAvailability.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "requestContactAvailability", "readOnly": true },
        "available": { "type": "boolean", "readOnly": true },
        "reason": { "type": "string", "readOnly": true }
      },
      "required": ["@type", "available"]
    }
  }
}
```

### Create

Create request schema (create-only and read-write properties):

<!-- definition ext.rri.requestContact.create -->
```json
{
  "$defs": {
    "ext.rri.requestContact.create": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "requestContact" },
        "id": { "$ref": "#/$defs/identifier" },
        "uriTemplate": { "$ref": "#/$defs/ext.rri.uriTemplate" }
      },
      "required": ["@type", "id", "uriTemplate"]
    }
  }
}
```

The URI Template is a String with the length constraints of (#request-contact-data-elements). The other constraints of the URI Template cannot be expressed in JSON Schema and MUST be enforced by implementations.

<!-- definition ext.rri.uriTemplate -->
```json
{
  "$defs": {
    "ext.rri.uriTemplate": { "type": "string", "minLength": 8, "maxLength": 1024 }
  }
}
```

### Read

Read response schema (read-write and read-only properties):

<!-- definition ext.rri.requestContact.read -->
```json
{
  "$defs": {
    "ext.rri.requestContact.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "requestContact", "readOnly": true },
        "id": { "$ref": "#/$defs/identifier", "readOnly": true },
        "provMetadata": { "$ref": "#/$defs/provMetadata.read", "readOnly": true },
        "uriTemplate": { "$ref": "#/$defs/ext.rri.uriTemplate" }
      },
      "required": ["@type", "id", "provMetadata", "uriTemplate"]
    }
  }
}
```

### Update

Update request schema (read-write properties):

<!-- definition ext.rri.requestContact.update -->
```json
{
  "$defs": {
    "ext.rri.requestContact.update": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "requestContact" },
        "uriTemplate": { "$ref": "#/$defs/ext.rri.uriTemplate" }
      },
      "required": ["@type", "uriTemplate"]
    }
  }
}
```

### Reference

Reference schema (identifier only):

<!-- definition ext.rri.requestContact.reference -->
```json
{
  "$defs": {
    "ext.rri.requestContact.reference": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "requestContact" },
        "id": { "$ref": "#/$defs/identifier" }
      },
      "required": ["@type", "id"]
    }
  }
}
```

## Domain Transfer Process Object {#json-domain-transfer-process}

### Create

Create request schema:

<!-- definition ext.rri.domainTransferProcess.create -->
```json
{
  "$defs": {
    "ext.rri.domainTransferProcess.create": {
      "type": "object",
      "properties": {
        "registrant": { "$ref": "#/$defs/contact.reference", "writeOnly": true },
        "contacts": {
          "type": "array",
          "writeOnly": true,
          "items": {
            "type": "object",
            "properties": {
              "label": { "type": "string" },
              "object": { "$ref": "#/$defs/contact.reference" }
            },
            "required": ["label", "object"]
          }
        },
        "generalRequest": { "$ref": "#/$defs/ext.rri.requestContact.reference", "writeOnly": true },
        "abuse": { "$ref": "#/$defs/ext.rri.requestContact.reference", "writeOnly": true },
        "dns": { "$ref": "#/$defs/dnsData.create", "writeOnly": true }
      },
      "required": ["registrant", "dns"]
    }
  }
}
```

# Examples {#examples}

This section contains examples of the new and updated objects. Each valid example validates against the Effective Schema [@!I-D.ietf-rpp-json, section 7.2] of a server that supports the extension, and each invalid example fails it. This section is non-normative.

## Request Contact {#examples-request-contact}

### Availability

Example request contact availability response for a request contact that cannot be created:

<!-- example valid requestContactAvailability.read -->
```json
{
    "@type": "requestContactAvailability",
    "available": false,
    "reason": "In use"
}
```

### Create

Example request contact create request:

<!-- example valid requestContact.create -->
```json
{
    "@type": "requestContact",
    "id": "DENIC-1000022-GR",
    "uriTemplate": "https://www.example.com/contact?domain={Alabel}"
}
```

### Read

Example request contact read response:

<!-- example valid requestContact.read -->
```json
{
    "@type": "requestContact",
    "id": "DENIC-1000022-GR",
    "provMetadata": {
        "@type": "provMetadata",
        "spClientId": "DENIC-1000022",
        "upDate": "2026-11-12T00:20:20.0Z"
    },
    "uriTemplate": "https://www.example.com/contact?domain={Alabel}"
}
```

### Update

Example request contact full update request:

<!-- example valid requestContact.update -->
```json
{
    "@type": "requestContact",
    "uriTemplate": "mailto:abuse@example.com"
}
```

Example request contact partial update request:

```json
[
  {
    "op": "replace",
    "path": "/uriTemplate",
    "value": "https://www.example.com/abuse/{Ulabel}"
  }
]
```

## Domain Name {#examples-domain-name}

### Create

Example domain create request with request contacts:

<!-- example valid domainName.create -->
```json
{
    "@type": "domainName",
    "name": "foo.example",
    "registrant": { "@type": "contact", "id": "DENIC-1000022-HOLDER" },
    "generalRequest": { "@type": "requestContact", "id": "DENIC-1000022-GR" },
    "abuse": { "@type": "requestContact", "id": "DENIC-1000022-AB" },
    "dns": {
        "@type": "dnsData",
        "records": [
            { "@type": "dnsRecord", "name": "@", "type": "a", "rdata": { "address": "192.0.2.10" } }
        ]
    }
}
```

### Read

Example domain read response with a second holder and request contacts:

<!-- example valid domainName.read -->
```json
{
    "@type": "domainName",
    "name": "foo.example",
    "provMetadata": { "@type": "provMetadata", "spClientId": "DENIC-1000022" },
    "status": [ { "@type": "domainStatus", "label": "ok" } ],
    "registrant": { "@type": "contact", "id": "DENIC-1000022-HOLDER" },
    "contacts": [
        { "label": "registrant", "object": { "@type": "contact", "id": "DENIC-1000022-HOLDER2" } }
    ],
    "generalRequest": { "@type": "requestContact", "id": "DENIC-1000022-GR" },
    "abuse": { "@type": "requestContact", "id": "DENIC-1000022-AB" }
}
```

### Update

Example partial update request that replaces the abuse contact and removes the general request contact:

```json
[
  {
    "op": "replace",
    "path": "/abuse",
    "value": { "@type": "requestContact", "id": "DENIC-1000022-AB2" }
  },
  {
    "op": "remove",
    "path": "/generalRequest"
  }
]
```

### Transfer Request

Example domain transfer request with the Input Data Elements of the extension:

<!-- example valid domainTransferProcess.create -->
```json
{
    "@type": "domainTransferProcess",
    "registrant": { "@type": "contact", "id": "DENIC-1000002-HOLDER" },
    "generalRequest": { "@type": "requestContact", "id": "DENIC-1000002-GENERAL" },
    "abuse": { "@type": "requestContact", "id": "DENIC-1000002-ABUSE" },
    "dns": {
        "@type": "dnsData",
        "records": [
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns1.example.com." } },
            { "@type": "dnsRecord", "name": "@", "type": "ns", "rdata": { "nsdname": "ns2.example.com." } }
        ]
    }
}
```

## Invalid Examples {#examples-invalid}

Example request contact create request without a URI Template:

<!-- example invalid requestContact.create -->
```json
{
    "@type": "requestContact",
    "id": "DENIC-1000022-GR"
}
```

Example request contact create request with a URI Template of fewer than 8 characters:

<!-- example invalid requestContact.create -->
```json
{
    "@type": "requestContact",
    "id": "DENIC-1000022-GR",
    "uriTemplate": "http://"
}
```

Example domain update request with a Contact Data Object as abuse contact:

<!-- example invalid domainName.update -->
```json
{
    "@type": "domainName",
    "abuse": { "@type": "contact", "id": "DENIC-1000022-HOLDER" }
}
```

Example domain transfer request without the data of the domain name:

<!-- example invalid domainTransferProcess.create -->
```json
{
    "@type": "domainTransferProcess"
}
```

The following domain update request validates against the Effective Schema, but a server that supports the extension rejects it, because `abuse` is not a label of the `contacts` data element (see (#domain-name-data-elements)):

<!-- example valid domainName.update -->
```json
{
    "@type": "domainName",
    "contacts": [
        { "label": "abuse", "object": { "@type": "contact", "id": "DENIC-1000022-AB" } }
    ]
}
```

# IANA Considerations {#iana}

This document has no IANA actions. The extension is a private extension [@!I-D.wullink-rpp-extension-guidelines, section 10], and its Identifier is formed by reverse domain name notation [@!I-D.wullink-rpp-extension-guidelines, section 7].

For a standardised version of the extension, the following entries would be registered in the RPP Data Object Registry [@!I-D.ietf-rpp-data-objects].

Object: requestContact

Object Name: Request Contact Data Object

Object Type: Resource

Description: Represents a URI Template to which requests about domain names are sent.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name          | Card. | Mutability  | Data Type                    | Description                                              |
| ------------------ | --------------------- | ----- | ----------- | ---------------------------- | -------------------------------------------------------- |
| id                 | Handle ID             | 1     | create-only | Identifier                   | External unique identifier of the request contact.       |
| provMetadata       | Provisioning Metadata | 1     | read-only   | Provisioning Metadata Object | Standard metadata about the object's lifecycle and ownership. |
| uriTemplate        | URI Template          | 1     | read-write  | String                       | A URI Template that states where requests are sent.      |

Operations: availability, create, read, update, delete. Input Data Elements: (None). Parameters: (None).

Object: requestContactAvailability

Object Name: Request Contact Availability Object

Object Type: Component

Extends: baseAvailability

Description: The result of an Availability operation on a Request Contact Data Object.

Reference: [This-ID]

Data Elements: (None)

Object: domainName (additions)

Data Elements

| Element Identifier | Element Name            | Card. | Mutability | Data Type                               | Description                                                           |
| ------------------ | ----------------------- | ----- | ---------- | --------------------------------------- | --------------------------------------------------------------------- |
| generalRequest     | General Request Contact | 0-1   | read-write | Aggregation[Request Contact Data Object] | The request contact to which general requests about the domain name are sent. |
| abuse              | Abuse Contact           | 0-1   | read-write | Aggregation[Request Contact Data Object] | The request contact to which reports of abuse of the domain name are sent.   |

Object: domainTransferProcess (additions)

Operation: transferCreate

Input Data Elements

| Identifier     | Name                    | Card. | Data Type                                 | Description                                      |
| -------------- | ----------------------- | ----- | ----------------------------------------- | ------------------------------------------------ |
| registrant     | Registrant              | 1     | Aggregation[Contact Data Object]          | The first holder of the domain name.             |
| contacts       | Contacts                | 0+    | LabelledAggregation[Contact Data Object]  | The holders of the domain name after the first.  |
| generalRequest | General Request Contact | 0-1   | Aggregation[Request Contact Data Object]  | The general request contact of the domain name.  |
| abuse          | Abuse Contact           | 0-1   | Aggregation[Request Contact Data Object]  | The abuse contact of the domain name.            |
| dns            | DNS                     | 1     | DNS Data Object                           | The DNS data of the domain name.                 |

Parameters: (None)

# Security Considerations {#security}

The extension inherits the authentication and authorisation services of the objects it extends [@!I-D.wullink-rpp-extension-guidelines, section 12]. A request contact is accessible to its sponsoring client only. A server MUST reject the use of another client's request contact in any operation, including as a data element of a domain name.

The Object Authorisation of a transfer request is forwarded to the registry. A server MUST NOT record it in logs.

A server forwards the URI Template to the registry, which expands it with a sample domain name on creation and rejects a template that it cannot expand. A server that does not forward the template to such a registry MUST check the constraints of (#request-contact-data-elements) itself before it stores or publishes the template.

# Privacy Considerations {#privacy}

The expanded URI Template of a domain name's request contacts is published in the registry's registration data directory service. A `mailto` template that names the mailbox of a natural person makes that address public. A client SHOULD use a role mailbox or a web form in a request contact, because the template is published for every domain name that refers to it. A request contact holds no other personal data, and the registry rejects verification data on it.

# Internationalisation Considerations {#i18n}

The variable `{Ulabel}` expands to the U-label of the domain name. The encoding of a U-label in the expanded URI is defined by [@!RFC6570, section 3.2.1]. The URI Template itself consists of ASCII characters.

{removeInRFC="true"}
{toc="exclude"}
# Changes History

{toc="exclude"}
{numbered="false"}
## 0.1.0 - 0.2.0

* refer to the profile de.denic.rpp.profile.rri and the presets rri and rri-strict #183
* add the request contact data object #131
* add generalRequest and abuse to the domain name data object and the transfer request, instead of contacts labels #131
* rename the extension identifier from rri to de.denic.rpp.rri #131
* restructure the document to the extension specification format #131

{toc="exclude"}
{numbered="false"}
## 0.1.0

* initial version: the data of the domain name in the transfer request #133

{backmatter}

# Mapping to DENIC RRI {#rri-mapping}

This appendix describes how a server that implements the extension maps it to RRI version 5.0 [@DENIC-RRI]. The facts are collected in rri-5.0-reference.md of the implementation, the gaps in gap-analysis.md.

| RPP                                     | RRI (XML 5.0)                                         |
| --------------------------------------- | ----------------------------------------------------- |
| `requestContact`                        | contact of `contact:type` `REQUEST`                   |
| `requestContact.id`                     | `contact:handle`                                      |
| `requestContact.uriTemplate`            | `contact:uri-template`                                |
| `provMetadata.spClientId`               | the RegAccId that the handle starts with              |
| `provMetadata.upDate`                   | `contact:changed`                                     |
| availability, create, read, update      | contact CHECK, CREATE, INFO, UPDATE                   |
| `domainName.generalRequest`             | `domain:contact role="generalrequest"`                |
| `domainName.abuse`                      | `domain:contact role="abusecontact"`                  |
| `domainTransferProcess` transferCreate  | domain CHPROV with the complete data of the domain    |
Table: Mapping to RRI

The registry holds 0 to 1 request contact of each role per domain name, so a domain name needs none. The backend profile of the implementation states this as `domainName.generalRequest` and `domainName.abuse` with `min_count` 0 and `max_count` 1.

The implementation maps the refusals of the registry to RPP result codes as follows:

| Case                                                                 | HTTP status | RPP result code |
| -------------------------------------------------------------------- | ----------- | --------------- |
| `registrant` or `dns` missing in a transfer request                  | 400         | 02001           |
| no `RPP-Authorization` in a transfer request                         | 400         | 02003           |
| AuthInfo does not match (63370088701), or no AuthInfo2 (56000088709) | 401         | 02202           |
| contact or request contact of another RegAcc (63200020603)           | 403         | 02201           |
| the gaining client already sponsors the domain name (63380063209)   | 409         | 02002           |
| required CHPROV data missing (53370080005)                           | 400         | 02003           |
| URI Template refused by the registry (83000000005)                   | 400         | 02005           |
| Read of a handle of the other kind of contact                        | 404         | 02303           |
| `contacts` entry labelled `generalRequest` or `abuse`                | 501         | 02102           |
| Delete of a request contact                                          | 501         | 02101           |
| Transfer Query, Cancel, Approve, or Reject                           | 501         | 02101           |
Table: Refusals of the implementation

The registry does not document how it encodes a U-label in an expanded template.

<reference anchor="DENIC-RRI" target="https://www.denic.de/">
  <front>
    <title>Registry Robot Interface (RRI), Version 5.0</title>
    <author>
      <organization>DENIC eG</organization>
    </author>
  </front>
</reference>
