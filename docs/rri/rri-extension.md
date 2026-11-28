%%%
title = "DENIC RRI Extension for the RESTful Provisioning Protocol (RPP)"
abbrev = "RPP DENIC RRI Extension"
area = "Applications and Real-Time"
workgroup = "Network Working Group"
submissiontype = "IETF"
keyword = ["RPP", "provisioning", "registry", "extension", "RRI"]
TocDepth = 4
date = 2026-11-27

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

This document defines a private extension of the RESTful Provisioning Protocol (RPP) for a server whose registry operates the DENIC Registry Robot Interface (RRI) version 5.0. The extension defines the Request Contact Data Object, adds the General Request and Abuse contacts to the Domain Name Data Object, adds the General Request and Abuse URI Templates of a registrar to the Organisation Data Object, adds the data of the domain to the Create operation of the Domain Transfer Process Object, and defines message types for the notifications of the registry.

{mainmatter}

# Introduction {#introduction}

This section states the purpose of the extension, the specifications it builds upon, and the reasons for the extension points it uses.

The RESTful Provisioning Protocol (RPP) is defined by [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], and [@!I-D.ietf-rpp-json]. This document extends these base specifications for a server that provisions objects in a registry operating the DENIC Registry Robot Interface (RRI) version 5.0 [@DENIC-RRI]. It follows the extension specification format of [@!I-D.wullink-rpp-extension-guidelines, section 9].

The registry holds data for which the base specifications define no data element:

Request contacts
: A domain name has, in addition to its holders, at most one General Request contact and at most one Abuse contact. Both are registry contacts of type `REQUEST`, which consist of a handle and a URI Template [@!RFC6570] that states where requests about the domain name are sent. A request contact has no name, no postal address, and no status. It therefore cannot be represented as a Contact Data Object [@!I-D.ietf-rpp-data-objects, section 12], whose Contact Information (`contactInfo`) and Status (`status`) data elements are required.

Registrar request templates
: A registrar account of the registry states a General Request and an Abuse URI Template [@!RFC6570] of its own, which the registry publishes with the public contact data of the registrar. The registry returns each template with the date of its last change, but without a handle, and a client cannot provision it. A template of a registrar therefore cannot be represented as a Request Contact Data Object, whose Handle ID is required, nor in the Contacts (`contacts`) data element of the Organisation Data Object [@!I-D.ietf-rpp-data-objects, section 14], which refers to Contact Data Objects.

Transfer data
: The only transfer of the registry (CHPROV) is requested by the gaining client together with the complete data of the domain name: its holders, its request contacts, and its DNS data, all of which belong to the gaining client. The Domain Transfer Process Object has no data element for this data.

Registry notifications
: The registry queues notifications of fifteen kinds for a client, for example a warning that domain names expire, a change of a domain name by the registry, or a request to verify a contact. The base specifications define message types for a few of them only [@!I-D.ietf-rpp-data-objects, section 9.19], and a Service Notice Message Object carries no structured data. Some notifications name several objects, while the Base Message Object refers to one object.

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

