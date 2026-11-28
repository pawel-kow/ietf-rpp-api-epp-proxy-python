%%%
title = "Registry Change Messages Extension for the RESTful Provisioning Protocol (RPP)"
abbrev = "RPP Registry Change Messages"
area = "Applications and Real-Time"
workgroup = "Network Working Group"
submissiontype = "IETF"
keyword = ["RPP", "provisioning", "registry", "extension", "messages"]
TocDepth = 4
date = 2026-11-28

[seriesInfo]
name = "Internet-Draft"
value = "draft-kowalik-rpp-registry-change-messages-00"
stream = "IETF"
status = "informational"

[[author]]
initials="P."
surname="Kowalik"
fullname="Pawel Kowalik"
organization = "DENIC"

%%%

.# Abstract

This document defines a private extension of the RESTful Provisioning Protocol (RPP) with message types that notify the sponsoring client of changes that the server made to its objects without a request of the client: the change of the data of a domain name or of a contact, the deletion of a domain name, and the deletion of contacts that no domain name referred to.

{mainmatter}

# Introduction {#introduction}

This section states the purpose of the extension, the specifications it builds upon, and the reasons for the extension points it uses.

The RESTful Provisioning Protocol (RPP) is defined by [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], and [@!I-D.ietf-rpp-json]. This document follows the extension specification format of [@!I-D.wullink-rpp-extension-guidelines, section 9]. It builds on the message components extension [@!RPP-MESSAGES], whose Object Reference Object, Registry Notice Object, and Bulk Base Message Object its message types use, and whose rules for the message types of a dependent extension apply to them.

A registry changes the objects of a client without a request of the client, for example by a decision of the registry, at the request of a court or of the registrant, or by a rule of its policy, such as the deletion of contacts that no domain name refers to. The client keeps a copy of the data of its objects and needs to learn of such a change. The base specifications define no message type for these events [@!I-D.ietf-rpp-data-objects, section 9.19], and a Service Notice Message Object carries no structured data. This extension defines a message type for each event.

The message types name the changed object and do not carry its new data. A client reads the object to learn its data.

## Conventions and Terminology {#terminology}

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [@!RFC2119] [@!RFC8174] when, and only when, they appear in all capitals, as shown here.

Terms of the RPP data model, such as Data Object, Component Object, data element, cardinality, mutability, Handle ID, and message type, are used as defined in [@!I-D.ietf-rpp-data-objects]. The terms Extension Mapper (`rpp:extends`) and Effective Schema are used as defined in [@!I-D.ietf-rpp-json]. The message components extension is the extension `io.github.pawel-kow.rpp.messages` [@!RPP-MESSAGES], and the term dependent extension is used as defined there.

## Choice of Extension Points {#choice}

This section is non-normative.

The events are defined as message types that extend the Base Message Object [@!I-D.ietf-rpp-data-objects, section 9.19.1], as [@!I-D.ietf-rpp-data-objects, section 5] recommends for extensions. A message about one object names it with the Object Type and the Object Identifier of the Base Message Object. The deletion of contacts that no domain name refers to is reported for several contacts at once, so its message type extends the Bulk Base Message Object of the message components extension, which holds a list of Object Reference Objects in place of the single Object Type and Object Identifier.

The notices of the registry about the event are Registry Notice Objects of the message components extension, so that a client reads them in the same form as in the message types of other extensions. The extension is a dependent extension of the message components extension, which states how its message types become part of the Message Data Object and of the `data` property of its JSON representation.

# Extension Overview {#overview}

This section identifies the extension.

| Field                | Value |
| -------------------- | ----- |
| Name                 | RPP Registry Change Messages |
| Identifier           | `io.github.pawel-kow.rpp.registry-changes` |
| Version              | 0.1.0 |
| RPP version          | [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], [@!I-D.ietf-rpp-json] |
| Schema `$id`         | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/registry-changes-extension.schema.json> |
| Changed base objects | `message` |
| New objects          | `domainUpdateMessage`, `contactUpdateMessage`, `domainDeletionMessage`, `contactDeletionMessage` |
Table: Extension Overview

A server that offers a preset with this extension MUST offer the message components extension `io.github.pawel-kow.rpp.messages` [@!RPP-MESSAGES] in the same preset, in version 0.1.0 or a later version with the same major version. The definitions of the extension refer to its Object Reference Object and Registry Notice Object.

# External Data Types {#external-data-types}

