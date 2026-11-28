%%%
title = "Domain Lock Messages Extension for the RESTful Provisioning Protocol (RPP)"
abbrev = "RPP Domain Lock Messages"
area = "Applications and Real-Time"
workgroup = "Network Working Group"
submissiontype = "IETF"
keyword = ["RPP", "provisioning", "registry", "extension", "messages", "lock"]
TocDepth = 4
date = 2026-11-28

[seriesInfo]
name = "Internet-Draft"
value = "draft-kowalik-rpp-domain-lock-messages-00"
stream = "IETF"
status = "informational"

[[author]]
initials="P."
surname="Kowalik"
fullname="Pawel Kowalik"
organization = "DENIC"

%%%

.# Abstract

This document defines a private extension of the RESTful Provisioning Protocol (RPP) with two message types, which notify the sponsoring client that the server locked a domain name against changes through the protocol, and that it removed the lock.

{mainmatter}

# Introduction {#introduction}

This section states the purpose of the extension, the specifications it builds upon, and the reasons for the extension points it uses.

The RESTful Provisioning Protocol (RPP) is defined by [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], and [@!I-D.ietf-rpp-json]. This document follows the extension specification format of [@!I-D.wullink-rpp-extension-guidelines, section 9]. It builds on the message components extension [@!RPP-MESSAGES], whose Registry Notice Object its message types use, and whose rules for the message types of a dependent extension apply to them.

A registry can lock a domain name against changes through the protocol, for example at the request of its registrant or by a decision of the registry, and later remove the lock. The registry informs the sponsoring client of both events, because the client can no longer change the domain name while it is locked. The base specifications define no message type for them [@!I-D.ietf-rpp-data-objects, section 9.19], and a Service Notice Message Object carries no structured data. This extension defines a message type for each event.

How a registry locks a domain name, and which status values a locked domain name has, is out of scope of this extension.

## Conventions and Terminology {#terminology}

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [@!RFC2119] [@!RFC8174] when, and only when, they appear in all capitals, as shown here.

Terms of the RPP data model, such as Data Object, Component Object, data element, cardinality, mutability, and message type, are used as defined in [@!I-D.ietf-rpp-data-objects]. The terms Extension Mapper (`rpp:extends`) and Effective Schema are used as defined in [@!I-D.ietf-rpp-json]. The message components extension is the extension `io.github.pawel-kow.rpp.messages` [@!RPP-MESSAGES], and the term dependent extension is used as defined there.

## Choice of Extension Points {#choice}

This section is non-normative.

The events are defined as message types that extend the Base Message Object [@!I-D.ietf-rpp-data-objects, section 9.19.1], as [@!I-D.ietf-rpp-data-objects, section 5] recommends for extensions. Each message is about one domain name, which the Object Type and the Object Identifier of the Base Message Object name. The notices of the registry about the event are Registry Notice Objects of the message components extension, so that a client reads them in the same form as in the message types of other extensions.

The extension is a dependent extension of the message components extension, which states how its message types become part of the Message Data Object and of the `data` property of its JSON representation.

# Extension Overview {#overview}

This section identifies the extension.

| Field                | Value |
| -------------------- | ----- |
| Name                 | RPP Domain Lock Messages |
| Identifier           | `io.github.pawel-kow.rpp.domain-lock` |
| Version              | 0.1.0 |
| RPP version          | [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], [@!I-D.ietf-rpp-json] |
| Schema `$id`         | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/domain-lock-extension.schema.json> |
| Changed base objects | `message` |
| New objects          | `domainLockMessage`, `domainUnlockMessage` |
Table: Extension Overview

A server that offers a preset with this extension MUST offer the message components extension `io.github.pawel-kow.rpp.messages` [@!RPP-MESSAGES] in the same preset, in version 0.1.0 or a later version with the same major version. The definitions of the extension refer to its Registry Notice Object.

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