The General Request and Abuse URI Templates of a registrar are defined as data elements of the Organisation Data Object whose Data Type is a new Component Object, the Request Template Object (#request-template), and not as relations to Request Contact Data Objects. The registry discloses no Handle ID and no sponsoring client for them, and a client cannot provision them, so they are not resources. The data elements have Identifiers of their own, and not those of the General Request and Abuse contacts of a domain name, because their Data Type differs.

The notifications of the registry are defined as message types that extend the Base Message Object [@!I-D.ietf-rpp-data-objects, section 9.19.1], as [@!I-D.ietf-rpp-data-objects, section 5] recommends for extensions. Where a message type of the base specifications fits a notification, it is used: the notification of a completed transfer to the losing client is a Transfer Outcome Message Object. A message type for a notification that names several objects extends the Bulk Base Message Object (#bulk-base-message), which holds a list of object references in place of the single Object Type and Object Identifier of the Base Message Object.

The base specifications define no extension point for message types: the `data` property of the Message Data Object is a fixed union of the message types of the base specifications [@!I-D.ietf-rpp-json, section 6.8], and the Extension Mapper only adds properties to a definition. The schema document of the extension therefore names its message types in the member `rpp:messages` (#message-type-mapping).

# Extension Overview {#overview}

This section identifies the extension.

| Field                | Value                                                                                         |
| -------------------- | --------------------------------------------------------------------------------------------- |
| Name                 | DENIC RRI                                                                                     |
| Identifier           | `de.denic.rpp.rri`                                                                            |
| Version              | 0.3.0                                                                                         |
| RPP version          | [@!I-D.ietf-rpp-core], [@!I-D.ietf-rpp-data-objects], [@!I-D.ietf-rpp-json]                   |
| Schema `$id`         | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/rri-extension.schema.json> |
| Changed base objects | `domainName`, `organisation`, `domainTransferProcess`, `message`                              |
| New objects          | `requestContact`, `requestContactAvailability`, `objectReference`, `datedObjectReference`, `registryNotice`, `bulkBaseMessage`, `requestTemplate`, and the message types of (#message-types) |
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

## Organisation Data Object {#organisation}

* Identifier: organisation

### Data Elements {#organisation-data-elements}

The following data elements are added to the Organisation Data Object.

* General Request Template
  * Identifier: generalRequestTemplate
  * Cardinality: 0-1
  * Mutability: read-only
  * Data Type: Request Template Object
  * Description: The URI Template that the organisation states for general requests about the domain names that it sponsors.
  * Constraints: (None)
* Abuse Template
  * Identifier: abuseTemplate
  * Cardinality: 0-1
  * Mutability: read-only
  * Data Type: Request Template Object
  * Description: The URI Template that the organisation states for reports of abuse of the domain names that it sponsors.
  * Constraints: (None)

The registry maintains these data elements outside the protocol. They appear in the response of the Read operation [@!I-D.ietf-rpp-data-objects, section 14.3.2] only.

### Operations {#organisation-operations}

None.

## Message Data Object {#message}

* Identifier: message

### Data Elements {#message-data-elements}

None. The Data (`data`) of a message is a message type of (#message-types) or of the base specifications [@!I-D.ietf-rpp-data-objects, section 9.19].

A server that supports the extension sends a notification of the registry that a message type of this document or of the base specifications describes as a message of that type. A server sends a notification that it cannot represent in that type as a Service Notice Message Object [@!I-D.ietf-rpp-data-objects, section 9.19.7].

### Operations {#message-operations}

#### Query Operation

* Identifier: query

The extension adds the Identifiers of the message types of (#message-types) to the values of the Message Type parameter (`type`) of the Query operation [@!I-D.ietf-rpp-data-objects, section 15.3.3]. A message matches a value of `type` when the Identifier of the message type of its Data equals the value.

A server that supports the extension responds to a Query whose `type` values name only message types that it does not send as to a Query on an empty queue.

#### Read and Delete Operations

The extension does not change the Read and Delete operations. A client reads and acknowledges a message of any type by its Message ID alone [@!I-D.ietf-rpp-core, section 16.10.2].

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

## Request Template Object {#request-template}

* Name: Request Template Object
* Identifier: requestTemplate
* Description: A URI Template to which requests about domain names are sent, with the date of its last change. Unlike a Request Contact Data Object, it has no identifier, and a client cannot provision it.
* Data Elements:
  * URI Template
    * Identifier: uriTemplate
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: String
    * Description: A URI Template [@!RFC6570] that states where requests are sent. The variables `{Alabel}` and `{Ulabel}` stand for the domain name in its A-label and U-label form.
    * Constraints: (None)
  * Update Date
    * Identifier: upDate
    * Cardinality: 0-1
    * Mutability: read-only
    * Data Type: Timestamp
    * Description: The date and time of the most recent modification of the URI Template.
    * Constraints: (None)

## Message Components {#message-components}

This section defines the Component Objects that the message types of the extension use.

### Object Reference Object {#object-reference}

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

### Dated Object Reference Object {#dated-object-reference}

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

### Registry Notice Object {#registry-notice}

* Name: Registry Notice Object
* Identifier: registryNotice
* Description: A notice of the registry about the event that a message reports.
* Data Elements:
  * Code
    * Identifier: code
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: String
    * Description: The code of the notice, which identifies its kind.
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

### Bulk Base Message Object {#bulk-base-message}

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

A message whose type extends the Bulk Base Message Object contains neither the Object Type (`objectType`) nor the Object Identifier (`objectId`) of the Base Message Object.

## Message Types {#message-types}

This section defines the message types of the extension. A server uses each of them as the Data (`data`) of a Message Data Object [@!I-D.ietf-rpp-data-objects, section 15]. In a message type that extends the Base Message Object, the Object Type (`objectType`) and the Object Identifier (`objectId`) are required.

| Identifier | Extends | Objects |
| ---------- | ------- | ------- |
| `domainExpiryWarningMessage` | `bulkBaseMessage` | several domain names |
| `domainExpiryMessage` | `bulkBaseMessage` | several domain names |
| `contactDeletionMessage` | `bulkBaseMessage` | several contacts |
| `authInfoExpiryMessage` | `baseMessage` | a domain name |
| `authInfoIssueMessage` | `baseMessage` | a domain name |
| `authInfoWithdrawalMessage` | `baseMessage` | a domain name |
| `domainDeletionMessage` | `baseMessage` | a domain name |
| `domainLockMessage` | `baseMessage` | a domain name |
| `domainUnlockMessage` | `baseMessage` | a domain name |
| `domainUpdateMessage` | `baseMessage` | a domain name |
| `domainReleaseMessage` | `baseMessage` | a domain name |
| `contactUpdateMessage` | `baseMessage` | a contact |
| `domainStatusMessage` | `baseMessage` | a domain name |
| `contactVerificationMessage` | `baseMessage` | a contact |
Table: Message Types of the Extension


### Domain Expiry Warning Message Object {#domain-expiry-warning-message}

* Name: Domain Expiry Warning Message Object
* Identifier: domainExpiryWarningMessage
* Extends: Bulk Base Message Object
* Description: Notification for the sponsoring client that domain names will expire and be deleted on the given dates.
* Data Elements:
  * Objects
    * Identifier: objects
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Dated Object Reference Object
    * Description: The domain names that will expire, each with the date and time of its expiry.
    * Constraints:
      * The Object Type of each entry MUST be `domainName`.

### Domain Expiry Message Object {#domain-expiry-message}

* Name: Domain Expiry Message Object
* Identifier: domainExpiryMessage
* Extends: Bulk Base Message Object
* Description: Notification for the sponsoring client that domain names expired and were deleted.
* Data Elements:
  * Objects
    * Identifier: objects
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Dated Object Reference Object
    * Description: The domain names that expired, each with the date and time of its expiry.
    * Constraints:
      * The Object Type of each entry MUST be `domainName`.

### Contact Deletion Message Object {#contact-deletion-message}

* Name: Contact Deletion Message Object
* Identifier: contactDeletionMessage
* Extends: Bulk Base Message Object
* Description: Notification for the sponsoring client that the server deleted contacts that no domain name referred to.
* Data Elements:
  * Objects
    * Identifier: objects
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Object Reference Object
    * Description: The deleted contacts.
    * Constraints:
      * The Object Type of each entry MUST be `contact`. A deleted request contact (#request-contact) is reported with the Object Type `contact` as well.

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
* Description: Notification for the sponsoring client that the server issued authorisation information for a domain name to its holders, at the request of a client.
* Data Elements: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

### Authorisation Information Withdrawal Message Object {#auth-info-withdrawal-message}

* Name: Authorisation Information Withdrawal Message Object
* Identifier: authInfoWithdrawalMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that the server deleted the authorisation information that it had issued to the holders of a domain name, because it could not deliver it.
* Data Elements:
  * Notices
    * Identifier: notices
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Registry Notice Object
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

### Domain Deletion Message Object {#domain-deletion-message}

* Name: Domain Deletion Message Object
* Identifier: domainDeletionMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that the server deleted a domain name, for example by a decision of the registry or because verification information was not provided in time.
* Data Elements:
  * Notices
    * Identifier: notices
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Registry Notice Object
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

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
    * Data Type: Registry Notice Object
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
    * Data Type: Registry Notice Object
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

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
    * Data Type: Registry Notice Object
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

### Domain Release Message Object {#domain-release-message}

* Name: Domain Release Message Object
* Identifier: domainReleaseMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that a domain name was released to the registry, which administers it in place of a sponsoring client.
* Data Elements:
  * Notices
    * Identifier: notices
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Registry Notice Object
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
    * Data Type: Registry Notice Object
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `contact`, and the Object Identifier (`objectId`) is the Handle ID of the contact.

### Domain Status Message Object {#domain-status-message}

* Name: Domain Status Message Object
* Identifier: domainStatusMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client of the status of a domain name that the server decided after a request of the client, for example after a risk assessment, and of the deadlines to provide verification information.
* Data Elements:
  * Status
    * Identifier: status
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Domain Name Status Object
    * Description: The status of the domain name.
    * Constraints: (None)
  * Holders
    * Identifier: holders
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Object Reference Object
    * Description: The holders of the domain name that the notification concerns.
    * Constraints:
      * The Object Type of each entry MUST be `contact`.
  * Hold Deadline
    * Identifier: holdDeadline
    * Cardinality: 0-1
    * Mutability: read-only
    * Data Type: Timestamp
    * Description: The date and time by which verification information must be provided, after which the server places the domain name on hold.
    * Constraints: (None)
  * Deletion Deadline
    * Identifier: deletionDeadline
    * Cardinality: 0-1
    * Mutability: read-only
    * Data Type: Timestamp
    * Description: The date and time by which verification information must be provided, after which the server deletes the domain name.
    * Constraints: (None)
  * Notices
    * Identifier: notices
    * Cardinality: 0+
    * Mutability: read-only
    * Data Type: Registry Notice Object
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `domainName`, and the Object Identifier (`objectId`) is the name of the domain name.

### Contact Verification Message Object {#contact-verification-message}

* Name: Contact Verification Message Object
* Identifier: contactVerificationMessage
* Extends: Base Message Object
* Description: Notification for the sponsoring client that verification information must be provided for a contact, to avoid that the domain names that refer to it are placed on hold or deleted.
* Data Elements:
  * Claims
    * Identifier: claims
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: String
    * Description: The claims of the contact to verify, for example `name`, `address`, or `email`.
    * Constraints: (None)
  * Referenced Domain Names
    * Identifier: referencedDomains
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: Integer
    * Description: The number of domain names that refer to the contact.
    * Constraints:
      * The value MUST NOT be negative.
  * Earliest Hold
    * Identifier: earliestHold
    * Cardinality: 0-1
    * Mutability: read-only
    * Data Type: Dated Object Reference Object
    * Description: The domain name that refers to the contact and that the server places on hold first, with the deadline for it.
    * Constraints:
      * The Object Type MUST be `domainName`.
  * Earliest Deletion
    * Identifier: earliestDeletion
    * Cardinality: 1
    * Mutability: read-only
    * Data Type: Dated Object Reference Object
    * Description: The domain name that refers to the contact and that the server deletes first, with the deadline for it.
    * Constraints:
      * The Object Type MUST be `domainName`.
  * Notices
    * Identifier: notices
    * Cardinality: 1+
    * Mutability: read-only
    * Data Type: Registry Notice Object
    * Description: The notices of the registry about the event that the message reports.
    * Constraints: (None)

The Object Type (`objectType`) is `contact`, and the Object Identifier (`objectId`) is the Handle ID of the contact.

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

The transfer is completed immediately. The server MUST respond with the Domain Transfer Process Object in the state `serverApproved`, with `reqClientId` and `actClientId` set to the identifier of the gaining client, and `requestDate` and `actionDate` set to the time of completion.

The server informs the losing client with a message whose Data is a Transfer Outcome Message Object [@!I-D.ietf-rpp-data-objects, section 9.19.4]. Its Transfer Status (`trStatus`) is `serverApproved`, its Object Type (`objectType`) is `domainName`, its Object Identifier (`objectId`) is the name of the domain name, and its Request Date (`requestDate`) and Action Date (`actionDate`) are the time of completion. Its Process (`process`) is the Domain Transfer Process Object of the response to the gaining client, so that the losing client learns the identifier of the gaining client.

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

The data elements that the extension adds to the Domain Name Data Object, the Organisation Data Object, and the Domain Transfer Process Object do not have Direct Access and add no endpoints. The message types of the extension add no endpoints either: a client retrieves them at the messages endpoint [@!I-D.ietf-rpp-core, section 16.10] and selects them with the `type` query parameter (#message-operations).

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

Example request for the oldest message about the status of a domain name or the verification of a contact:

```http
GET /messages?type=domainStatusMessage&type=contactVerificationMessage HTTP/1.1
Host: rpp.example
Authorization: Bearer <token>
Accept: application/rpp+json
RPP-Cltrid: ABC-12347
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
    "#/$defs/organisation.read": "#/$defs/ext.rri.organisation.read",
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
    "version": "0.3.0",
    "objects": ["requestContact"]
  }
}
```

## Message Type Mapping {#message-type-mapping}

The `data` property of the definitions `message.read` and `message.create` [@!I-D.ietf-rpp-json, section 6.8] is a `oneOf` of the message types of the base specifications, and the Extension Mapper only adds properties to a definition. The schema document of the extension therefore maps the Identifier of each of its message types to its definition in the member `rpp:messages`:

```json
{
  "rpp:messages": {
    "domainExpiryWarningMessage": "#/$defs/ext.rri.domainExpiryWarningMessage.read",
    "domainExpiryMessage": "#/$defs/ext.rri.domainExpiryMessage.read",
    "authInfoExpiryMessage": "#/$defs/ext.rri.authInfoExpiryMessage.read",
    "authInfoIssueMessage": "#/$defs/ext.rri.authInfoIssueMessage.read",
    "authInfoWithdrawalMessage": "#/$defs/ext.rri.authInfoWithdrawalMessage.read",
    "domainDeletionMessage": "#/$defs/ext.rri.domainDeletionMessage.read",
    "domainLockMessage": "#/$defs/ext.rri.domainLockMessage.read",
    "domainUnlockMessage": "#/$defs/ext.rri.domainUnlockMessage.read",
    "domainUpdateMessage": "#/$defs/ext.rri.domainUpdateMessage.read",
    "domainReleaseMessage": "#/$defs/ext.rri.domainReleaseMessage.read",
    "contactUpdateMessage": "#/$defs/ext.rri.contactUpdateMessage.read",
    "contactDeletionMessage": "#/$defs/ext.rri.contactDeletionMessage.read",
    "domainStatusMessage": "#/$defs/ext.rri.domainStatusMessage.read",
    "contactVerificationMessage": "#/$defs/ext.rri.contactVerificationMessage.read"
  }
}
```

The Effective Schema of `message.read` and `message.create` at a server whose preset contains the extension adds to the `oneOf` of the `data` property a reference to each definition that `rpp:messages` maps. The abstract Bulk Base Message Object and the components of (#message-components) are not mapped. A client that receives a message whose message type it does not know can acknowledge the message by its Message ID.

A> The member `rpp:messages` is not defined by [@!I-D.ietf-rpp-json]. It is proposed for inclusion there as the extension point for message types.

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

## Organisation Data Object {#json-organisation}

Read response schema:

<!-- definition ext.rri.organisation.read -->
```json
{
  "$defs": {
    "ext.rri.organisation.read": {
      "type": "object",
      "properties": {
        "generalRequestTemplate": { "$ref": "#/$defs/ext.rri.requestTemplate.read", "readOnly": true },
        "abuseTemplate": { "$ref": "#/$defs/ext.rri.requestTemplate.read", "readOnly": true }
      }
    }
  }
}
```

The Extension Mapper extends only the read definition, because the data elements are read-only. A Create or Update request that contains one of them fails the Effective Schema.

The Request Template Object:

<!-- definition ext.rri.requestTemplate.read -->
```json
{
  "$defs": {
    "ext.rri.requestTemplate.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "requestTemplate", "readOnly": true },
        "uriTemplate": { "type": "string", "readOnly": true },
        "upDate": { "type": "string", "format": "date-time", "readOnly": true }
      },
      "required": ["@type", "uriTemplate"]
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

## Message Objects {#json-messages}

Each message type repeats the data elements that it inherits as top-level properties [@!I-D.ietf-rpp-json, section 6.2.16]. A message type that extends the Bulk Base Message Object does not declare `objectType` and `objectId`. The value of `objectType` of a referenced object is constrained with `allOf`.

### Components

Object Reference Object:

<!-- definition ext.rri.objectReference.read -->
```json
{
  "$defs": {
    "ext.rri.objectReference.read": {
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

<!-- definition ext.rri.datedObjectReference.read -->
```json
{
  "$defs": {
    "ext.rri.datedObjectReference.read": {
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

<!-- definition ext.rri.registryNotice.read -->
```json
{
  "$defs": {
    "ext.rri.registryNotice.read": {
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

<!-- definition ext.rri.bulkBaseMessage.read -->
```json
{
  "$defs": {
    "ext.rri.bulkBaseMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "bulkBaseMessage", "readOnly": true },
        "objects": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.rri.objectReference.read" }, "readOnly": true }
      },
      "required": ["@type", "objects"]
    }
  }
}
```

### Message Types

Domain Expiry Warning Message Object:

<!-- definition ext.rri.domainExpiryWarningMessage.read -->
```json
{
  "$defs": {
    "ext.rri.domainExpiryWarningMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainExpiryWarningMessage", "readOnly": true },
        "objects": { "type": "array", "minItems": 1, "items": { "allOf": [{ "$ref": "#/$defs/ext.rri.datedObjectReference.read" }, { "properties": { "objectType": { "const": "domainName" } } }] }, "readOnly": true }
      },
      "required": ["@type", "objects"]
    }
  }
}
```

Domain Expiry Message Object:

<!-- definition ext.rri.domainExpiryMessage.read -->
```json
{
  "$defs": {
    "ext.rri.domainExpiryMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainExpiryMessage", "readOnly": true },
        "objects": { "type": "array", "minItems": 1, "items": { "allOf": [{ "$ref": "#/$defs/ext.rri.datedObjectReference.read" }, { "properties": { "objectType": { "const": "domainName" } } }] }, "readOnly": true }
      },
      "required": ["@type", "objects"]
    }
  }
}
```

Contact Deletion Message Object:

<!-- definition ext.rri.contactDeletionMessage.read -->
```json
{
  "$defs": {
    "ext.rri.contactDeletionMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "contactDeletionMessage", "readOnly": true },
        "objects": { "type": "array", "minItems": 1, "items": { "allOf": [{ "$ref": "#/$defs/ext.rri.objectReference.read" }, { "properties": { "objectType": { "const": "contact" } } }] }, "readOnly": true }
      },
      "required": ["@type", "objects"]
    }
  }
}
```

Authorisation Information Expiry Message Object:

<!-- definition ext.rri.authInfoExpiryMessage.read -->
```json
{
  "$defs": {
    "ext.rri.authInfoExpiryMessage.read": {
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

<!-- definition ext.rri.authInfoIssueMessage.read -->
```json
{
  "$defs": {
    "ext.rri.authInfoIssueMessage.read": {
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

<!-- definition ext.rri.authInfoWithdrawalMessage.read -->
```json
{
  "$defs": {
    "ext.rri.authInfoWithdrawalMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "authInfoWithdrawalMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.rri.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Domain Deletion Message Object:

<!-- definition ext.rri.domainDeletionMessage.read -->
```json
{
  "$defs": {
    "ext.rri.domainDeletionMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainDeletionMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.rri.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Domain Lock Message Object:

<!-- definition ext.rri.domainLockMessage.read -->
```json
{
  "$defs": {
    "ext.rri.domainLockMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainLockMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.rri.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Domain Unlock Message Object:

<!-- definition ext.rri.domainUnlockMessage.read -->
```json
{
  "$defs": {
    "ext.rri.domainUnlockMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainUnlockMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.rri.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Domain Update Message Object:

<!-- definition ext.rri.domainUpdateMessage.read -->
```json
{
  "$defs": {
    "ext.rri.domainUpdateMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainUpdateMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.rri.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Domain Release Message Object:

<!-- definition ext.rri.domainReleaseMessage.read -->
```json
{
  "$defs": {
    "ext.rri.domainReleaseMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainReleaseMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.rri.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Contact Update Message Object:

<!-- definition ext.rri.contactUpdateMessage.read -->
```json
{
  "$defs": {
    "ext.rri.contactUpdateMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "contactUpdateMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "contact", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.rri.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "notices"]
    }
  }
}
```

Domain Status Message Object:

<!-- definition ext.rri.domainStatusMessage.read -->
```json
{
  "$defs": {
    "ext.rri.domainStatusMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "domainStatusMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "domainName", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "status": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/domainStatus.read" }, "readOnly": true },
        "holders": { "type": "array", "minItems": 1, "items": { "allOf": [{ "$ref": "#/$defs/ext.rri.objectReference.read" }, { "properties": { "objectType": { "const": "contact" } } }] }, "readOnly": true },
        "holdDeadline": { "type": "string", "format": "date-time", "readOnly": true },
        "deletionDeadline": { "type": "string", "format": "date-time", "readOnly": true },
        "notices": { "type": "array", "items": { "$ref": "#/$defs/ext.rri.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "status", "holders"]
    }
  }
}
```

Contact Verification Message Object:

<!-- definition ext.rri.contactVerificationMessage.read -->
```json
{
  "$defs": {
    "ext.rri.contactVerificationMessage.read": {
      "type": "object",
      "properties": {
        "@type": { "type": "string", "const": "contactVerificationMessage", "readOnly": true },
        "objectType": { "type": "string", "const": "contact", "readOnly": true },
        "objectId": { "type": "string", "readOnly": true },
        "claims": { "type": "array", "minItems": 1, "items": { "type": "string" }, "readOnly": true },
        "referencedDomains": { "type": "integer", "minimum": 0, "readOnly": true },
        "earliestHold": { "allOf": [{ "$ref": "#/$defs/ext.rri.datedObjectReference.read" }, { "properties": { "objectType": { "const": "domainName" } } }], "readOnly": true },
        "earliestDeletion": { "allOf": [{ "$ref": "#/$defs/ext.rri.datedObjectReference.read" }, { "properties": { "objectType": { "const": "domainName" } } }], "readOnly": true },
        "notices": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/ext.rri.registryNotice.read" }, "readOnly": true }
      },
      "required": ["@type", "objectType", "objectId", "claims", "referencedDomains", "earliestDeletion", "notices"]
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

## Organisation {#examples-organisation}

### Read

Example organisation read response of a registrar with request templates:

<!-- example valid organisation.read -->
```json
{
    "@type": "organisation",
    "id": "DENIC-1000022",
    "provMetadata": {
        "@type": "provMetadata",
        "spClientId": "DENIC-1000022",
        "upDate": "2026-11-12T00:20:20Z"
    },
    "status": [ { "@type": "organisationStatus", "label": "ok" } ],
    "roles": {
        "registrar": {
            "@type": "organisationRole",
            "status": [ { "@type": "organisationRoleStatus", "label": "ok" } ]
        }
    },
    "parent": { "@type": "organisation", "id": "DENIC-1000020" },
    "contactInfo": {
        "@type": "Card",
        "version": "2.0",
        "kind": "org",
        "name": { "full": "Example Registrar GmbH" },
        "addresses": {
            "addr": {
                "components": [
                    { "kind": "name", "value": "Example Street 1" },
                    { "kind": "locality", "value": "Frankfurt am Main" },
                    { "kind": "postcode", "value": "60311" }
                ],
                "countryCode": "DE"
            }
        },
        "phones": {
            "voice": { "number": "tel:+49.695550100" },
            "fax": { "number": "tel:+49.695550199", "features": { "fax": true } }
        },
        "emails": { "email": { "address": "info@example.com" } },
        "links": { "url": { "uri": "https://www.example.com/" } }
    },
    "generalRequestTemplate": {
        "@type": "requestTemplate",
        "uriTemplate": "https://www.example.com/contact?domain={Alabel}",
        "upDate": "2026-11-10T09:00:00Z"
    },
    "abuseTemplate": {
        "@type": "requestTemplate",
        "uriTemplate": "mailto:abuse@example.com",
        "upDate": "2026-11-10T09:00:00Z"
    }
}
```

## Messages {#examples-messages}

Example message read response with a Domain Status Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "8960348c-2a2b-4c41-9d8e-1f7e2b6c0a11",
    "creationDate": "2026-11-12T14:51:08Z",
    "status": "queued",
    "data": {
        "@type": "domainStatusMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "status": [ { "@type": "domainStatus", "label": "serverHold" } ],
        "holders": [
            { "@type": "objectReference", "objectType": "contact", "objectId": "DENIC-1000022-HOLDER" }
        ],
        "deletionDeadline": "2026-11-24T14:51:08Z",
        "notices": [
            {
                "@type": "registryNotice",
                "code": "16350000041",
                "text": "Verification information must be provided for the holder(s) to avoid deletion by",
                "arguments": [ "Date: 2026-11-24T14:51:08Z", "VerificationClaims: address;name" ]
            }
        ]
    }
}
```

Example message read response with a Contact Verification Message Object:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "5d1c7a40-8b3e-4f0a-a6d2-3c9e8f1b2d44",
    "creationDate": "2026-11-12T15:00:00Z",
    "status": "queued",
    "data": {
        "@type": "contactVerificationMessage",
        "objectType": "contact",
        "objectId": "DENIC-1000022-HOLDER",
        "claims": [ "name", "address" ],
        "referencedDomains": 2,
        "earliestDeletion": {
            "@type": "datedObjectReference",
            "objectType": "domainName",
            "objectId": "foo.example",
            "date": "2026-11-24T14:51:08Z"
        },
        "notices": [
            {
                "@type": "registryNotice",
                "code": "16350000051",
                "text": "Please provide the requested verification information by means of a Contact UPDATE"
            }
        ]
    }
}
```

Example message read response with a Domain Expiry Warning Message Object about two domain names:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "02699380-9c7a-11de-8188-9ff72af94906",
    "creationDate": "2026-11-12T00:00:00Z",
    "status": "queued",
    "data": {
        "@type": "domainExpiryWarningMessage",
        "objects": [
            { "@type": "datedObjectReference", "objectType": "domainName", "objectId": "foo.example", "date": "2026-11-19T00:00:00Z" },
            { "@type": "datedObjectReference", "objectType": "domainName", "objectId": "bar.example", "date": "2026-11-19T00:00:00Z" }
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
            { "@type": "objectReference", "objectType": "contact", "objectId": "DENIC-1000022-OLD1" },
            { "@type": "objectReference", "objectType": "contact", "objectId": "DENIC-1000022-OLD2" }
        ]
    }
}
```

Example message read response for the losing client of a transfer:

<!-- example valid message.read -->
```json
{
    "@type": "message",
    "id": "1b2c3d4e-5f60-4718-9a0b-c1d2e3f40516",
    "creationDate": "2026-11-14T12:00:00Z",
    "status": "queued",
    "data": {
        "@type": "transferOutcomeMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "trStatus": "serverApproved",
        "requestDate": "2026-11-14T12:00:00Z",
        "actionDate": "2026-11-14T12:00:00Z",
        "process": {
            "@type": "domainTransferProcess",
            "trStatus": "serverApproved",
            "reqClientId": "DENIC-1000002",
            "requestDate": "2026-11-14T12:00:00Z",
            "actClientId": "DENIC-1000002",
            "actionDate": "2026-11-14T12:00:00Z"
        }
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

Example message read response with a Domain Status Message Object without a status:

<!-- example invalid message.read -->
```json
{
    "@type": "message",
    "id": "8960348c-2a2b-4c41-9d8e-1f7e2b6c0a11",
    "creationDate": "2026-11-12T14:51:08Z",
    "status": "queued",
    "data": {
        "@type": "domainStatusMessage",
        "objectType": "domainName",
        "objectId": "foo.example",
        "holders": [
            { "@type": "objectReference", "objectType": "contact", "objectId": "DENIC-1000022-HOLDER" }
        ]
    }
}
```

Example message read response with a Domain Expiry Message Object that refers to a contact:

<!-- example invalid message.read -->
```json
{
    "@type": "message",
    "id": "02699380-9c7a-11de-8188-9ff72af94907",
    "creationDate": "2026-11-12T00:00:00Z",
    "status": "queued",
    "data": {
        "@type": "domainExpiryMessage",
        "objects": [
            { "@type": "datedObjectReference", "objectType": "contact", "objectId": "DENIC-1000022-HOLDER", "date": "2026-11-12T00:00:00Z" }
        ]
    }
}
```

Example organisation read response with a General Request Template without a URI Template:

<!-- example invalid organisation.read -->
```json
{
    "@type": "organisation",
    "id": "DENIC-1000022",
    "provMetadata": { "@type": "provMetadata", "spClientId": "DENIC-1000022" },
    "status": [ { "@type": "organisationStatus", "label": "ok" } ],
    "roles": { "registrar": { "@type": "organisationRole" } },
    "generalRequestTemplate": { "@type": "requestTemplate", "upDate": "2026-11-10T09:00:00Z" }
}
```

Example organisation read response with a reference to a request contact as Abuse Template:

<!-- example invalid organisation.read -->
```json
{
    "@type": "organisation",
    "id": "DENIC-1000022",
    "provMetadata": { "@type": "provMetadata", "spClientId": "DENIC-1000022" },
    "status": [ { "@type": "organisationStatus", "label": "ok" } ],
    "roles": { "registrar": { "@type": "organisationRole" } },
    "abuseTemplate": { "@type": "requestContact", "id": "DENIC-1000022-AB" }
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

Object: requestTemplate

Object Name: Request Template Object

Object Type: Component

Description: A URI Template to which requests about domain names are sent, with the date of its last change.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| uriTemplate | URI Template | 1 | read-only | String | A URI Template that states where requests are sent. |
| upDate | Update Date | 0-1 | read-only | Timestamp | The date and time of the most recent modification of the URI Template. |

Object: domainName (additions)

Data Elements

| Element Identifier | Element Name            | Card. | Mutability | Data Type                               | Description                                                           |
| ------------------ | ----------------------- | ----- | ---------- | --------------------------------------- | --------------------------------------------------------------------- |
| generalRequest     | General Request Contact | 0-1   | read-write | Aggregation[Request Contact Data Object] | The request contact to which general requests about the domain name are sent. |
| abuse              | Abuse Contact           | 0-1   | read-write | Aggregation[Request Contact Data Object] | The request contact to which reports of abuse of the domain name are sent.   |

Object: organisation (additions)

Data Elements

| Element Identifier     | Element Name             | Card. | Mutability | Data Type               | Description                                                                 |
| ---------------------- | ------------------------ | ----- | ---------- | ----------------------- | --------------------------------------------------------------------------- |
| generalRequestTemplate | General Request Template | 0-1   | read-only  | Request Template Object | The URI Template that the organisation states for general requests.         |
| abuseTemplate          | Abuse Template           | 0-1   | read-only  | Request Template Object | The URI Template that the organisation states for reports of abuse.         |

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

Object: domainExpiryWarningMessage

Object Name: Domain Expiry Warning Message Object

Object Type: Component

Extends: bulkBaseMessage

Description: Notification for the sponsoring client that domain names will expire and be deleted on the given dates.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| objects | Objects | 1+ | read-only | Dated Object Reference Object | The domain names that will expire, each with the date and time of its expiry. |

Object: domainExpiryMessage

Object Name: Domain Expiry Message Object

Object Type: Component

Extends: bulkBaseMessage

Description: Notification for the sponsoring client that domain names expired and were deleted.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| objects | Objects | 1+ | read-only | Dated Object Reference Object | The domain names that expired, each with the date and time of its expiry. |

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

Description: Notification for the sponsoring client that the server issued authorisation information for a domain name to its holders, at the request of a client.

Reference: [This-ID]

Data Elements: (None)

Object: authInfoWithdrawalMessage

Object Name: Authorisation Information Withdrawal Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that the server deleted the authorisation information that it had issued to the holders of a domain name, because it could not deliver it.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| notices | Notices | 1+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

Object: domainDeletionMessage

Object Name: Domain Deletion Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that the server deleted a domain name, for example by a decision of the registry or because verification information was not provided in time.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| notices | Notices | 1+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

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

Object: domainReleaseMessage

Object Name: Domain Release Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that a domain name was released to the registry, which administers it in place of a sponsoring client.

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

Object: domainStatusMessage

Object Name: Domain Status Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client of the status of a domain name that the server decided after a request of the client, for example after a risk assessment, and of the deadlines to provide verification information.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| status | Status | 1+ | read-only | Domain Name Status Object | The status of the domain name. |
| holders | Holders | 1+ | read-only | Object Reference Object | The holders of the domain name that the notification concerns. |
| holdDeadline | Hold Deadline | 0-1 | read-only | Timestamp | The date and time by which verification information must be provided, after which the server places the domain name on hold. |
| deletionDeadline | Deletion Deadline | 0-1 | read-only | Timestamp | The date and time by which verification information must be provided, after which the server deletes the domain name. |
| notices | Notices | 0+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

Object: contactVerificationMessage

Object Name: Contact Verification Message Object

Object Type: Component

Extends: baseMessage

Description: Notification for the sponsoring client that verification information must be provided for a contact, to avoid that the domain names that refer to it are placed on hold or deleted.

Reference: [This-ID]

Data Elements

| Element Identifier | Element Name | Card. | Mutability | Data Type | Description |
| ------------------ | ------------ | ----- | ---------- | --------- | ----------- |
| claims | Claims | 1+ | read-only | String | The claims of the contact to verify, for example `name`, `address`, or `email`. |
| referencedDomains | Referenced Domain Names | 1 | read-only | Integer | The number of domain names that refer to the contact. |
| earliestHold | Earliest Hold | 0-1 | read-only | Dated Object Reference Object | The domain name that refers to the contact and that the server places on hold first, with the deadline for it. |
| earliestDeletion | Earliest Deletion | 1 | read-only | Dated Object Reference Object | The domain name that refers to the contact and that the server deletes first, with the deadline for it. |
| notices | Notices | 1+ | read-only | Registry Notice Object | The notices of the registry about the event that the message reports. |

Object: message (additions)

Operation: query

Parameters: the values of `type` (Message Type) include the identifiers of the message types above.

# Security Considerations {#security}

The extension inherits the authentication and authorisation services of the objects it extends [@!I-D.wullink-rpp-extension-guidelines, section 12]. A request contact is accessible to its sponsoring client only. A server MUST reject the use of another client's request contact in any operation, including as a data element of a domain name.

The Object Authorisation of a transfer request is forwarded to the registry. A server MUST NOT record it in logs.

A server forwards the URI Template to the registry, which expands it with a sample domain name on creation and rejects a template that it cannot expand. A server that does not forward the template to such a registry MUST check the constraints of (#request-contact-data-elements) itself before it stores or publishes the template.

# Privacy Considerations {#privacy}

The expanded URI Template of a domain name's request contacts is published in the registry's registration data directory service. A `mailto` template that names the mailbox of a natural person makes that address public. A client SHOULD use a role mailbox or a web form in a request contact, because the template is published for every domain name that refers to it. A request contact holds no other personal data, and the registry rejects verification data on it.

The General Request and Abuse Templates of an organisation are part of the public contact data of a registrar, which the registry publishes, and any client can read them [@!I-D.ietf-rpp-data-objects, section 14.3.2]. As for a request contact, a `mailto` template that names the mailbox of a natural person makes that address public.

The message types of the extension name contacts by their Handle ID and carry no contact information, such as the name or the postal address of a holder. The Claims of a Contact Verification Message Object name the kinds of contact information to verify, not their values.

# Internationalisation Considerations {#i18n}

The variable `{Ulabel}` expands to the U-label of the domain name. The encoding of a U-label in the expanded URI is defined by [@!RFC6570, section 3.2.1]. The URI Template itself consists of ASCII characters.

{removeInRFC="true"}
{toc="exclude"}
# Changes History

{toc="exclude"}
{numbered="false"}
## 0.2.0 - 0.3.0

* add the message types of the registry notifications, the bulk base message object, the object reference, dated object reference and registry notice objects #248
* add the member rpp:messages to the schema document as the extension point for message types #248
* the type parameter of the message query takes the identifiers of the message types #248
* inform the losing client of a transfer with a transfer outcome message #248
* add the general request and abuse templates of a registrar to the organisation data object, and the request template object; the organisation read keeps the first URL of a registrar #249

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

The implementation maps the notifications of the registry (QUEUE-READ) to the message types as follows:

| RRI `msgType`                 | RPP message type             |
| ----------------------------- | ---------------------------- |
| `expireWarning`               | `domainExpiryWarningMessage` |
| `expire`                      | `domainExpiryMessage`        |
| `authInfoExpire`              | `authInfoExpiryMessage`      |
| `authInfo2Notify`             | `authInfoIssueMessage`       |
| `chprovAuthInfo`              | `transferOutcomeMessage`     |
| `domainDelete`                | `domainDeletionMessage`      |
| `authInfo2Delete`             | `authInfoWithdrawalMessage`  |
| `lockCreate`                  | `domainLockMessage`          |
| `lockDelete`                  | `domainUnlockMessage`        |
| `domainUpdate`                | `domainUpdateMessage`        |
| `domainTransit`               | `domainReleaseMessage`       |
| `contactUpdate`               | `contactUpdateMessage`       |
| `contactDelete`               | `contactDeletionMessage`     |
| `domainStatusUpdate`          | `domainStatusMessage`        |
| `contactVerificationRequired` | `contactVerificationMessage` |
Table: Message Types of RRI

The data of a notification maps as follows:

* `msgid` is the Message ID (`id`), `msgtime` the Creation Date (`creationDate`), and `msgcnt` the `RPP-Queue-Size`.
* A domain (`msg:domain`) is referred to by its A-label (`msg:ace`), a contact by its handle (`msg:handle`).
* The entries of `expireWarning` and `expire` are Dated Object Reference Objects whose Date is `msg:expire`.
* `chprovAuthInfo`: the Request Date and Action Date are `msgtime`, the `reqClientId` and `actClientId` of the Process are `msg:new`. `msg:old` is the receiving RegAcc and is not represented.
* `authInfoExpire`: the Expiry Date is `msg:authinfoexpire`.
* `msg:message` is a Registry Notice Object: its `code` attribute is the Code, `tr:text` the Text, and each `tr:argument` an Argument. The `level` attribute is not represented.
* `domainStatusUpdate`: the Status is `msg:status`, mapped as for a domain INFO (`connect` to `ok`, `failed` to `inactive`, `pendingCreate`, `serverHold`, `redemptionPeriod` to `pendingDelete`). The Holders are `msg:holders/msg:handle`, the Hold Deadline is `msg:verificationDeadlineBeforeDedelegation`, and the Deletion Deadline is `msg:verificationDeadlineBeforeDeletion`.
* `contactVerificationRequired`: the Claims are `msg:verificationClaims/msg:claim`, the Referenced Domain Names `msg:numberOfReferencedDomainsTotal`, the Earliest Hold `msg:earliestDomainForDedelegation` and the Earliest Deletion `msg:earliestDomainForDeletion`, each with its `msg:verificationDeadline` as Date.
* `contactDelete`: each `msg:handles/msg:handle` is an entry of the Objects. The registry does not say whether a handle was a contact or a request contact.

A> TBC: the registry describes the holders of `domainStatusUpdate` as those for which no verification is required, while its example lists every holder.

The implementation serves the messages operations as follows:

* A Query without `type` is a QUEUE-READ without `msgType`. A Query with `type` is a QUEUE-READ with the `msgType` of each value that has one, and the oldest of the messages read (by `msgtime`) is returned. A value without an RRI `msgType`, such as `autoRenewalMessage` or `serviceNoticeMessage`, reads nothing, so a Query with only such values answers as on an empty queue.
* `RPP-Queue-Size` of a Query without `type` is the `msgcnt` of its QUEUE-READ, and of a Query with `type` the sum of the `msgcnt` values of the QUEUE-READs sent.
* QUEUE-DELETE deletes only the oldest message overall or of a given `msgType`. A Delete is a QUEUE-DELETE without `msgType`. When the registry refuses it with `63650063607` (not the oldest), the implementation reads with QUEUE-READ per `msgType` to find the type whose oldest message has the Message ID, and repeats the QUEUE-DELETE with that `msgType`. A Read by Message ID finds the message in the same way. These reads cost no quota.

The implementation serves the Read operation of the Organisation Data Object with regacc INFO, for any RegAcc and to any client, and maps its response as follows:

| RPP                                 | RRI (XML 5.0)                                                     |
| ----------------------------------- | ----------------------------------------------------------------- |
| `id`                                | `regacc:handle`                                                   |
| `provMetadata.spClientId`           | `regacc:handle`                                                   |
| `provMetadata.upDate`               | `regacc:changed`                                                  |
| `status`                            | `ok`, which RRI does not hold                                     |
| `roles`                             | `registrar`, with the status `ok` and no `roleId`                 |
| `parent`                            | `regacc:memberacc`, unless it is the `regacc:handle`              |
| `contactInfo.kind`                  | `org`                                                             |
| `contactInfo.name.full`             | `regacc:name`                                                     |
| `contactInfo.addresses.addr`        | `regacc:postal`                                                   |
| `contactInfo.phones`                | `regacc:phone` and `regacc:fax`                                   |
| `contactInfo.emails.email`          | `regacc:email`                                                    |
| `contactInfo.links.url`             | the first `regacc:url` with a scheme                              |
| `generalRequestTemplate`            | `regacc:contact role="generalrequest"`                            |
| `abuseTemplate`                     | `regacc:contact role="abusecontact"`                              |
| `requestTemplate.uriTemplate`       | `contact:uri-template`                                            |
| `requestTemplate.upDate`            | `contact:changed`                                                 |
Table: Mapping of regacc INFO

* The Sponsoring Client ID is the RegAccId itself, because a RegAcc maintains its own profile, in the registry's web interface and not through RRI.
* `regacc:memberacc` identifies the member that holds the RegAcc. It is a reference to an organisation that regacc INFO may not find, in which case its Read is 404. A MemberAccId equal to the RegAccId is not represented, as an organisation that is its own parent would be a loop [@!I-D.ietf-rpp-data-objects, section 14.2].
* Each `regacc:address` is a `name` component, in its order, `regacc:postalCode` the `postcode`, `regacc:city` the `locality`, and `regacc:countryCode` the `countryCode`.
* The phone and fax numbers of a RegAcc are E.123 numbers (`\+[/\-\.\s0-9x]{1,254}`). Each becomes an rpp-telephone-uri of the RPP JSContact profile [@I-D.wullink-rpp-jscontact-profile]: the digits before the first separator (space, `-`, `.`, or `/`) are the country code, the other digits before an `x` the subscriber number, and the digits after the `x` the extension (`;ext=`). The phone numbers are `voice`, `voice-1`, and so on, without `features`, the fax numbers `fax`, `fax-1`, and so on, with the feature `fax`, in their order. A number that does not give an rpp-telephone-uri is left out.
* The first URL with a scheme is the link `url`. The Card profile defines no key for a further link, so further URLs are left out. A URL without a scheme is left out.
* The `contact:type` of a template (`REQUEST`) is not represented. A `regacc:contact` without `contact:uri-template` is left out.
* Create, Update, and Delete of an organisation, and its `users` and `processes` endpoints, are 501 (`02101`). The registry maintains RegAccs outside RRI.

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
| Read or Delete of a Message ID that is the oldest message of no type | 404         | 02303           |
| Read of an organisation whose identifier is not a RegAccId (63310062008) | 400     | 02005           |
| Read of an organisation that does not exist (63300062010)            | 404         | 02303           |
| Create, Update, or Delete of an organisation, its users or processes | 501         | 02101           |
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