None.

# Result Codes {#result-codes}

None.

# Problem Details {#problem-details}

None.

# HTTP Headers {#http-headers}

None.

# Discovery Document {#discovery}

A server that supports the extension lists it in the `extensions` of its Discovery document with the values of (#overview), in each preset that contains it. It lists no object in `objects`.

# Updated Data Objects {#updated-data-objects}

This section states the additions of the extension to the Message Data Object.

## Message Data Object {#message}

* Identifier: message

The message types of (#message-types) are message types of a dependent extension. The Data of a message, the values of the Message Type parameter (`type`) of the Query operation, and the Read and Delete operations follow the rules of the message components extension for them [@!RPP-MESSAGES]. A server that supports the extension sends the notification of an event that a message type of (#message-types) describes as a message of that type.

# New Data Objects {#new-data-objects}

This section defines the message types of the extension. A server uses each of them as the Data (`data`) of a Message Data Object [@!I-D.ietf-rpp-data-objects, section 15]. In a message type that extends the Base Message Object, the Object Type (`objectType`) and the Object Identifier (`objectId`) are required.

| Identifier | Extends | Objects |
| ---------- | ------- | ------- |
| `domainUpdateMessage` | `baseMessage` | a domain name |
| `contactUpdateMessage` | `baseMessage` | a contact |
| `domainDeletionMessage` | `baseMessage` | a domain name |
| `contactDeletionMessage` | `bulkBaseMessage` | several contacts |
Table: Message Types of the Extension

`bulkBaseMessage` is the Bulk Base Message Object of the message components extension [@!RPP-MESSAGES].

## Message Types {#message-types}

### Domain Update Message Object {#domain-update-message}

* Name: Domain Update Message Object
* Identifier: domainUpdateMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that the server changed the data of a domain name. The client reads the domain name to learn its data.
* Data Elements:
  * Notices
    * Identifier: notices
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Registry Notice Object [@!RPP-MESSAGES]
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

### Contact Update Message Object {#contact-update-message}

* Name: Contact Update Message Object
* Identifier: contactUpdateMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that the server changed the data of a contact. The change concerns every domain name that refers to the contact. The client reads the contact to learn its data.
* Data Elements:
  * Notices
    * Identifier: notices
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Registry Notice Object [@!RPP-MESSAGES]
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `contact`, and the Object Identifier (`objectId`) is the Handle ID of the contact.

### Domain Deletion Message Object {#domain-deletion-message}

* Name: Domain Deletion Message Object
* Identifier: domainDeletionMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that the server deleted a domain name, for example by a decision of the registry or because the registrant did not meet an obligation of the registry in time.
* Data Elements:
  * Notices
    * Identifier: notices
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Registry Notice Object [@!RPP-MESSAGES]
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

### Contact Deletion Message Object {#contact-deletion-message}

* Name: Contact Deletion Message Object
* Identifier: contactDeletionMessage
* Extends: Bulk Base Message Object [@!RPP-MESSAGES]
* Description: Notification for the sponsoring client that the server deleted contacts that no domain name referred to.
* Data Elements:
  * Objects
    * Identifier: objects
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Object Reference Object [@!RPP-MESSAGES]
    * Description: The deleted contacts.
    * Constraints:
      * The Object Type of each entry MUST be `contact`.

# Updated Process Objects {#updated-process-objects}

None.

# New Process Objects {#new-process-objects}

None.

# Endpoints {#endpoints}

None. A client retrieves the messages at the messages endpoint [@!I-D.ietf-rpp-core, section 16.10] and selects them with the `type` query parameter. This section is non-normative.

Example request for the oldest message about a change of a domain name or a contact:

```http
GET /messages?type=domainUpdateMessage&type=contactUpdateMessage HTTP/1.1
Host: rpp.example
Authorization: Bearer <token>
Accept: application/rpp+json
RPP-Cltrid: ABC-12361
```

# JSON Schema {#json-schema}

This section defines the JSON representation of the message types, following the rules of [@!I-D.ietf-rpp-json, section 4] and the Extension Framework of [@!I-D.ietf-rpp-json, section 7].

The extension defines one JSON Schema document, <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/registry-changes-extension.schema.json>. Every definition of the extension has the prefix `ext.registryChanges.`. It refers to the Component Objects of the message components extension by their names, `#/$defs/ext.messages.<definition>` [@!RPP-MESSAGES].

## Extension Mapping {#extension-mapping}

The extension adds no member to a base definition, so its Extension Mapper is empty:

```json
{
  "rpp:extends": {}
}
```

The schema document states the Name, Identifier, and Version of (#overview) in the property `rpp:extension`. The New objects are message types, and `objects` names only Data Objects:

```json
{
  "rpp:extension": {
    "name": "RPP Registry Change Messages",
    "id": "io.github.pawel-kow.rpp.registry-changes",
    "version": "0.1.0",
    "objects": []
  }
}
```

## Message Type Mapping {#message-type-mapping}

The schema document maps the Identifier of each message type of the extension to its definition in the member `rpp:messages`, as the message components extension defines for a dependent extension [@!RPP-MESSAGES]:

```json
{
  "rpp:messages": {
    "domainUpdateMessage": "#/$defs/ext.registryChanges.domainUpdateMessage.read",
    "contactUpdateMessage": "#/$defs/ext.registryChanges.contactUpdateMessage.read",
    "domainDeletionMessage": "#/$defs/ext.registryChanges.domainDeletionMessage.read",
    "contactDeletionMessage": "#/$defs/ext.registryChanges.contactDeletionMessage.read"
  }
}
```

## Message Types {#json-message-types}

Each message type repeats the data elements that it inherits as top-level properties [@!I-D.ietf-rpp-json, section 6.2.16]. A message type that extends the Bulk Base Message Object does not declare `objectType` and `objectId`. The value of `objectType` of a referenced object is constrained with `allOf`.

Domain Update Message Object:

<!-- definition ext.registryChanges.domainUpdateMessage.read -->
```json
{
  "$defs": {
    "ext.registryChanges.domainUpdateMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainUpdateMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.messages.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Contact Update Message Object:

<!-- definition ext.registryChanges.contactUpdateMessage.read -->
```json
{
  "$defs": {
    "ext.registryChanges.contactUpdateMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "contactUpdateMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "contact", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.messages.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Domain Deletion Message Object:

<!-- definition ext.registryChanges.domainDeletionMessage.read -->
```json
{
  "$defs": {
    "ext.registryChanges.domainDeletionMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainDeletionMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.messages.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Contact Deletion Message Object:

<!-- definition ext.registryChanges.contactDeletionMessage.read -->
```json
{
  "$defs": {
    "ext.registryChanges.contactDeletionMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "contactDeletionMessage", "readOnly": true },
        "objects": { "type": "array", "minItems": 1, "items": { "allOf": [{ "$ref": "#/$defs/ext.messages.objectReference.read" }, { "properties": { "objectType": { "const": "contact" } } }] }, "readOnly": true }
      },
      "required": ["@type", "objects"]
    }
  }
}
```

# Examples {#examples}

This section is non-normative.

## Messages {#examples-messages}

Example message read response with a Domain Update Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "5b7c9d1e-2f3a-4b5c-8d6e-7f8091a2b3c4",
    "creationDate": "2026-11-21T08:00:00Z",
    "status": "queued",
    "data": {
        "@type": "domainUpdateMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "notices": [
            {
                "@type": "registryNotice",
                "code": "3000",
                "text": "The domain name was changed by the registry",
                "arguments": [ "Reference: 4712" ]
            }
        ]
    }
}
```

Example message read response with a Contact Update Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "6c8d0e2f-3a4b-4c5d-9e7f-8091a2b3c4d5",
    "creationDate": "2026-11-21T08:05:00Z",
    "status": "queued",
    "data": {
        "@type": "contactUpdateMessage",
        "objectType": "contact",
        "objectId": "sh8013",
        "notices": [
            { "@type": "registryNotice", "code": "3001", "text": "The contact was changed by the registry" }
        ]
    }
}
```

Example message read response with a Domain Deletion Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "7d9e1f3a-4b5c-4d6e-8f80-91a2b3c4d5e6",
    "creationDate": "2026-11-22T00:00:00Z",
    "status": "queued",
    "data": {
        "@type": "domainDeletionMessage",
        "objectType": "domainName",
        "objectId": "bar.example",
        "notices": [
            { "@type": "registryNotice", "code": "3002", "text": "The domain name was deleted by the registry" }
        ]
    }
}
```

Example message read response with a Contact Deletion Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "7f3e9b12-4c5d-4e6f-8a9b-0c1d2e3f4a55",
    "creationDate": "2026-11-12T03:00:00Z",
    "status": "queued",
    "data": {
        "@type": "contactDeletionMessage",
        "objects": [
            { "@type": "objectReference", "objectType": "contact", "objectId": "sh8013" },
            { "@type": "objectReference", "objectType": "contact", "objectId": "sh8014" }
        ]
    }
}
```

## Invalid Examples {#examples-invalid}

Example message read response with a Contact Deletion Message Object that refers to a domain name:

<!-- example invalid message.read -->
```json
{
    "@type": "message",
    "id": "7f3e9b12-4c5d-4e6f-8a9b-0c1d2e3f4a56",
    "creationDate": "2026-11-12T03:00:00Z",
    "status": "queued",
    "data": {
        "@type": "contactDeletionMessage",
        "objects": [
            { "@type": "objectReference", "objectType": "domainName", "objectId": "foo.example" }
        ]
    }
}
```

Example message read response with a Contact Deletion Message Object that names one object with the members of the Base Message Object:

<!-- example invalid message.read -->
```json
{
    "@type": "message",
    "id": "7f3e9b12-4c5d-4e6f-8a9b-0c1d2e3f4a57",
    "creationDate": "2026-11-12T03:00:00Z",
    "status": "queued",
    "data": {
        "@type": "contactDeletionMessage",
        "objectType": "contact",
        "objectId": "sh8013",
        "objects": [
            { "@type": "objectReference", "objectType": "contact", "objectId": "sh8013" }
        ]
    }
}
```

Example message read response with a Domain Update Message Object without notices:

<!-- example invalid message.read -->
```json
{
    "@type": "message",
    "id": "5b7c9d1e-2f3a-4b5c-8d6e-7f8091a2b3c5",
    "creationDate": "2026-11-21T08:00:00Z",
    "status": "queued",
    "data": {
        "@type": "domainUpdateMessage",
        "objectType": "domainName",
        "objectId": "foo.example"
    }
}
```

# IANA Considerations {#iana}

This document has no IANA actions. The extension is a private extension [@!I-D.wullink-rpp-extension-guidelines, section 10], and its Identifier is formed by reverse domain name notation [@!I-D.wullink-rpp-extension-guidelines, section 7] under the domain `pawel-kow.github.io`.

For a standardised version of the extension, the following entries would be registered in the RPP Data Object Registry [@!I-D.ietf-rpp-data-objects].

Object: domainUpdateMessage

Object Name: Domain Update Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that the server changed the data of a domain name.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| notices | Notices | 1+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

Object: contactUpdateMessage

Object Name: Contact Update Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that the server changed the data of a contact.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| notices | Notices | 1+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

Object: domainDeletionMessage

Object Name: Domain Deletion Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that the server deleted a domain name.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| notices | Notices | 1+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

Object: contactDeletionMessage

Object Name: Contact Deletion Message Object

Object Type: Component

Extends: bulkBaseMessage

Description: Notification for the sponsoring client that the server deleted contacts that no domain name referred to.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| objects | Objects | 1+ | read-only | Object Reference Object | The deleted contacts. |

# Security Considerations {#security}

The extension inherits the authentication and authorisation services of the base specifications [@!I-D.wullink-rpp-extension-guidelines, section 12]. A server queues a message of the extension for the sponsoring client of the object only. A message carries no data of the changed object: a client that reads the object after a Domain Update or Contact Update Message Object is authorised as for any read of it.

# Privacy Considerations {#privacy}

The message types name contacts by their Handle ID and carry no contact information, such as the name or the postal address of a person. A client learns the changed data of a contact only by a read of the contact, with the disclosure rules of the Contact Data Object [@!I-D.ietf-rpp-data-objects, section 12]. The privacy considerations of the Registry Notice Object [@!RPP-MESSAGES] apply to the notices.

# Internationalisation Considerations {#i18n}

None.

{removeInRFC="true"}
{toc="exclude"}
# Changes History

{toc="exclude"}
{numbered="false"}
## 0.1.0

* initial version: the domain update, contact update, domain deletion and contact deletion message types, moved from the extension de.denic.rpp.rri 0.3.0 #261

{backmatter}

<reference anchor="RPP-MESSAGES" target="https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/docs/extensions/messages-extension.md">
  <front>
    <title>Message Components Extension for the RESTful Provisioning Protocol (RPP)</title>
    <author initials="P." surname="Kowalik" fullname="Pawel Kowalik"/>
    <date year="2026" month="November"/>
  </front>
</reference>