The message types of (#message-types) are message types of a dependent extension. The Data of a message, the values of the Message Type parameter (`type`) of the Query operation, and the Read and Delete operations follow the rules of the message components extension for them [@!RPP-MESSAGES]. A server that supports the extension sends the notification of a lock or of the removal of a lock of a domain name as a message of the type of (#message-types) that describes it.

# New Data Objects {#new-data-objects}

This section defines the message types of the extension. A server uses each of them as the Data (`data`) of a Message Data Object [@!I-D.ietf-rpp-data-objects, section 15]. In both, the Object Type (`objectType`) and the Object Identifier (`objectId`) of the Base Message Object are required.

| Identifier | Extends | Objects |
| ---------- | ------- | ------- |
| `domainLockMessage` | `baseMessage` | a domain name |
| `domainUnlockMessage` | `baseMessage` | a domain name |
Table: Message Types of the Extension

## Message Types {#message-types}

### Domain Lock Message Object {#domain-lock-message}

* Name: Domain Lock Message Object
* Identifier: domainLockMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that the server locked a domain name against changes through the protocol.
* Data Elements:
  * Notices
    * Identifier: notices
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Registry Notice Object [@!RPP-MESSAGES]
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

### Domain Unlock Message Object {#domain-unlock-message}

* Name: Domain Unlock Message Object
* Identifier: domainUnlockMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that the server removed the lock of a domain name.
* Data Elements:
  * Notices
    * Identifier: notices
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Registry Notice Object [@!RPP-MESSAGES]
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

# Updated Process Objects {#updated-process-objects}

None.

# New Process Objects {#new-process-objects}

None.

# Endpoints {#endpoints}

None. A client retrieves the messages at the messages endpoint [@!I-D.ietf-rpp-core, section 16.10] and selects them with the `type` query parameter. This section is non-normative.

Example request for the oldest message about a lock or the removal of a lock:

```http
GET /messages?type=domainLockMessage&type=domainUnlockMessage HTTP/1.1
Host: rpp.example
Authorization: Bearer <token>
Accept: application/rpp+json
RPP-Cltrid: ABC-12360
```

# JSON Schema {#json-schema}

This section defines the JSON representation of the message types, following the rules of [@!I-D.ietf-rpp-json, section 4] and the Extension Framework of [@!I-D.ietf-rpp-json, section 7].

The extension defines one JSON Schema document, <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/domain-lock-extension.schema.json>. Every definition of the extension has the prefix `ext.domainLock.`. It refers to the Registry Notice Object of the message components extension by its name, `#/$defs/ext.messages.registryNotice.read` [@!RPP-MESSAGES].

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
    "name": "RPP Domain Lock Messages",
    "id": "io.github.pawel-kow.rpp.domain-lock",
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
    "domainLockMessage": "#/$defs/ext.domainLock.domainLockMessage.read",
    "domainUnlockMessage": "#/$defs/ext.domainLock.domainUnlockMessage.read"
  }
}
```

## Message Types {#json-message-types}

Each message type repeats the data elements that it inherits as top-level properties [@!I-D.ietf-rpp-json, section 6.2.16].

Domain Lock Message Object:

<!-- definition ext.domainLock.domainLockMessage.read -->
```json
{
  "$defs": {
    "ext.domainLock.domainLockMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainLockMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.messages.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Domain Unlock Message Object:

<!-- definition ext.domainLock.domainUnlockMessage.read -->
```json
{
  "$defs": {
    "ext.domainLock.domainUnlockMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainUnlockMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.messages.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

# Examples {#examples}

This section is non-normative.

## Messages {#examples-messages}

Example message read response with a Domain Lock Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "3a1f0c2e-7b4d-4e59-9c61-2d8e5f7a9b10",
    "creationDate": "2026-11-20T09:15:00Z",
    "status": "queued",
    "data": {
        "@type": "domainLockMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "notices": [
            {
                "@type": "registryNotice",
                "code": "2000",
                "text": "The domain name was locked by the registry",
                "arguments": [ "Reference: 4711" ]
            }
        ]
    }
}
```

Example message read response with a Domain Unlock Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "9e2b4d61-0a3c-4f7e-8b15-6c9d1e2f3a40",
    "creationDate": "2026-11-27T10:00:00Z",
    "status": "queued",
    "data": {
        "@type": "domainUnlockMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "notices": [
            {
                "@type": "registryNotice",
                "code": "2001",
                "text": "The lock of the domain name was removed by the registry"
            }
        ]
    }
}
```

## Invalid Examples {#examples-invalid}

Example message read response with a Domain Lock Message Object without notices:

<!-- example invalid message.read -->
```json
{
    "@type": "message",
    "id": "3a1f0c2e-7b4d-4e59-9c61-2d8e5f7a9b11",
    "creationDate": "2026-11-20T09:15:00Z",
    "status": "queued",
    "data": {
        "@type": "domainLockMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "notices": []
    }
}
```

Example message read response with a Domain Unlock Message Object about a contact:

<!-- example invalid message.read -->
```json
{
    "@type": "message",
    "id": "9e2b4d61-0a3c-4f7e-8b15-6c9d1e2f3a41",
    "creationDate": "2026-11-27T10:00:00Z",
    "status": "queued",
    "data": {
        "@type": "domainUnlockMessage",
        "objectType": "contact",
        "objectId": "sh8013",
        "notices": [
            { "@type": "registryNotice", "code": "2001", "text": "The lock was removed" }
        ]
    }
}
```

# IANA Considerations {#iana}

This document has no IANA actions. The extension is a private extension [@!I-D.wullink-rpp-extension-guidelines, section 10], and its Identifier is formed by reverse domain name notation [@!I-D.wullink-rpp-extension-guidelines, section 7] under the domain `pawel-kow.github.io`.

For a standardised version of the extension, the following entries would be registered in the RPP Data Object Registry [@!I-D.ietf-rpp-data-objects].

Object: domainLockMessage

Object Name: Domain Lock Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that the server locked a domain name against changes through the protocol.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| notices | Notices | 1+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

Object: domainUnlockMessage

Object Name: Domain Unlock Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that the server removed the lock of a domain name.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| notices | Notices | 1+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

# Security Considerations {#security}

The extension inherits the authentication and authorisation services of the base specifications [@!I-D.wullink-rpp-extension-guidelines, section 12]. A server queues a message of the extension for the sponsoring client of the domain name only. The extension defines no operation to lock a domain name or to remove a lock: a message informs the client of an event, and a client that acts on it, for example by an update of the domain name, is authorised as for that operation.

# Privacy Considerations {#privacy}

The message types name a domain name and carry no contact information. The privacy considerations of the Registry Notice Object [@!RPP-MESSAGES] apply to their notices.

# Internationalisation Considerations {#i18n}

None.

{removeInRFC="true"}
{toc="exclude"}
# Changes History

{toc="exclude"}
{numbered="false"}
## 0.1.0

* initial version: the domain lock and domain unlock message types, moved from the extension de.denic.rpp.rri 0.3.0 #261

{backmatter}

<reference anchor="RPP-MESSAGES" target="https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/docs/extensions/messages-extension.md">
  <front>
    <title>Message Components Extension for the RESTful Provisioning Protocol (RPP)</title>
    <author initials="P." surname="Kowalik" fullname="Pawel Kowalik"/>
    <date year="2026" month="November"/>
  </front>
</reference>
