%%%
title = "Authorisation Information Extension for the RESTful Provisioning Protocol (RPP)"
abbrev = "RPP Authorisation Information"
area = "Applications and Real-Time"
workgroup = "Network Working Group"
submissiontype = "IETF"
keyword = ["RPP", "provisioning", "registry", "extension", "authorisation information"]
TocDepth = 4
date = 2026-11-28

[seriesInfo]
name = "Internet-Draft"
value = "draft-kowalik-rpp-authinfo-00"
stream = "IETF"
status = "informational"

[[author]]
initials="P."
surname="Kowalik"
fullname="Pawel Kowalik"
organization = "DENIC"

%%%

.# Abstract

This document defines a private extension of the RESTful Provisioning Protocol (RPP) with two Process Objects of the Domain Name Data Object. With the first, the sponsoring client sets the authorisation information of a domain name with an expiry date, reads the expiry date, and removes the authorisation information. With the second, a client asks the server to generate authorisation information for a domain name and to deliver it to the registrants of the domain name. The extension also defines three message types, which notify the sponsoring client that the authorisation information of a domain name expired, that the server issued authorisation information to the registrants, and that the server withdrew issued authorisation information.

{mainmatter}

# Introduction {#introduction}

This section states the purpose of the extension, the specifications it builds upon, and the reasons for the extension points it uses.

The RESTful Provisioning Protocol (RPP) is defined by [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], and [@!I-D.ietf-rpp-json]. This document follows the extension specification format of [@!I-D.wullink-rpp-extension-guidelines, section 9]. It builds on the message components extension [@!RPP-MESSAGES], whose Registry Notice Object one of its message types uses, and whose rules for the message types of a dependent extension apply to its message types.

A server can limit the lifetime of the authorisation information of a domain name and let the sponsoring client choose the expiry date within that limit. The Authorisation Information Object [@!I-D.ietf-rpp-data-objects, section 9.12] consists of a method and a value and has no expiry date, so that a client can neither set nor read one.

A server can also generate authorisation information for a domain name at the request of a client and deliver it to the registrants of the domain name by a channel outside the protocol. A registrant then passes it on to a client of its choice, which uses it, for example, to request a transfer of the domain name without the help of the sponsoring client. The base specifications define no operation that asks the server to issue authorisation information.

The server informs the sponsoring client when the authorisation information of a domain name expires, when it issued authorisation information to the registrants, and when it withdrew issued authorisation information. The base specifications define no message type for these events [@!I-D.ietf-rpp-data-objects, section 9.19], and a Service Notice Message Object carries no structured data.

This extension defines a Process Object for each of the two operations and a message type for each of the three events. Which lifetime a server allows, in which status of a domain name it issues authorisation information, and by which channel it delivers issued authorisation information are matters of server policy and out of scope of this extension.

## Conventions and Terminology {#terminology}

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [@!RFC2119] [@!RFC8174] when, and only when, they appear in all capitals, as shown here.

Terms of the RPP data model, such as Data Object, Component Object, Process Object, data element, cardinality, mutability, Identifier, Unique Identifier, Reference, Owner Data Object, This Object, and message type, are used as defined in [@!I-D.ietf-rpp-data-objects]. The terms Extension Mapper (`rpp:extends`) and Effective Schema are used as defined in [@!I-D.ietf-rpp-json]. The message components extension is the extension `io.github.pawel-kow.rpp.messages` [@!RPP-MESSAGES], and the term dependent extension is used as defined there.

The following term is used in this document:

