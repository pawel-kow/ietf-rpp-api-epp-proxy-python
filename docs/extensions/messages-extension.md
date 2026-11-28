%%%
title = "Message Components Extension for the RESTful Provisioning Protocol (RPP)"
abbrev = "RPP Message Components"
area = "Applications and Real-Time"
workgroup = "Network Working Group"
submissiontype = "IETF"
keyword = ["RPP", "provisioning", "registry", "extension", "messages"]
TocDepth = 4
date = 2026-11-28

[seriesInfo]
name = "Internet-Draft"
value = "draft-kowalik-rpp-message-components-00"
stream = "IETF"
status = "informational"

[[author]]
initials="P."
surname="Kowalik"
fullname="Pawel Kowalik"
organization = "DENIC"

%%%

.# Abstract

This document defines a private extension of the RESTful Provisioning Protocol (RPP) that defines Component Objects for the message types of other extensions: a reference to an object, a reference to an object with a date, a notice of the registry, and an abstract base for a message about several objects. It also states how the message types of an extension that builds on it join the Message Data Object. The extension defines no message type of its own.

{mainmatter}

# Introduction {#introduction}

This section states the purpose of the extension, the specifications it builds upon, and the reasons for the extension points it uses.

The RESTful Provisioning Protocol (RPP) is defined by [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], and [@!I-D.ietf-rpp-json]. This document follows the extension specification format of [@!I-D.wullink-rpp-extension-guidelines, section 9].

A registry queues notifications for a client about events that the client did not request, such as a change of a domain name by the registry. The base specifications define message types for a few of them only [@!I-D.ietf-rpp-data-objects, section 9.19]. An extension that defines further message types needs the same parts in many of them:

* a reference to an object that the message is about, in a message that names several objects, while the Base Message Object [@!I-D.ietf-rpp-data-objects, section 9.19.1] refers to one object,
* a reference to an object together with a date that concerns it, such as the date of its expiry, and
* the notices of the registry about the event, each with a code, a human-readable text, and the values that complete the text.

This extension defines these parts once, as Component Objects, so that the message types of several extensions share them. It also states once how the message types of such an extension become part of the Message Data Object (#message), so that each of these extensions defines only its message types.

## Conventions and Terminology {#terminology}

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [@!RFC2119] [@!RFC8174] when, and only when, they appear in all capitals, as shown here.

Terms of the RPP data model, such as Data Object, Component Object, data element, cardinality, mutability, Unique Identifier, and message type, are used as defined in [@!I-D.ietf-rpp-data-objects]. The terms Extension Mapper (`rpp:extends`) and Effective Schema are used as defined in [@!I-D.ietf-rpp-json].

The following term is used in this document:

Dependent extension
: An extension whose definitions refer to a definition of this extension, and whose specification states that it builds on this extension.

## Choice of Extension Points {#choice}

This section is non-normative.

The parts are new Component Objects [@!I-D.wullink-rpp-extension-guidelines, section 5], and the abstract Bulk Base Message Object extends the Base Message Object [@!I-D.ietf-rpp-data-objects, section 9.19.1], as [@!I-D.ietf-rpp-data-objects, section 5] recommends for the message types of extensions. The extension defines no message type, because a message type describes an event, and the events belong to the dependent extensions that define them. It adds no member to a base definition.

The Component Objects are defined in an extension of their own, and not in each dependent extension, so that a client sees one definition for each `@type` value, whichever dependent extensions a server offers. [@!I-D.wullink-rpp-extension-guidelines, section 8.3] asks extensions to be independent of one another. A dependent extension depends on this extension, as a deliberate exception: this extension only defines shared building blocks and the rules that the message types of the dependent extensions have in common.

The base specifications define no extension point for message types: the `data` property of the Message Data Object is a fixed union of the message types of the base specifications [@!I-D.ietf-rpp-json, section 6.8], and the Extension Mapper only adds properties to a definition. A dependent extension therefore names its message types in the member `rpp:messages` of its schema document (#message-type-mapping).

# Extension Overview {#overview}

This section identifies the extension.

| Field                | Value |
| -------------------- | ----- |
| Name                 | RPP Message Components |
| Identifier           | `io.github.pawel-kow.rpp.messages` |
| Version              | 0.1.0 |
| RPP version          | [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], [@!I-D.ietf-rpp-json] |
| Schema `$id`         | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/messages-extension.schema.json> |
| Changed base objects | `message` |
| New objects          | `objectReference`, `datedObjectReference`, `registryNotice`, `bulkBaseMessage` |
Table: Extension Overview

A dependent extension states in its specification that a server that offers a preset with it MUST offer this extension in the same preset, in version 0.1.0 or a later version with the same major version.

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

This section states how the message types of dependent extensions become part of the Message Data Object. The rules apply to every message type that a dependent extension maps in its `rpp:messages` (#message-type-mapping), at a server whose preset contains the dependent extension. This extension itself defines no message type.

## Message Data Object {#message}

* Identifier: message

### Data Elements {#message-data-elements}

None. The Data (`data`) of a message is a message type of the base specifications [@!I-D.ietf-rpp-data-objects, section 9.19] or of a dependent extension that the preset contains.

A server that supports a dependent extension sends a notification that a message type of that extension describes as a message of that type. A server sends a notification that it cannot represent in that type as a Service Notice Message Object [@!I-D.ietf-rpp-data-objects, section 9.19.7]. A server does not send a message of a type that no extension of the preset of the response defines.

### Operations {#message-operations}

#### Query Operation {#message-query}

* Identifier: query

The Identifiers of the message types of the dependent extensions are values of the Message Type parameter (`type`) of the Query operation [@!I-D.ietf-rpp-data-objects, section 15.3.3]. A message matches a value of `type` when the Identifier of the message type of its Data equals the value.

A server responds to a Query whose `type` values name only message types that it does not send under the preset of the request as to a Query on an empty queue.

#### Read and Delete Operations {#message-read-delete}

The extension does not change the Read and Delete operations. A client reads and acknowledges a message of any type by its Message ID alone [@!I-D.ietf-rpp-core, section 16.10.2]. A client that receives a message whose message type it does not know can acknowledge the message by its Message ID.

# New Data Objects {#new-data-objects}

This section defines the Component Objects that the extension introduces. A server uses them only within the message types of dependent extensions.

## Object Reference Object {#object-reference}

* Name: Object Reference Object
* Identifier: objectReference
* Description: A reference to an object that a message is about.
* Data Elements:
  * Object Type
    * Identifier: objectType
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: String
    * Description: The object identifier of the referenced object, for example `domainName` or `contact`.
    * Constraints: (None)
  * Object Identifier
    * Identifier: objectId
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: String
    * Description: The unique identifier of the referenced object.
    * Constraints:
      * The value MUST be the Unique Identifier of an object of the type that the Object Type names.

A data element of a dependent extension whose Data Type is the Object Reference Object can constrain the Object Type to one value.

## Dated Object Reference Object {#dated-object-reference}

* Name: Dated Object Reference Object
* Identifier: datedObjectReference
* Extends: Object Reference Object
* Description: A reference to an object, with a date that concerns the object. The data element that uses it states the meaning of the date.
* Data Elements:
  * Date
    * Identifier: date
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: Timestamp
    * Description: The date and time that concerns the referenced object.
    * Constraints: (None)

## Registry Notice Object {#registry-notice}

* Name: Registry Notice Object
* Identifier: registryNotice
* Description: A notice of the registry about the event that a message reports.
* Data Elements:
  * Code
    * Identifier: code
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: String
    * Description: The code of the notice, which identifies its kind. The registry assigns the codes.
    * Constraints:
      * The value MUST consist of the digits `0` to `9` only.
  * Text
    * Identifier: text
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: String
    * Description: Human-readable text of the notice.
    * Constraints: (None)
  * Arguments
    * Identifier: arguments
    * Cardinality: 0+
    * Mutability: read-only
    * Data Type: String
    * Description: Values that complete the text, for example a reference of the registry to the request that caused the event, or a date.
    * Constraints: (None)

A client identifies the kind of a notice by its Code and MUST NOT rely on its Text, which the registry may change or translate. A client that does not know a Code treats the notice as information only.

## Bulk Base Message Object {#bulk-base-message}

* Name: Bulk Base Message Object
* Identifier: bulkBaseMessage
* Abstract: true
* Extends: Base Message Object
* Description: Base structure for a message about several objects.
* Data Elements:
  * Objects
    * Identifier: objects
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Object Reference Object
    * Description: The objects that the message is about.
    * Constraints: (None)

A message whose type extends the Bulk Base Message Object contains neither the Object Type (`objectType`) nor the Object Identifier (`objectId`) of the Base Message Object. A message type that extends it MAY restate the Objects with the Dated Object Reference Object as its Data Type. In a message type of a dependent extension that extends the Base Message Object, the Object Type and the Object Identifier are required.

# Updated Process Objects {#updated-process-objects}

None.

# New Process Objects {#new-process-objects}

None.

# Endpoints {#endpoints}

None. The Component Objects are carried in messages, which a client retrieves at the messages endpoint [@!I-D.ietf-rpp-core, section 16.10] and selects with the `type` query parameter (#message-query).

# JSON Schema {#json-schema}

This section defines the JSON representation of the Component Objects and the member with which a dependent extension names its message types, following the rules of [@!I-D.ietf-rpp-json, section 4] and the Extension Framework of [@!I-D.ietf-rpp-json, section 7].

The extension defines one JSON Schema document, <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/messages-extension.schema.json>. Every definition of the extension has the prefix `ext.messages.`. A definition of a dependent extension refers to a definition of this extension by its name in the `$defs` of the Effective Schema, for example `{ "$ref": "#/$defs/ext.messages.registryNotice.read" }`, as it refers to a base definition [@!I-D.ietf-rpp-json, section 4.10].

## Extension Mapping {#extension-mapping}

The extension adds no member to a base definition, so its Extension Mapper is empty:

```json
{
  "rpp:extends": {}
}
```

The schema document states the Name, Identifier, and Version of (#overview) in the property `rpp:extension`. The New objects are Component Objects, and `objects` names only Data Objects:

```json
{
  "rpp:extension": {
    "name": "RPP Message Components",
    "id": "io.github.pawel-kow.rpp.messages",
    "version": "0.1.0",
    "objects": []
  }
}
```

## Message Type Mapping {#message-type-mapping}

The `data` property of the definitions `message.read` and `message.create` [@!I-D.ietf-rpp-json, section 6.8] is a `oneOf` of the message types of the base specifications, and the Extension Mapper only adds properties to a definition. The schema document of a dependent extension therefore maps the Identifier of each of its message types to its definition in the member `rpp:messages`, for example:

```
{
  "rpp:messages": {
    "exampleMessage": "#/$defs/ext.example.exampleMessage.read"
  }
}
```

The Effective Schema of `message.read` and `message.create` at a server whose preset contains a dependent extension adds to the `oneOf` of the `data` property a reference to each definition that its `rpp:messages` maps. An Identifier in `rpp:messages` MUST NOT be the Identifier of a message type of the base specifications or of another extension. The schema document of this extension has no member `rpp:messages`: the abstract Bulk Base Message Object and the Component Objects are not message types, and the Effective Schema does not add them to the `data` property.

A> The member `rpp:messages` is not defined by [@!I-D.ietf-rpp-json]. It is proposed for inclusion there as the extension point for message types.

## Definitions {#json-definitions}

Each Component Object repeats the data elements that it inherits as top-level properties [@!I-D.ietf-rpp-json, section 6.2.16]. A dependent extension constrains the Object Type of a reference with `allOf`, for example `{ "allOf": [{ "$ref": "#/$defs/ext.messages.objectReference.read" }, { "properties": { "objectType": { "const": "contact" } } }] }`.

Object Reference Object:

<!-- definition ext.messages.objectReference.read -->
```json
{
  "$defs": {
    "ext.messages.objectReference.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "objectReference", "readOnly": true },
        "objectType": { "type": "string", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId"]
    }
  }
}
```

Dated Object Reference Object:

<!-- definition ext.messages.datedObjectReference.read -->
```json
{
  "$defs": {
    "ext.messages.datedObjectReference.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "datedObjectReference", "readOnly": true },
        "objectType": { "type": "string", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "date": { "type": "string", "format": "date-time", "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "date"]
    }
  }
}
```

Registry Notice Object:

<!-- definition ext.messages.registryNotice.read -->
```json
{
  "$defs": {
    "ext.messages.registryNotice.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "registryNotice", "readOnly": true },
        "code": { "type": "string", "pattern": "^[0-9]+$", "readOnly": true },
        "text": { "type": "string", "readOnly": true },
        "arguments": { "type": "array", "items": { "type": "string" }, "readOnly": true }
      },
      "required": ["@type", "code", "text"]
    }
  }
}
```

Bulk Base Message Object:

<!-- definition ext.messages.bulkBaseMessage.read -->
```json
{
  "$defs": {
    "ext.messages.bulkBaseMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "bulkBaseMessage", "readOnly": true },
        "objects": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.messages.objectReference.read" }, "readOnly": true }
      },
      "required": ["@type", "objects"]
    }
  }
}
```

# Examples {#examples}

This section is non-normative. The examples of messages that use the Component Objects are in the specifications of the dependent extensions.

## Components {#examples-components}

Example Object Reference Object:

<!-- example valid objectReference.read -->
```json
{
    "@type": "objectReference",
    "objectType": "contact",
    "objectId": "sh8013"
}
```

Example Dated Object Reference Object:

<!-- example valid datedObjectReference.read -->
```json
{
    "@type": "datedObjectReference",
    "objectType": "domainName",
    "objectId": "foo.example",
    "date": "2026-12-01T00:00:00Z"
}
```

Example Registry Notice Object:

<!-- example valid registryNotice.read -->
```json
{
    "@type": "registryNotice",
    "code": "1000",
    "text": "The domain name was changed by the registry",
    "arguments": [ "Reference: 4711" ]
}
```

## Invalid Examples {#examples-invalid}

Example Registry Notice Object with a code that is not digits:

<!-- example invalid registryNotice.read -->
```json
{
    "@type": "registryNotice",
    "code": "E1000",
    "text": "The domain name was changed by the registry"
}
```

Example Dated Object Reference Object without a date:

<!-- example invalid datedObjectReference.read -->
```json
{
    "@type": "datedObjectReference",
    "objectType": "domainName",
    "objectId": "foo.example"
}
```

# IANA Considerations {#iana}

This document has no IANA actions. The extension is a private extension [@!I-D.wullink-rpp-extension-guidelines, section 10], and its Identifier is formed by reverse domain name notation [@!I-D.wullink-rpp-extension-guidelines, section 7] under the domain `pawel-kow.github.io`.

For a standardised version of the extension, the following entries would be registered in the RPP Data Object Registry [@!I-D.ietf-rpp-data-objects].

Object: objectReference

Object Name: Object Reference Object

Object Type: Component

Description: A reference to an object that a message is about.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| objectType | Object Type | 1 | read-only | String | The object identifier of the referenced object. |
| objectId | Object Identifier | 1 | read-only | String | The unique identifier of the referenced object. |

Object: datedObjectReference

Object Name: Dated Object Reference Object

Object Type: Component

Extends: objectReference

Description: A reference to an object, with a date that concerns the object.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| date | Date | 1 | read-only | Timestamp | The date and time that concerns the referenced object. |

Object: registryNotice

Object Name: Registry Notice Object

Object Type: Component

Description: A notice of the registry about the event that a message reports.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| code | Code | 1 | read-only | String | The code of the notice. |
| text | Text | 1 | read-only | String | Human-readable text of the notice. |
| arguments | Arguments | 0+ | read-only | String | Values that complete the text. |

Object: bulkBaseMessage

Object Name: Bulk Base Message Object

Object Type: Component

Extends: baseMessage

Abstract: true

Description: Base structure for a message about several objects.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| objects | Objects | 1+ | read-only | Object Reference Object | The objects that the message is about. |

Object: message (additions)

Operation: query

Parameters: the values of `type` (Message Type) include the identifiers of the message types of the dependent extensions.

# Security Considerations {#security}

The extension inherits the authentication and authorisation services of the base specifications [@!I-D.wullink-rpp-extension-guidelines, section 12]. The Component Objects appear only in messages, which a server delivers to the client whose queue holds them [@!I-D.ietf-rpp-core, section 16.10]. An Object Reference names an object and grants no access to it: a client that reads the referenced object is authorised as for any read of it.

# Privacy Considerations {#privacy}

An Object Reference names a contact by its Unique Identifier and carries no contact information. The Text and the Arguments of a Registry Notice are written by the registry. Personal data that the registry puts in them, such as a name in a text, is disclosed to the client that receives the message.

# Internationalisation Considerations {#i18n}

None.

{removeInRFC="true"}
{toc="exclude"}
# Changes History

{toc="exclude"}
{numbered="false"}
## 0.1.0

* initial version: the object reference, dated object reference, registry notice and bulk base message objects, moved from the extension de.denic.rpp.rri 0.3.0, and the rules for the message types of the dependent extensions #261

{backmatter}