Issued authorisation information
: Authorisation information that the server generated for a domain name at the request of a client and delivered to the registrants of the domain name (#auth-info-issue-process).

## Choice of Extension Points {#choice}

This section is non-normative.

The operations on authorisation information are defined as new Process Objects of the Domain Name Data Object, the Authorisation Information Process Object (#auth-info-process) and the Authorisation Information Issue Process Object (#auth-info-issue-process). An expiry date is not a data element of the Authorisation Information Object, which is immutable and consists of a method and a value. Issuing authorisation information to the registrants is an action on the domain name with no data element of the domain name as its input, for which [@!I-D.ietf-rpp-core, section 16.1.4] asks for a Process Object. The Authorisation Information (`authInfo`) data element of the Domain Name Data Object is not changed.

The events are defined as message types that extend the Base Message Object [@!I-D.ietf-rpp-data-objects, section 9.19.1], as [@!I-D.ietf-rpp-data-objects, section 5] recommends for extensions. Each message is about one domain name, which the Object Type and the Object Identifier of the Base Message Object name. The notices of the registry about the withdrawal of issued authorisation information are Registry Notice Objects of the message components extension, so that a client reads them in the same form as in the message types of other extensions.

The extension is a dependent extension of the message components extension, which states how its message types become part of the Message Data Object and of the `data` property of its JSON representation.

# Extension Overview {#overview}

This section identifies the extension.

| Field                | Value |
| -------------------- | ----- |
| Name                 | RPP Authorisation Information |
| Identifier           | `io.github.pawel-kow.rpp.authinfo` |
| Version              | 0.1.0 |
| RPP version          | [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], [@!I-D.ietf-rpp-json] |
| Schema `$id`         | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/authinfo-extension.schema.json> |
| Changed base objects | `domainName`, `processes`, `message` |
| New objects          | `authInfoProcess`, `authInfoIssueProcess`, `authInfoExpiryMessage`, `authInfoIssueMessage`, `authInfoWithdrawalMessage` |
Table: Extension Overview

A server that offers a preset with this extension MUST offer the message components extension `io.github.pawel-kow.rpp.messages` [@!RPP-MESSAGES] in the same preset, in version 0.1.0 or a later version with the same major version. The Authorisation Information Withdrawal Message Object (#auth-info-withdrawal-message) refers to its Registry Notice Object.

# External Data Types {#external-data-types}

None.

# Result Codes {#result-codes}

None. The extension uses the result codes of [@!I-D.ietf-rpp-core, section 18].

# Problem Details {#problem-details}

None.

# HTTP Headers {#http-headers}

None. A client conveys issued authorisation information as the Object Authorisation of a request in the `RPP-Authorization` header field [@!I-D.ietf-rpp-core, section 6.1], as any other authorisation information.

# Discovery Document {#discovery}

A server that supports the extension lists it in the `extensions` of its Discovery document with the values of (#overview), in each preset that contains it. It lists no object in `objects`.

# Updated Data Objects {#updated-data-objects}

This section states the additions of the extension to the Domain Name Data Object, the Processes Object, and the Message Data Object.

## Domain Name Data Object {#domain-name}

* Identifier: domainName

### Data Elements {#domain-name-data-elements}

None. The extension does not change the Authorisation Information (`authInfo`) data element. Its relation to the Authorisation Information Process Object is stated in (#auth-info-process).

### Operations {#domain-name-operations}

None.

### Processes {#domain-name-processes}

The Domain Name Data Object supports, in addition to the Process Objects of [@!I-D.ietf-rpp-data-objects, section 11.4], the Process Objects of (#new-process-objects).

## Processes Object {#processes}

* Identifier: processes

### Data Elements {#processes-data-elements}

The following data elements are added to the Processes Object [@!I-D.ietf-rpp-data-objects, section 9.16], as it requires for the Process Objects that an extension defines.

* Authorisation Information Processes
  * Identifier: authInfoProcess
  * Cardinality: 0+
  * Mutability: read-only
  * Data Type: Aggregation[Authorisation Information Process Object]
  * Direct Access: true
  * Description: The authorisation information processes initiated on the owning domain name.
  * Constraints: (None)
* Authorisation Information Issue Processes
  * Identifier: authInfoIssueProcess
  * Cardinality: 0+
  * Mutability: read-only
  * Data Type: Aggregation[Authorisation Information Issue Process Object]
  * Direct Access: true
  * Description: The authorisation information issue processes initiated on the owning domain name.
  * Constraints: (None)

These data elements appear only in the Processes Object of a Domain Name Data Object.

## Message Data Object {#message}

* Identifier: message

The message types of (#message-types) are message types of a dependent extension. The Data of a message, the values of the Message Type parameter (`type`) of the Query operation, and the Read and Delete operations follow the rules of the message components extension for them [@!RPP-MESSAGES]. A server that supports the extension sends the notification of an event that a message type of (#message-types) describes as a message of that type.

# New Data Objects {#new-data-objects}

This section defines the message types of the extension. A server uses each of them as the Data (`data`) of a Message Data Object [@!I-D.ietf-rpp-data-objects, section 15]. In each of them, the Object Type (`objectType`) and the Object Identifier (`objectId`) of the Base Message Object are required.

| Identifier | Extends | Objects |
| ---------- | ------- | ------- |
| `authInfoExpiryMessage` | `baseMessage` | a domain name |
| `authInfoIssueMessage` | `baseMessage` | a domain name |
| `authInfoWithdrawalMessage` | `baseMessage` | a domain name |
Table: Message Types of the Extension

## Message Types {#message-types}

### Authorisation Information Expiry Message Object {#auth-info-expiry-message}

* Name: Authorisation Information Expiry Message Object
* Identifier: authInfoExpiryMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client of the expiry of the authorisation information of a domain name.
* Data Elements:
  * Expiry Date
    * Identifier: expiryDate
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: Timestamp
    * Description: The date and time of the expiry of the authorisation information.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

### Authorisation Information Issue Message Object {#auth-info-issue-message}

* Name: Authorisation Information Issue Message Object
* Identifier: authInfoIssueMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that the server issued authorisation information for a domain name to its registrants, at the request of a client.
* Data Elements: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

### Authorisation Information Withdrawal Message Object {#auth-info-withdrawal-message}

* Name: Authorisation Information Withdrawal Message Object
* Identifier: authInfoWithdrawalMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that the server deleted the authorisation information that it had issued to the registrants of a domain name, for example because it could not deliver it.
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

This section defines the Process Objects that the extension introduces. Their Owner Data Object is the Domain Name Data Object.

## Authorisation Information Process Object {#auth-info-process}

* Name: Authorisation Information Process Object
* Identifier: authInfoProcess
* Unique Identifier: processId
* Extends: Base Process Object
* Description: Represents the authorisation information that the sponsoring client sets for a domain name, with its expiry date. Creating this object sets the authorisation information, reading it returns its expiry date, and deleting it removes the authorisation information.

### Data Elements {#auth-info-process-data-elements}

* Authorisation Information
  * Identifier: authInfo
  * Cardinality: 1
  * Mutability: create-only
  * Data Type: Authorisation Information Object
  * Description: The authorisation information that the sponsoring client sets for the domain name.
  * Constraints:
    * The Method MUST be a method that the server supports for the Authorisation Information (`authInfo`) of a domain name.
    * The value MUST satisfy the policy of the server for the authorisation information of a domain name, which is the policy for the Authorisation Information (`authInfo`) data element of the Domain Name Data Object.
    * The server MUST NOT return the value in any operation.
* Expiry Date
  * Identifier: expiryDate
  * Cardinality: 0-1
  * Mutability: create-only
  * Data Type: Date
  * Description: The last day on which the authorisation information is valid.
  * Constraints: (None)

The authorisation information of this Process Object is the Authorisation Information (`authInfo`) of the domain name [@!I-D.ietf-rpp-data-objects, section 11.2]. A domain name has at most one. An update of the `authInfo` of the domain name replaces it, with an expiry date of the server's policy, and a removal of the `authInfo` removes it. The Expiry Date is a day, and it ends at the end of that day in UTC, unless the server's policy states another time zone.

When the authorisation information expires, the server informs the sponsoring client with a message whose Data is an Authorisation Information Expiry Message Object (#auth-info-expiry-message).

### Operations {#auth-info-process-operations}

#### Create {#auth-info-process-create}

* Identifier: create

The Create operation sets the authorisation information of a domain name.

* Input:
  * Reference: Owner Data Object
  * Object: Authorisation Information Process Object
* Output:
  * Object: Authorisation Information Process Object
* Authorisation:
  * Only the sponsoring client is authorised to perform this operation.

When the Create operation has no Expiry Date, the server sets the expiry date by its policy. The server MUST reject a Create whose Authorisation Information has a method that it does not support, with a result code of [@!I-D.ietf-rpp-core, section 18]. The server MUST reject a Create for a domain name that has authorisation information, and a Create whose Expiry Date its policy does not allow. The output contains the Expiry Date that applies, when the server knows it.

#### Read {#auth-info-process-read}

* Identifier: read

The Read operation returns the expiry date of the authorisation information of a domain name.

* Input:
  * Reference: This Object
* Output:
  * Object: Authorisation Information Process Object
* Authorisation:
  * Only the sponsoring client is authorised to perform this operation.

The output contains the Expiry Date and not the Authorisation Information. The server MUST respond to a Read for a domain name without authorisation information as for a Process Object that does not exist.

#### Delete {#auth-info-process-delete}

* Identifier: delete

The Delete operation removes the authorisation information of a domain name.

* Input:
  * Reference: This Object
* Authorisation:
  * Only the sponsoring client is authorised to perform this operation.

The server MUST respond to a Delete for a domain name without authorisation information as for a Process Object that does not exist.

The Update operation is not supported.

## Authorisation Information Issue Process Object {#auth-info-issue-process}

* Name: Authorisation Information Issue Process Object
* Identifier: authInfoIssueProcess
* Unique Identifier: processId
* Extends: Base Process Object
* Description: Represents a request of a client that the server generate authorisation information for a domain name and deliver it to the registrants of the domain name, by a channel outside the protocol.
* Data Elements: (None)

### Operations {#auth-info-issue-process-operations}

#### Create {#auth-info-issue-process-create}

* Identifier: create

The Create operation asks the server to issue authorisation information for a domain name.

* Input:
  * Reference: Owner Data Object
  * Object: Authorisation Information Issue Process Object
* Output:
  * Object: Authorisation Information Issue Process Object
* Authorisation:
  * Any authenticated client is authorised to perform this operation.

The server generates the authorisation information and delivers it to the registrants. It MUST NOT return the authorisation information to any client. The server informs the sponsoring client with a message whose Data is an Authorisation Information Issue Message Object (#auth-info-issue-message). A client uses the authorisation information that a registrant passes on to it as the Object Authorisation of a transfer request or a read of the domain name [@!I-D.ietf-rpp-core, section 6.1].

Issued authorisation information is not the Authorisation Information (`authInfo`) of the domain name, and the Authorisation Information Process Object does not affect it. It is valid for a period of the server's policy. The server MUST reject a Create that its policy does not allow, such as a Create for a domain name for which issued authorisation information is valid, or for a domain name in a status in which its policy allows no issue.

When the server cannot deliver issued authorisation information, it deletes it and informs the sponsoring client with a message whose Data is an Authorisation Information Withdrawal Message Object (#auth-info-withdrawal-message).

The Read, Update, and Delete operations are not supported.

# Endpoints {#endpoints}

This section lists the endpoints that result from the new Process Objects, derived by the rules of [@!I-D.ietf-rpp-core, section 16.1]. The `plural()` function applied to the Identifiers `authInfoProcess` and `authInfoIssueProcess` gives the path segments `authInfoProcesses` and `authInfoIssueProcesses`. This section is non-normative.

| Operation                                      | HTTP Method | URL path                                                  |
| ---------------------------------------------- | ----------- | --------------------------------------------------------- |
| Authorisation Information: create              | POST        | /domainNames/{id}/processes/authInfoProcesses             |
| Authorisation Information: read                | GET         | /domainNames/{id}/processes/authInfoProcesses/latest      |
| Authorisation Information: delete              | DELETE      | /domainNames/{id}/processes/authInfoProcesses/latest      |
| Authorisation Information Issue: create        | POST        | /domainNames/{id}/processes/authInfoIssueProcesses        |
Table: Endpoints of the Process Objects

A server that assigns no Process ID exposes no process resource. It responds to a Create of the Authorisation Information Process Object or the Authorisation Information Issue Process Object with HTTP status code 200 (OK) and without a `Location` header field [@!I-D.ietf-rpp-core, section 16.1.4], and serves the Read and Delete of an Authorisation Information Process Object at `latest` only.

The message types of the extension add no endpoints: a client retrieves them at the messages endpoint [@!I-D.ietf-rpp-core, section 16.10] and selects them with the `type` query parameter.

Example Authorisation Information create request:

```http
POST /domainNames/foo.example/processes/authInfoProcesses HTTP/1.1
Host: rpp.example
Authorization: Bearer <token>
Accept: application/rpp+json
Content-Type: application/rpp+json
RPP-Cltrid: ABC-12348
Content-Length: 132
```

Example Authorisation Information create response:

```http
HTTP/1.1 200 OK
Date: Sat, 14 Nov 2026 12:00:00 GMT
Content-Type: application/rpp+json
RPP-Svtrid: XYZ-12348
RPP-Cltrid: ABC-12348
RPP-Code: 01000
```

Example Authorisation Information Issue create request:

```http
POST /domainNames/foo.example/processes/authInfoIssueProcesses HTTP/1.1
Host: rpp.example
Authorization: Bearer <token>
Accept: application/rpp+json
Content-Type: application/rpp+json
RPP-Cltrid: ABC-12349
Content-Length: 35
```

Example request for the oldest message about authorisation information issued to the registrants:

```http
GET /messages?type=authInfoIssueMessage&type=authInfoWithdrawalMessage HTTP/1.1
Host: rpp.example
Authorization: Bearer <token>
Accept: application/rpp+json
RPP-Cltrid: ABC-12352
```

# JSON Schema {#json-schema}

This section defines the JSON representation of the new and updated objects, following the rules of [@!I-D.ietf-rpp-json, section 4] and the Extension Framework of [@!I-D.ietf-rpp-json, section 7].

The extension defines one JSON Schema document, <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/authinfo-extension.schema.json>. Every definition of the extension has the prefix `ext.authinfo.`. It refers to the Registry Notice Object of the message components extension by its name, `#/$defs/ext.messages.registryNotice.read` [@!RPP-MESSAGES].

## Extension Mapping {#extension-mapping}

The Extension Mapper maps the base definition of the Processes Object to the definition of the extension:

```json
{
  "rpp:extends": {
    "#/$defs/processes.read": "#/$defs/ext.authinfo.processes.read"
  }
}
```

The key of the Extension Mapper and the `$ref` values refer to the base definitions by their keys in the shared `$defs` object [@!I-D.ietf-rpp-json, section 4.10], because the JSON Schema document of the base specifications has no `$id` yet.

The schema document states the Name, Identifier, and Version of (#overview) in the property `rpp:extension`. The New objects are Process Objects and message types, and `objects` names only Data Objects:

```json
{
  "rpp:extension": {
    "name": "RPP Authorisation Information",
    "id": "io.github.pawel-kow.rpp.authinfo",
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
    "authInfoExpiryMessage": "#/$defs/ext.authinfo.authInfoExpiryMessage.read",
    "authInfoIssueMessage": "#/$defs/ext.authinfo.authInfoIssueMessage.read",
    "authInfoWithdrawalMessage": "#/$defs/ext.authinfo.authInfoWithdrawalMessage.read"
  }
}
```

## Processes Object {#json-processes}

Read response schema:

<!-- definition ext.authinfo.processes.read -->
```json
{
  "$defs": {
    "ext.authinfo.processes.read": {
      "type": "object",
      "properties": {
        "authInfoProcess": {
          "type": "array",
          "items": { "$ref": "#/$defs/ext.authinfo.authInfoProcess.reference" },
          "readOnly": true
        },
        "authInfoIssueProcess": {
          "type": "array",
          "items": { "$ref": "#/$defs/ext.authinfo.authInfoIssueProcess.reference" },
          "readOnly": true
        }
      }
    }
  }
}
```

## Authorisation Information Process Object {#json-auth-info-process}

### Create

Create request schema:

<!-- definition ext.authinfo.authInfoProcess.create -->
```json
{
  "$defs": {
    "ext.authinfo.authInfoProcess.create": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoProcess" },
        "authInfo": { "$ref": "#/$defs/authInfo.create", "writeOnly": true },
        "expiryDate": { "type": "string", "format": "date", "writeOnly": true }
      },
      "required": ["@type", "authInfo"]
    }
  }
}
```

### Read

Read response schema, which is also the response schema of the Create operation:

<!-- definition ext.authinfo.authInfoProcess.read -->
```json
{
  "$defs": {
    "ext.authinfo.authInfoProcess.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoProcess", "readOnly": true },
        "processId": { "type": "string", "readOnly": true },
        "expiryDate": { "type": "string", "format": "date", "readOnly": true }
      },
      "required": ["@type"]
    }
  }
}
```

### Reference

<!-- definition ext.authinfo.authInfoProcess.reference -->
```json
{
  "$defs": {
    "ext.authinfo.authInfoProcess.reference": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoProcess" },
        "processId": { "type": "string", "readOnly": true }
      },
      "required": ["@type", "processId"]
    }
  }
}
```

## Authorisation Information Issue Process Object {#json-auth-info-issue-process}

### Create

Create request schema:

<!-- definition ext.authinfo.authInfoIssueProcess.create -->
```json
{
  "$defs": {
    "ext.authinfo.authInfoIssueProcess.create": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoIssueProcess" }
      },
      "required": ["@type"]
    }
  }
}
```

Response schema of the Create operation:

<!-- definition ext.authinfo.authInfoIssueProcess.read -->
```json
{
  "$defs": {
    "ext.authinfo.authInfoIssueProcess.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoIssueProcess", "readOnly": true },
        "processId": { "type": "string", "readOnly": true }
      },
      "required": ["@type"]
    }
  }
}
```

### Reference

<!-- definition ext.authinfo.authInfoIssueProcess.reference -->
```json
{
  "$defs": {
    "ext.authinfo.authInfoIssueProcess.reference": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoIssueProcess" },
        "processId": { "type": "string", "readOnly": true }
      },
      "required": ["@type", "processId"]
    }
  }
}
```

## Message Types {#json-message-types}

Each message type repeats the data elements that it inherits as top-level properties [@!I-D.ietf-rpp-json, section 6.2.16].

Authorisation Information Expiry Message Object:

<!-- definition ext.authinfo.authInfoExpiryMessage.read -->
```json
{
  "$defs": {
    "ext.authinfo.authInfoExpiryMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoExpiryMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "expiryDate": { "type": "string", "format": "date-time", "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "expiryDate"]
    }
  }
}
```

Authorisation Information Issue Message Object:

<!-- definition ext.authinfo.authInfoIssueMessage.read -->
```json
{
  "$defs": {
    "ext.authinfo.authInfoIssueMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoIssueMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId"]
    }
  }
}
```

Authorisation Information Withdrawal Message Object:

<!-- definition ext.authinfo.authInfoWithdrawalMessage.read -->
```json
{
  "$defs": {
    "ext.authinfo.authInfoWithdrawalMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoWithdrawalMessage", "readOnly": true },
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

## Authorisation Information {#examples-auth-info}

Example authorisation information create request with an expiry date:

<!-- example valid authInfoProcess.create -->
```json
{
    "@type": "authInfoProcess",
    "authInfo": { "@type": "authInfo", "method": "authinfo", "authdata": "Abc23456" },
    "expiryDate": "2026-12-01"
}
```

Example authorisation information create or read response:

<!-- example valid authInfoProcess.read -->
```json
{
    "@type": "authInfoProcess",
    "expiryDate": "2026-12-01"
}
```

## Authorisation Information Issue {#examples-auth-info-issue}

Example authorisation information issue create request:

<!-- example valid authInfoIssueProcess.create -->
```json
{
    "@type": "authInfoIssueProcess"
}
```

Example authorisation information issue create response:

<!-- example valid authInfoIssueProcess.read -->
```json
{
    "@type": "authInfoIssueProcess"
}
```

## Messages {#examples-messages}

Example message read response with an Authorisation Information Expiry Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "5c7e1a90-2b3d-4f68-a1c4-7d9e0f2a3b51",
    "creationDate": "2026-12-02T00:00:05Z",
    "status": "queued",
    "data": {
        "@type": "authInfoExpiryMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "expiryDate": "2026-12-02T00:00:00+01:00"
    }
}
```

Example message read response with an Authorisation Information Issue Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "8d2f3b41-6c5e-4a07-9b18-0e1f2a3c4d62",
    "creationDate": "2026-11-28T09:00:00Z",
    "status": "queued",
    "data": {
        "@type": "authInfoIssueMessage",
        "objectType": "domainName",
        "objectId": "foo.example"
    }
}
```

Example message read response with an Authorisation Information Withdrawal Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "1e4a5c72-8d9f-4b30-a2c6-3f4e5d6a7b83",
    "creationDate": "2026-12-05T14:30:00Z",
    "status": "queued",
    "data": {
        "@type": "authInfoWithdrawalMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "notices": [
            {
                "@type": "registryNotice",
                "code": "2003",
                "text": "The issued authorisation information could not be delivered and was deleted"
            }
        ]
    }
}
```

## Invalid Examples {#examples-invalid}

Example authorisation information create request without authorisation information:

<!-- example invalid authInfoProcess.create -->
```json
{
    "@type": "authInfoProcess",
    "expiryDate": "2026-12-01"
}
```

Example message read response with an Authorisation Information Expiry Message Object without the expiry date:

<!-- example invalid message.read -->
```json
{
    "@type": "message",
    "id": "5c7e1a90-2b3d-4f68-a1c4-7d9e0f2a3b52",
    "creationDate": "2026-12-02T00:00:05Z",
    "status": "queued",
    "data": {
        "@type": "authInfoExpiryMessage",
        "objectType": "domainName",
        "objectId": "foo.example"
    }
}
```

Example message read response with an Authorisation Information Withdrawal Message Object without notices:

<!-- example invalid message.read -->
```json
{
    "@type": "message",
    "id": "1e4a5c72-8d9f-4b30-a2c6-3f4e5d6a7b84",
    "creationDate": "2026-12-05T14:30:00Z",
    "status": "queued",
    "data": {
        "@type": "authInfoWithdrawalMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "notices": []
    }
}
```

# IANA Considerations {#iana}

This document has no IANA actions. The extension is a private extension [@!I-D.wullink-rpp-extension-guidelines, section 10], and its Identifier is formed by reverse domain name notation [@!I-D.wullink-rpp-extension-guidelines, section 7] under the domain `pawel-kow.github.io`.

For a standardised version of the extension, the following entries would be registered in the RPP Data Object Registry [@!I-D.ietf-rpp-data-objects].

Object: processes (additions)

Data Elements

| Element Identifier   | Element Name                              | Card. | Mutability | Data Type                                                   | Description                                                                         |
| -------------------- | ----------------------------------------- | ----- | ---------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| authInfoProcess      | Authorisation Information Processes       | 0+    | read-only  | Aggregation[Authorisation Information Process Object]       | The authorisation information processes initiated on the owning domain name.       |
| authInfoIssueProcess | Authorisation Information Issue Processes | 0+    | read-only  | Aggregation[Authorisation Information Issue Process Object] | The authorisation information issue processes initiated on the owning domain name. |

Object: authInfoProcess

Object Name: Authorisation Information Process Object

Object Type: Process

Extends: baseProcess

Description: Represents the authorisation information that the sponsoring client sets for a domain name, with its expiry date.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name              | Card. | Mutability  | Data Type                        | Description                                                    |
| ------------------ | ------------------------- | ----- | ----------- | -------------------------------- | -------------------------------------------------------------- |
| authInfo           | Authorisation Information | 1     | create-only | Authorisation Information Object | The authorisation information that the sponsoring client sets. |
| expiryDate         | Expiry Date               | 0-1   | create-only | Date                             | The last day on which the authorisation information is valid.  |

Operations: create, read, delete. Input Data Elements: (None). Parameters: (None).

Object: authInfoIssueProcess

Object Name: Authorisation Information Issue Process Object

Object Type: Process

Extends: baseProcess

Description: Represents a request that the server issue authorisation information for a domain name to its registrants.

Reference: [This-ID]

Data Elements: (None)

Operations: create. Input Data Elements: (None). Parameters: (None).

Object: authInfoExpiryMessage

Object Name: Authorisation Information Expiry Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client of the expiry of the authorisation information of a domain name.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| expiryDate | Expiry Date | 1 | read-only | Timestamp | The date and time of the expiry of the authorisation information. |

Object: authInfoIssueMessage

Object Name: Authorisation Information Issue Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that the server issued authorisation information for a domain name to its registrants, at the request of a client.

Reference: [This-ID]

Data Elements: (None)

Object: authInfoWithdrawalMessage

Object Name: Authorisation Information Withdrawal Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that the server deleted the authorisation information that it had issued to the registrants of a domain name, for example because it could not deliver it.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| notices | Notices | 1+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

# Security Considerations {#security}

The extension inherits the authentication and authorisation services of the objects it extends [@!I-D.wullink-rpp-extension-guidelines, section 12]. Only the sponsoring client creates, reads, and deletes an Authorisation Information Process Object, and a server queues a message of the extension for the sponsoring client of the domain name only.

The Authorisation Information of an Authorisation Information Process Object is a secret that authorises a transfer of the domain name. The server returns it in no operation (#auth-info-process-data-elements). A server MUST NOT record it in logs. An expiry date limits the time in which authorisation information that became known to a third party can be used.

Any client can create an Authorisation Information Issue Process Object for any domain name. The server delivers the authorisation information to the registrants only, by a channel outside the protocol, and informs the sponsoring client, so that neither the requesting client nor the sponsoring client learns it. A server that rejects a Create while issued authorisation information is valid (#auth-info-issue-process-create) limits how often a client can cause a delivery to the registrants.

# Privacy Considerations {#privacy}

The server delivers issued authorisation information with the contact data that it holds for the registrants. The Authorisation Information Issue Process Object discloses none of it to the requesting client.

The message types name a domain name and carry no contact information. The privacy considerations of the Registry Notice Object [@!RPP-MESSAGES] apply to the notices of the Authorisation Information Withdrawal Message Object.

# Internationalisation Considerations {#i18n}

None.

{removeInRFC="true"}
{toc="exclude"}
# Changes History

{toc="exclude"}
{numbered="false"}
## 0.1.0

* initial version: the authorisation information process and authorisation information issue process objects, their data elements of the processes object, and the authorisation information expiry, issue and withdrawal message types, moved from the extension de.denic.rpp.rri 0.3.0 #262

{backmatter}

<reference anchor="RPP-MESSAGES" target="https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/docs/extensions/messages-extension.md">
  <front>
    <title>Message Components Extension for the RESTful Provisioning Protocol (RPP)</title>
    <author initials="P." surname="Kowalik" fullname="Pawel Kowalik"/>
    <date year="2026" month="November"/>
  </front>
</reference>
