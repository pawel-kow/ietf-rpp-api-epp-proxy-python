# Spec issues

Points in the RPP drafts that could not be implemented, or where the intended behaviour is unclear.
Each entry says what the proxy does today.

## Phone numbers

- The JSContact profile -02 requires `tel:+CC.number`, but the `contactInfo` examples (json §8.2) still use `tel:+1-703-555-5555`, which the profile rejects.
- **Proxy:** follows the profile, anything else is a 400. `;ext=` maps to EPP `x`. The tests based on json §8.2 use the profile form.

## Phone key and features

- The profile assumes voice when `features` is absent, and gives the key `fax` to the preferred fax number. It does not say what a `fax` key without `features` means, or a `voice` key with `{"fax": true}`.
- Should the key pattern and `features` always have to match? The type of a number is stated twice, and §4.1.10 and §4.1.8 do not bind the two together. If they must match, `features` is redundant for a single-purpose number, and the profile should say so and name the rejection. If they need not, it should say which one decides.
- §4.1.8 says `features` "MUST contain only the "voice" or "fax" keys", which can mean those two keys are allowed together, or exactly one of them. If both are allowed, the meaning of the map key is open: does `voice` with `{"voice": true, "fax": true}` also count as the preferred fax number, and which entry wins if a `fax` key exists too?
- Suggested text for §4.1.8: "The "features" member MUST contain exactly one key, and that key MUST match the predefined key of the map entry."
- **Proxy:** a key and features that disagree are a 400. Both features on one number are a 501 (`02102`). EPP could hold such a number as both `voice` and `fax`, but it would read back as two entries, so the round trip would not keep what the client sent.

## Localization language

- The profile keys `localizations` by language tag and wants `language` on the Card when there are localizations. EPP `postalInfo type="loc"` has no language, so neither survives a round trip through an EPP backend. The EPP Compatibility Profile should say how a server reads back a localization.
- **Proxy:** accepts `language` and any tag and stores neither. A read uses the key `und`, and returns only the members that differ from the internationalized form.
- EPP needs a complete `loc`, so a partial localization inherits the rest and reads back without it.
- A read of a contact with only a `loc` form has no internationalized form, only `localizations`, which the profile does not foresee.

## Localized and additional entries the EPP mapping cannot hold

- The profile allows a localized email, `email-1`, `voice-1` and `fax-1`. RFC 5733 has one email, one voice and one fax number, none of them per postalInfo.
- **Proxy:** 501 (`02102`), as for `links` and more than 3 street lines. More than one localization is a 501 too. The profile only says to reject it, without a result code.

## Card in the JSON draft

- json §6.2.9 still has `addresses[*].full` and open `features`, and does not reference the profile. It should follow profile -02.
- **Proxy:** follows the profile.

## Individual contact with an organisation

- The contact example (json §8.2.2) is `kind: individual` with `organizations`. EPP has one `postalInfo` with `name` and `org`, but no kind, so the kind cannot survive a round trip through an EPP backend.
- **Proxy:** 501 (`02102`). The draft example is tested as such in `draft_contact/test2`, and without `organizations` in `test3`.
- A read derives `kind` from the organisation, so a PATCH that removes the organisation would leave `kind: org` without one, which a create refuses. Unless the patch names `/contactInfo/kind` or replaces `/contactInfo`, the kind of the patched contact is derived again from its end state (`org` with an organisation, `individual` without), so `remove /contactInfo/organizations/org` and `add /contactInfo/organizations` need no `kind` operation. A PUT follows create: `kind: org` without an organisation is 400 (`02001`).

## Length of contact fields

- RFC 5733 limits `name`, `org`, `street` and `city` to 255 characters and `pc` to 16. The RPP schema has no `maxLength` on the matching JSContact fields, and the drafts only touch on size: data-objects §2.1.1 says usages "MAY impose" a maximum length, and §7 of the profile says servers "should impose appropriate limits". So a value can be valid RPP and not fit EPP.
- Should length be limited at all, or left to server policy? Should the EPP Compatibility Profile state the RFC 5733 limits, so the schema can enforce them?
- If it is server policy, which result code does a value over the limit get, and may a client discover the limit? May a server shorten a value, or must it reject it?
- **Proxy:** does not check these lengths. The test backend cuts the value and answers `1000` (pawel-kow/epp#21), so a 300-character `name.full` is a 201 and reads back as 255. A correct EPP server would reject it.

## Contact labels

- `contacts[].label` is an open string. EPP has `admin`, `billing` and `tech`. Are the values registered anywhere, or are they profile-defined?
- **Proxy:** other labels are 501 (`02102`).

## `match` on nested objects

- json §5.2.1 says the server MUST NOT match nested data structures, but its example matches `{"label": "tech", "object": {"@type": "contact", "id": "REG-200"}}`.
- **Proxy:** follows the example, EPP needs the role and the id to remove a contact.

## JSON Patch without a read

- §5.2.2 requires an error when no element matches, and step 6 validates the resulting object. A proxy that translates operations to EPP add/rem/chg has no resulting object. Result codes for patch failures are not defined either (no match, ambiguous match, create-only path).
- **Proxy:** no check before EPP. Non-patchable paths are 400 (`02001`).

## JSON Patch operations that need a read before the write

- EPP update is a delta (`add`, `rem`, `chg`) and has no "set". Some patch operations cannot become a delta without the current object: `replace` or `remove` of a whole array, `replace` with `match`, `remove` with a partial `match` (EPP `rem` needs the full value: role and id, host name and addresses, the whole DS), `/status`, `/dns`, and removal of `authInfo`.
- §5.2.2 says a partial update MUST be atomic. A proxy that reads, applies and then sends the diff is not atomic: another client can change the object in between, and the EPP update then fails or applies on a different state than the one that was patched.
- Open question for the EPP Compatibility Profile: must these operations be forbidden for an EPP backend (with a defined error), or may a server implement them with a read and a non-atomic write? If they are allowed, §5.2.2 needs an exception for atomicity, or the profile needs to say what the client gets when the object changed in between. If they are forbidden, the profile should list them, and name the result code, as `02102` is only a generic "not implemented".
- §5.2.2 requires an error when no element matches or when a `replace` with `match` is ambiguous, but defines no result code. The EPP Compatibility Profile should name one. 2308 (data management policy violation, 422) fits best, as the request is well formed but the object state does not allow it; 2303 would suggest the whole object is missing.
- Suggested: allow them, as OPTIONAL, and state that atomicity is only guaranteed for operations that map to a single EPP update.
- **Proxy:** no element matches and an ambiguous `replace` answer `02308` (422), with the index of the failed operation in the detail. Operations that map directly (`add` to an array, `remove` with a full `match`, `replace` of `registrant` and `authInfo`) are sent without a read, and a missing element is reported from the EPP error (2303, 2306), if the registry gives one: the test server accepts the removal of a host the domain does not have. Operations that need the current state read the object first (`info`), apply the patch, and send the diff in one EPP update. The read and the update are not atomic. The "no element matches" error is only exact for the reading path.

Example 1, `replace` of a whole array. The domain has `ns1.example.net` and `ns2.example.net`:

```json
[{"op": "replace", "path": "/nameservers", "value": [{"hostName": "ns3.example.net"}]}]
```

EPP has no "set", so the proxy reads the domain (`<domain:info>`), sees the two hosts, and sends:

```xml
<domain:update>
  <domain:name>example.example</domain:name>
  <domain:add><domain:ns><domain:hostObj>ns3.example.net</domain:hostObj></domain:ns></domain:add>
  <domain:rem><domain:ns>
    <domain:hostObj>ns1.example.net</domain:hostObj>
    <domain:hostObj>ns2.example.net</domain:hostObj>
  </domain:ns></domain:rem>
</domain:update>
```

Example 2, `remove` with a partial `match`. The domain has `tech` contacts `REG-200` and `REG-300`:

```json
[{"op": "remove", "path": "/contacts", "match": {"label": "tech"}}]
```

EPP `rem` needs role and id, so the proxy reads the domain and expands the match to every matching element:

```xml
<domain:rem>
  <domain:contact type="tech">REG-200</domain:contact>
  <domain:contact type="tech">REG-300</domain:contact>
</domain:rem>
```

Example 3, no atomicity. Client A sends example 1. Between the `info` and the `update`, client B adds `ns4.example.net`. The `update` is built from the old state and still succeeds, so `ns4.example.net` stays, and the result is not what A's patch would give when applied to the object (§5.2.2 step 6). If B had removed `ns2.example.net` instead, the `rem` would fail with 2303 and A would see an error for a patch that was valid when it was sent.

## Status in JSON Patch

- `status` has cardinality 1+ (data-objects §13.2) and Figure 3 of json §5.2.2 rejects `remove` of such a property, as step 6 rejects `replace` with an empty array. But the client owns only the client statuses, and the registry sets `ok` when none is left, so the resulting object is valid. A full update can clear them (core §16.8), so a client expects a patch to be able to.
- A `replace` of `/status` holds the whole array, but a client cannot set or remove server statuses. The draft does not say whether a server status left out of the value is an error, ignored, or has to be repeated.
- Should the EPP Compatibility Profile say that a patch of `status` covers only the statuses a client owns?
- **Proxy:** a patch of `/status` applies as if the object had no server statuses, on hosts, domains and contacts. `remove /status` and `replace /status []` clear the client statuses (a deviation from Figure 3), and server statuses are left alone. A value that names a server status is 400 (`02001`), even if the object has it, and a `match` that names one finds no element (422, `02308`). `ok` is the exception, it stays visible because the draft's example in §5.3.1 replaces it.

## `ok` in the partial update example

- json §5.3.1 changes a domain "from `ok` to `clientUpdateProhibited`" with a `replace` that matches `{"label": "ok"}`. Data-objects §9.3.1 and §9.4.1 say a client MUST NOT alter status values set by the server, and that `ok` is set and removed by the server.
- `ok` also cannot be combined with other statuses (§9.3.4, §9.4.4), so adding a client status is enough: the registry drops `ok` by itself. The `match` makes the patch fail on an object that has any other status instead of `ok`, although the client only wants to add its own status.
- Suggested: change the example to an `add` of `clientUpdateProhibited` on `/status`. If matching `ok` is meant to stay allowed, the draft should state it as an exception to §9.3.1.
- **Proxy:** follows the example, `ok` is the one server status a patch can see. The `replace` only adds the client status, and `ok` is left to the registry.

## EPP operations that RPP PATCH cannot express without a read by the client

- EPP changes one part of an element by `rem` and `add` of values the client names. JSON Patch has no such step: `match` does not reach nested data (§5.2.1), and `replace` takes the complete element. To change one address of a nameserver, one field of a DS, or a flag of a status, the client has to read the element and send it back whole, or use an index path (`/nameservers/1/addresses/0`), which needs the current array and shifts when someone else changes it. §5.2.2 step 2 does not say whether index paths are allowed.
- EPP `add` of a value that is already present, and `rem` of one that is not, are errors (2306, 2303). JSON Patch `add` without `match` only appends, and does not say whether a duplicate is an error. A client that wants "make sure X is present" or "make sure X is gone" has to read first, in EPP and in RPP alike. The draft has no conditional or idempotent form.
- EPP can `rem` and `add` the same value in one update, as long as the end state is valid. Patch operations run in order and step 6 only checks the end state, so this works; but a `replace` with `match` that must match exactly one element (§5.2.2) fails for a client that does not know whether there is a duplicate.
- The profile does not say which statuses a client may set. EPP rejects server statuses (`serverUpdateProhibited` and others), so a client cannot tell from the patch alone which `/status` entries to touch, and has to read the object to see which ones it owns.
- **Proxy:** none of these are handled specially. Index paths are a 400 (`02001`). The draft is not clear on whether they are allowed. A whole-element `replace` with `match` goes through the read path above.

Example 4, one part of an element. The domain uses `hostAttr` and `ns2.example.net` has addresses `192.0.2.1` and `192.0.2.2`. The client wants to change only the first address:

```json
[{"op": "replace", "path": "/nameservers/1/addresses/0/ip", "value": "192.0.2.9"}]
```

It must know that `ns2.example.net` is at index 1 and that the address is at index 0, which needs a read, and the indexes are wrong if the arrays change before the patch arrives. Without indexes, the only option is to replace the whole element, and the client has to send the other address as well:

```json
[{"op": "replace", "path": "/nameservers",
  "match": {"hostName": "ns2.example.net"},
  "value": {"hostName": "ns2.example.net",
            "addresses": [{"ip": "192.0.2.9", "version": "v4"}, {"ip": "192.0.2.2", "version": "v4"}]}}]
```

EPP can only do this as `rem` and `add` of the whole `hostAttr`:

```xml
<domain:add><domain:ns><domain:hostAttr>
  <domain:hostName>ns2.example.net</domain:hostName>
  <domain:hostAddr ip="v4">192.0.2.9</domain:hostAddr>
  <domain:hostAddr ip="v4">192.0.2.2</domain:hostAddr>
</domain:hostAttr></domain:ns></domain:add>
<domain:rem><domain:ns><domain:hostAttr>
  <domain:hostName>ns2.example.net</domain:hostName>
  <domain:hostAddr ip="v4">192.0.2.1</domain:hostAddr>
  <domain:hostAddr ip="v4">192.0.2.2</domain:hostAddr>
</domain:hostAttr></domain:ns></domain:rem>
```

Here the `rem` needs the old addresses too, so the proxy reads even for this whole-element `replace`.

Example 5, "ensure present". The client wants `ns3.example.net` to be a nameserver and does not know whether it is already one:

```json
[{"op": "add", "path": "/nameservers", "value": {"hostName": "ns3.example.net"}}]
```

If it is already one, EPP rejects the whole update (RFC 5731, result code 2306), while JSON Patch has no defined result for a duplicate:

```xml
<response><result code="2306">
  <msg>Parameter value policy error</msg>
  <extValue><reason>nameserver already associated with the domain</reason></extValue>
</result></response>
```

The "ensure gone" case is the same with `remove` and `match`, and EPP answers 2303. To avoid the error the client has to read the domain first, and then send the patch only if it is needed.

## Delete response

- Core §16.7 and json §8.1.6 show a 200 with a body, the OpenAPI says "output cardinality 0-1", and `domainName.read` requires `provMetadata` and `status`. EPP delete returns no object data.
- **Proxy:** 200 with an empty body.

## Pending operations and 202

- No operation defines a 202. Table 8 allows any 2xx for `x1yzz`, Table 10 says 200, Table 9 lists only `x1000`.
- **Proxy:** 200 with `01001`.
- A create or update that succeeded but could not be read back has no defined response (#23). **Proxy:** 202 without a body.

## Problem Details

- Core §9 says the document MUST contain `errors`, but lists it as optional. `status` must reflect the HTTP status, but is not in the field list.
- The error object `type` SHOULD be a URI identifying the error type, and no URIs are defined.
- **Proxy:** always sends `status` and one `errors` entry whose `type` is `urn:ietf:params:rpp:error`.

## Headers on rejected requests

- `RPP-Cltrid` MUST be echoed, and the OpenAPI marks it required on all responses, including the 400 for a missing `RPP-Cltrid`.
- `RPP-Svtrid` MUST be in every response. A request rejected before reaching the backend has no EPP svTRID.
- **Proxy:** omits `RPP-Cltrid` when the client did not send it, and generates a UUID for `RPP-Svtrid`.

## Repeated `RPP-Cltrid`

- Core §6.1 calls `RPP-Cltrid` an idempotency key "allowing the server to detect and safely handle duplicate requests", and says the value "MUST be unique per request". It does not say what the server answers to a duplicate, and §8 requires a redirected request to repeat the value "for the purpose of idempotency".
- An EPP backend can refuse a reused clTRID with `2400`, and Table 9 makes that 500 `02400`. A client retrying a create after a lost response gets a server error, even when the first attempt worked.
- Is an error the intended answer to a duplicate, or should the server replay the first response? If an error, which status and result code? A client mistake suggests 4xx, for example 409, rather than 500.
- Must a duplicate with a different body be treated differently from a true retry? How long must the server remember a value, and is the scope per client?
- **Proxy:** passes the EPP answer on, so a repeated value is 500 (`02400`) on the test backend (`host_availability/test6`). It detects no duplicates itself (#43).

## `authdata` in read responses

- json §6.2.7 says `authdata` MAY be omitted from read responses, but `authInfo.read` requires it.
- **Proxy:** returns `authInfo` only when the registry returned a password, and only when the request includes it, see "Visibility and `includeElements`".

## Visibility and `includeElements`

- Data-objects §2.4 gives `authInfo` of a domain and of a contact the Visibility `onDemand`: it is in the output only when the client names it in `includeElements` (§2.7.3). §2.4 also says Visibility "affects operation output only" and not what a client may send. Core §16.8 clears what a full update omits, so a client that PUTs back a read made without `includeElements=authInfo` would clear the password (see "Full update of a domain").
- **Proxy:** Visibility also decides whether an `onDemand` element is part of a full update. Without `includeElements` naming it, it is not part of the representation: a PUT leaves it as it is, and a PUT that sends it is a 400 (`02001`). With `includeElements` naming it, it is part of the representation like any other element: present is set, omitted is cleared. Every response that holds a domain, contact or host (create, read, PUT, PATCH) shows an `onDemand` element only when it is named. A PATCH is not affected, as each of its operations names what it changes. The `onDemand` elements are taken from `draft-ietf-rpp-data-objects.yaml`, which `copy_models.sh` copies with the contract, so nothing is specific to `authInfo`.
- Open question: is this what the draft intends? If Visibility should not affect input, the draft has to say what a full update does with an `onDemand` element the client did not read.
- Core §16.1.7 repeats an operation parameter once per value ("An operation parameter with a cardinality of 0+ or 1+ MUST be repeated"), while data-objects §2.7.3 defines `includeElements` with cardinality 0-1 as "a comma-separated list", and the OpenAPI follows that (one string, `explode: false`).
- **Proxy:** follows core: one Identifier per repeated `includeElements` (`?includeElements=authInfo&includeElements=status`). A value with a comma is one Identifier that no object has, so it is a 400 (`02001`), as is any Identifier that is not a top-level data element of the object (§2.7.3). The OpenAPI is left as generated.

## Undeclared properties

- json §4.9.1 requires schemas to be enriched with `unevaluatedProperties: false` before validation. The generated schemas and OpenAPI do not contain it.
- **Proxy:** `rpp_models` rejects undeclared properties with a 400.

## `authInfo` on create

- `authInfo` is optional in `domainName.create`, but EPP requires it, and the backend answers `2003` (400).
- **Proxy:** passes that through. Should the EPP Compatibility Profile make it required?

## Domain `dns` and EPP

- Nothing says how `dnsData` maps to EPP. Core §5 refers to a mapping document that does not exist yet ([TODO REF]).
- **Proxy:** on create, `ns` records and their glue are `ns.hostAttr`, `ds` and `dnskey` records are secDNS. `ns`, `ds` and `dnskey` must be owned by the domain, and `a` and `aaaa` by a nameserver given in the same request. Whether a nameserver outside the domain may have addresses is left to the registry: a read shows what the registry stores, so the proxy accepts the same records as input, on create, PUT and PATCH. Other records, and `ds` or `dnskey` below the domain, are 501 (`02102`). A read returns `ns.hostAttr` as `dns` and `ns.hostObj` as `nameservers`.
- A registry can store `hostAttr` as host objects, as the test backend does. The create then reads back as `nameservers`, and the glue is at `GET /hosts/{name}`.
- **Proxy:** a host is the same in both forms, whatever the case, so a PATCH or PUT with `ns` records of the hosts the domain has as host objects (and the reverse) changes nothing, which is what a repeated PUT does on such a registry. The addresses of a host object live on the host and cannot be compared, so a `hostAttr` with addresses over a host object (or the reverse) is a `rem` and an `add`. Current host attributes against wanted host objects are swapped whole when the set of names differs, or when any current host attribute has an address, all removed and all added, because EPP takes one form or the other and a registry that shows attributes stores them. The reverse, current host objects and wanted records with a partial overlap, only removes and adds the names that differ, because a registry that stores attributes as objects would refuse to add again a host that is still associated. A PUT that gives the delegation as records therefore needs a host with its own addresses to be an exact repeat, or the glue is sent again each time.

## DNSSEC with `nameservers`

- Data-objects §11.2 forbids `nameservers` together with DNS Data entries, without excepting `ds` and `dnskey`. Read literally, a domain delegated through host objects cannot have DNSSEC, and a client has to give its delegation as `ns` records. Should the rule be limited to `ns`, `a` and `aaaa`?
- **Proxy:** a create with `nameservers` and any `dns` record is a 400, while PATCH and PUT reject only `ns` records and their glue (`a`, `aaaa`) with `nameservers`. A read of such a domain returns both, because it would otherwise lose data, and a full replacement of an existing object has to be able to express what a read returns. A PUT that omits `dns` removes the DNSSEC data, so a domain with host objects and a DS has to be sent with both. A glue record (`a`, `aaaa`) counts as an `ns` record here, so `nameservers` with glue is a 400 as well.

## `ds` with `dnskey`

- Data-objects §9.9.1 has a TBC on `keyData` inside `dsData`, and §9.11 lets a client send both record types. RFC 5910 has a DS and a key data interface, and a server uses one.
- **Proxy:** both in one request are 501 (`02102`). A read leaves out a `keyData` nested in a `dsData`.
- A server using the DS interface can refuse `dnskey` (2306, as the test backend does), or derive a `ds` from it. The client then reads back another record type than it sent.

## IDN

- json §6.4 requires `lgr` whenever `uName` is present, and core EPP has no element for either. So `uName` cannot be computed from the A-label on read without breaking that rule.
- The EPP IDN extension (`urn:ietf:params:xml:ns:idn-1.0`, draft-obispo-epp-idn-04) carries an IDN table id (`de`) chosen by the registry, json §6.4 an LGR name from the IANA IDN tables registry (`latn-1.0`). Neither draft says how one maps to the other.
- The extension adds nothing to check, so core's availability example with `uName` and `lgr` cannot be expressed in EPP.
- draft-obispo-epp-idn-04 asks for 2005 when `uname` does not map to the name. The test backend answers 2306.
- **Proxy:** `lgr` is the IDN table through the configured map `rpp_idn_lgr_tables` (LGR name to table id, one to one), `uName` is `idn:uname`. On create, an `lgr` not in the map, or a `uName` without `lgr`, is a 400 (`02001`). An `xn--` name without `lgr` goes to the server, which may refuse it. A server that does not offer the extension gives 501 (`02103`). A read gives `uName` and `lgr` from the Info reply, and leaves both out, with a warning in the log, when the table is not in the map. PUT and PATCH cannot change them (`domainName.update`). Availability with `uName` or `lgr` is 501 (`02102`), and an A-label alone is checked as any name.

## Disclose

- The Disclose Object is TBD in data-objects §9.13, and `disclose.read` has only `@type`.
- **Proxy:** 501 (`02102`) (#59).

## Host DNS records

- The EPP Compatibility Profile (data-objects §13.2) limits the entries of `dns` to A and AAAA, but the host examples (json §8.3.2 to §8.3.4) include an `ns` record.
- The same section allows entries subordinate to the host name, but EPP has one address list per host, so a record for another name has no place in EPP.
- A record of the host can name its owner in two forms, `@` and the absolute name, and the examples (json §8.3.2 to §8.3.4) use both in one `records` array: `@` for the `ns` record, `ns1.example.example.` for the addresses. A `match` on `name` then depends on which form the server returns, and a host rename (data-objects §13.3.4) leaves every record with an absolute name pointing at the old name, while `@` follows the host.
- Suggested: allow only one form for the records of a host, preferably `@`, which also survives a rename. Otherwise the draft should say whether a server normalizes the name, and which name applies in a patch that renames the host.
- **Proxy:** a patch that renames the host and changes records in one request takes `@` or the old name, and a record under the new name answers 501 (`02102`). A read emits both forms, as the examples do.
- **Proxy:** follows the examples. An `ns` record is accepted only as the self-reference (`@` with the host as `nsdname`), and A and AAAA records must name the host itself (`@` or its name), anything else is 501 (`02102`). A read always emits the `ns` record, plus A and AAAA records when the host has addresses.

### The own `ns` record of a host

- A host object represents its name implicitly, so EPP has nothing to store for the self-referencing `ns` record. The examples (json §8.3.2 to §8.3.4) show it, but the drafts do not say whether it is data of the object, or whether a client may omit or remove it.
- Is the following intended, or at least acceptable? A record that is required on input and carries no information makes a client state what the server already knows. It also goes beyond the drafts: `dns` has cardinality 0-1 (data-objects §13.2), §13.3.2 lets an external host omit its addresses, and `host.create` and `host.update` require only `@type` and `hostName`. If the record is not meant to be mandatory, the EPP Compatibility Profile should say so, and the examples should drop it or mark it as server-generated.
- **Proxy:** the record is mandatory and never reaches EPP:
  - A create or PUT without it is a 400 (`02001`), also with no `dns` at all, so `{"@type": "host", "hostName": "..."}` is rejected. A PUT that renames the host gives it with the new name. The checks of the rest of the request come first, so a request that is 501 for another reason stays a 501.
  - A patch that leaves a host without it is a 501 (`02102`): `remove` with a `match` that hits it, `remove` or `replace` of the whole `/dns/records`, `remove` or `replace` of `/dns`. A client clears the addresses by removing the `a` and `aaaa` records. Removing it and adding it back in one patch is allowed, as only the end state counts (§5.2.2 step 6).
  - `add` of it is dropped without a read. A patch with nothing else becomes an empty EPP update, and the backend answers `2003` (400), as for an empty patch.

## Data the EPP Compatibility Profile cannot hold

- The host create example (json §8.3.2) has `dns.controls.ttl`, which core EPP has no element for (RFC 9803 adds one), and the data-objects draft does not limit `controls` in the EPP Compatibility Profile. An example the profile cannot carry leaves open what a server should do: reject it, ignore it, or apply a default. Should the profile forbid `controls`, and with which result code?
- **Proxy:** `ttl` is 501 (`02103`), because the proxy does not implement RFC 9803, on hosts and domains, so the §8.3.2 example answers 501 as written (`draft_host/test2`). `maxSigLifetime` is 501 (`02102`), and a read leaves out the secDNS `maxSigLife`. Nothing is dropped silently.

## `status` on host create

- `status` is read-write on a host, and `host.create` accepts `clientDeleteProhibited` and `clientUpdateProhibited`. EPP `<host:create>` has no status element, so honouring it takes a create and an update, which is not atomic. Should the EPP Compatibility Profile exclude `status` from create?
- The same applies to domain create.
- **Proxy:** 501 (`02102`).

## Full update of a domain

- Core §16.8 clears what a PUT omits, "subject to server policy". Data-objects §11.3.4 says the Authorisation Information MAY be removed, and json §4.9.3 says a client MUST NOT send `authInfo` in a request body and a server MUST reject it. Yet `domainName.create` and `domainName.update` both carry `authInfo`, and a read can return it (see `authdata` in read responses). A client that follows §4.9.3 and PUTs back what it read would wipe the password on every PUT.
- **Proxy:** `authInfo` is part of a PUT only when the request includes it (`includeElements=authInfo`), see "Visibility and `includeElements`". Then it is compared like any other member: a password that differs from the one the registry shows is set (EPP `chg`), one that is the same changes nothing, and an omitted one removes the stored one (`domain:null`). A registry that does not show the password makes every password differ, so it is sent. Without it the password is left alone, and a body with `authInfo` is a 400 (`02001`). §4.9.3 is not applied to `authInfo` in the body, as on create.
- Json §4.4 requires a server to reject a data element that is not allowed in a request, and `status` accepts only client statuses (`domainStatus.create`).
- **Proxy:** a PUT with a member outside `domainName.update` (`name`, `provMetadata`, `expiryDate`, `subordinateHosts`, `uName`, `lgr`, `processes`) is a 400 (`02001`), and so is `ok` or another server status in `status`, unlike a PATCH, which accepts `ok` (see the `ok` entry). `status` is a set: client statuses not listed are removed (an omitted `status` removes them all), a changed reason is a remove and an add, and server statuses stay. The path name is the only identity. The registry sets `ok` when no status is left. A `due` date has no place in EPP and is 501 (`02102`), on a PUT and a PATCH. A domain read now carries the status `reason` when the registry gives one (the test backend does not), so a PUT or PATCH with the same reason changes nothing and one without it drops it. A member the schema does not declare is a 400 at any depth.
- A full update has no EPP command, so the proxy reads the domain, takes the difference and sends one update, as for a PATCH that needs the current state. The read and the update are not atomic. The `dns` and `nameservers` checks of a create apply (`ttl` 501, `ds` with `dnskey` 501), except as in "DNSSEC with `nameservers`". They apply to the request as it is, also where it repeats what the domain has.

## Full update of a contact

- Core §16.8 clears what a PUT omits, "subject to server policy", but the json §8.2.4 example omits `name` and `organizations` and its response keeps both, with `kind: individual` and an organisation (which a create refuses, see above). EPP can clear the organisation, `voice` and `fax` (an empty element), but not the `name`, the address (`city` and `cc` are required), the email, or a `postalInfo` form: RFC 5733 has no element to remove one. Data-objects §12.3.4 does not say what a PUT does with them.
- **Proxy:** a PUT is the wanted state: after it, the read-write members of the contact are those of the request. An omitted `organizations`, `voice` or `fax` is cleared (the example's response differs here). An omitted `name`, address, email or localization asks to clear what EPP cannot clear, so it is 501 (`02102`), as is a PATCH that removes one of them, and clearing the name or address of a localization. The json §8.2.4 example omits `name`, so it is 501 (`draft_contact/test5`). An address that is sent replaces the whole address, so an omitted region or postcode is cleared. A localization the read shows in part (the members equal to the card are left out) is not rewritten from that read: a PUT or PATCH that repeats it leaves the stored form alone, unless it is equal to the card, which reads back as none and follows the card when that changes.
- Each `postalInfo` form that differs is sent complete, as the test backend replaces a form on a `chg` and wipes the address members that are not sent again. A `chg` of a form the contact does not have is ignored by that backend, which still answers 1000 (pawel-kow/epp#23), and RFC 5733 does not say what a server must do.
- **Proxy:** after the read-back the proxy compares which forms exist, on the contact model (an invisible localization counts), and a form that the update added and that the registry still lacks is a 500 (`02400`) naming the form, because the registry reported success and does not hold the data, and the client did nothing wrong. The fields of a form are not compared, as the registry may normalise or cut them. The update is not split, so the other members of the same update may already be applied, and the proxy cannot undo that. A correct registry adds the form, so nothing is refused up front.
- Data-objects §12.3.4 says the Authorisation Information MAY be changed, not removed, and RFC 5733 has no null element for a contact's `authInfo`, unlike domains. **Proxy:** `remove /authInfo` is 501 (`02102`), and so is a PUT that includes `authInfo` (`includeElements=authInfo`) and omits it. Otherwise as for domains: without `includeElements=authInfo` the password is left alone, and with it a present one replaces it.
- `disclose` is 501 (`02102`), as on create. An omitted `disclose` is left alone, because a read does not show it.
- Statuses are as for domains: a set of the client statuses, compared by label, a changed reason is a remove and an add, `due` is 501, a server status is 400. The registry's `ok` is not a client status. A member outside `contact.update` (`id`, `provMetadata`, `processes`) is 400 (`02001`), at any depth.
- A PATCH of `status` and `authInfo`, and an `add` or `replace` of the voice or fax phone or of the email (an entry, or its `number` or `address`), is sent without a read: EPP holds one value each, which `chg` sets. Such an operation is checked as the same entry in a full update. A `replace` of a phone or email the contact does not have therefore sets it, where RFC 6902 asks for an error. Removing one, and every other operation on `contactInfo`, reads the contact first, applies the patch to it, and sends the difference in one update, so that removing what is not there stays a 422. The read and the update are not atomic. No element matches is 422 (`02308`) only on the read path, see the entry "JSON Patch operations that need a read before the write": a direct operation, such as the removal of a status the contact does not have, is sent, and the test backend accepts it. Two operations on one status label are not sent together, as their order would be lost, so they take the read path.
- A PUT that changes nothing is a 200 with the current contact and no EPP update, and 403 (`02201`) for a client that is not the sponsor, as for domains.

## Host transfer

- Data-objects §13.4 gives the host a Transfer Process and the OpenAPI has the operations. RFC 5732 defines no host transfer: subordinate hosts move with their domain, and data-objects §11.4.2 disallows anything that breaks that relationship.
- **Proxy:** 501 (`02101`).

## Full update without a change

- A host update must provide at least one change (data-objects §13.3.4), but a PUT repeating the stored state is a valid full update (core §16.8) and PUT is idempotent in HTTP.
- Data-objects §11.3.4 has the same "at least one change" rule for domains, while core §16.8 requires a 200 with the object.
- **Proxy:** a domain, contact or host PUT that changes nothing is a 200 with the current object and no EPP update, as is a PATCH that changes nothing, unless the client is not the sponsor (the `clID` of the read differs from the session's): then it is 403 (`02201`), because no EPP command runs to refuse it. The login id is assumed to equal the `clID` of the object, compared without regard to case.

## Transfer process

- `GET .../transferProcesses/latest` with nothing pending gets EPP `2301`. Table 9 maps `02301` to 409, but the OpenAPI has no 409 on that GET, and core §16.9.5.2 says the resource "may not exist", which suggests 404 (#68).
- **Proxy:** 409 (`02301`).
- Core §16.9.5.5 shows approve with no content and the OpenAPI declares no `requestBody`, but json §8.1.10 sends `{"@type": "domainTransferProcess"}`.
- **Proxy:** accepts both. Approve reads its body like reject does: `reason` is 501 (`02102`), anything else the schema does not allow is 400 (`02001`), and nothing is sent to EPP, because an approval cannot be undone.
- Json §8.2.9 gives an example with `reason`, which data-objects §10.1.1.5 forbids in the EPP Compatibility Profile, without naming the rejection.
- **Proxy:** 501 (`02102`).
- EPP has no process ids and no transfer history, so the list and `/{processId}` operations have nothing to map to.
- **Proxy:** 501 (`02101`), and responses have no `processId`.
- EPP has no push transfer, and its response does not say the direction.
- **Proxy:** `transferDir: push` and `gainingClientId` are 501 (`02102`), and responses always have `transferDir: pull`.
- Contacts use the same mapping as domains (core §16.9.5, json §8.2.6 to §8.2.9) with `@type` `transferProcess`. RFC 5733 has no period and `contact:trnData` no expiry date, so a contact has neither, and a `transferPeriod` in a contact request is not in the schema (json §4.4).
- **Proxy:** `transferPeriod` on a contact is 400 (`02001`). Json §8.2.9's reject example has `reason`, so the draft's own example is 501 (`02102`) and `draft_contact/test11` expects that.
- The OpenAPI declares no 501 on the transfer operations, which the proxy answers for list, `/{processId}`, push, `gainingClientId` and `reason`.
- `RPP-Authorization` can accompany query, cancel, approve and reject too. RFC 5730 §2.9.3.4 says authorization information MUST be provided to complete a transfer command, and RFC 5733 §3.2.4 gives `contact:authInfo` for every `op` without saying a server ignores it on any of them.
- **Proxy:** forwards it on every operation. EPP has a place for it, so nothing is dropped, and refusing it would change the domain wire.

## Renew process

- Json §8.1.7 and data-objects §10.3 make `expiryDate` optional, and call it the client's guard against duplicate renewals. EPP requires `curExpDate` (RFC 5731 §3.2.3), as an `xs:date`.
- **Proxy:** without `expiryDate` it reads the domain and uses the date of its `exDate`. The read and the renew are not atomic, and the client gave up the guard, so a client that retries without `expiryDate` after a lost response renews twice (see "Repeated `RPP-Cltrid`"). With `expiryDate` it sends no read.
- EPP holds only a date, so the time of day of `expiryDate` has no element. The json §8.1.7 example has `22:00:00Z`.
- **Proxy:** sends the date in UTC, after converting any offset, and does not check the time. A date that does not match is EPP's `2306`, so 422.
- Core §16.9.4 shows a 201 with a `Location`, which assumes an exposed process resource. EPP has no process, and the OpenAPI has no `latest` or `{processId}` path for renew. Core §16.1.4 requires a 200 from a server without a persistent process resource.
- **Proxy:** 200, no `Location`, no `processId`. The body is `@type` and the new `expiryDate` from `renData`, with no `renewalPeriod` (EPP does not echo it). A `1001` is a 200 with `01001` and no `expiryDate`, as is a `1000` without `renData`.
- Data-objects §10.3 allows the period to default by server policy.
- **Proxy:** sends no `period` when `renewalPeriod` is absent, and leaves the default to the registry. The test backend answers `1000` without extending the expiry (pawel-kow/epp#25).
- EPP's renew (RFC 5731 §3.2.3) has no authInfo, so an `RPP-Authorization` header on a renew has nowhere to go.
- **Proxy:** 501 (`02102`).
- A `1001` has not completed, and data-objects §10.3 ties the new expiry date to a completed renewal.
- **Proxy:** `expiryDate` is left out of a `1001`, even when the registry sends `renData`.
- `expiryDate` must be an RFC 3339 date-time. The schema `format` is not enforced (json §4.9.1's `unevaluatedProperties` is a separate gap, see "Undeclared properties").
- **Proxy:** checks the RFC 3339 §5.6 form itself, with `T` and `Z` in either case. A leap second (`:60`) is a 400.
- EPP has no process list or process ids.
- **Proxy:** `GET .../renewProcesses` is 501 (`02101`).

## Restore process

- Core §16.9.3 and json §8.1.13 to §8.1.15 restore any object in the Redemption Grace Period, and json §8.3.6 to §8.3.8 give host examples. RFC 3915 defines RGP for domains only, and the OpenAPI has no host restore path.
- **Proxy:** domains only. A host restore path answers 404, as for any path the OpenAPI does not have.
- Core §16.9.3 shows a 201 with a `Location`, which assumes an exposed process resource. EPP has no restore process and no process ids.
- **Proxy:** a request and a report are a 200 without `Location` and without `processId`, as for renew (core §16.1.4). The list and `/{processId}` operations are 501 (`02101`).
- Json §8.1.13 allows a restore request with an inline report that restores the object at once. RFC 3915 restores in two commands, a request and then a report.
- **Proxy:** a `restoreReport` in a POST is 501 (`02102`). The proxy does not send the two commands for it.
- Json §6.2.10 makes only `@type` and `statements` (one or two) required, `restoreTime` and exactly two statements in the EPP Compatibility Profile. RFC 3915 §4.2.5 requires `preData`, `postData`, `delTime`, `resTime`, `resReason` and two statements.
- **Proxy:** a report missing any of `preData`, `postData`, `deleteTime`, `restoreTime` and `restoreReason`, or without exactly two statements, is 400 (`02001`). `deleteTime` and `restoreTime` must be RFC 3339 date-times.
- EPP returns neither the dates of the restore process (`requestDate`, `reportDate`, `reportDueDate`) nor the report.
- **Proxy:** the body is `@type` and `restoreStatus` alone. After a request it is the `rgp:upData` status, `pendingRestore` without one. After a report it is the `rgp:upData` status, `restored` for a `1000` without one, `pendingRestore` for a `1001`.
- A PATCH of a restore process has no stored report to apply to.
- **Proxy:** applies the patch to `{"@type": "restoreProcess"}` and sends the result as a report, so a `remove` is 422 (`02308`).
- EPP has no restore query. The RGP statuses of a domain Info (RFC 3915 §4.1.2) cannot tell a restored domain from one that was never deleted.
- **Proxy:** `GET .../restoreProcesses/latest` reads the domain: `pendingRestore` is `pendingRestore`, `pendingDelete` is `rgpPendingDelete`, and anything else is 404 (`02303`), so `restored` is never read.
- **Proxy:** the proxy logs in with `urn:ietf:params:xml:ns:rgp-1.0` when the server offers it. Without it every restore operation is 501 (`02103`). The RGP statuses are not yet part of the domain's `status` (#105).

## Discovery

- Core §11 and data-objects §17.3.1 require the document without authentication. The drafts give no caching rule, and `datetime` is the current time, so a cached document goes stale.
- Json §6.10 and data-objects §17.2 say the same about `objects`: each value MUST be a valid object identifier of the RPP Data Object Registry. In data-objects §17.2 that rule sits in a stray description and constraint after Notices, detached from `Objects`, whose own constraint says "(None)". The description of `Objects` ("The list of identifiers of data objects supported by the server") covers `message`, which is not a provisioning object, so it is unclear whether `message` belongs in `objects` (#99).
- Json §5.2.1 shows `idnLgr` elements without `url` and `default`, which `discoveryIdnLgr.read` requires.
- No RPP extension identifier exists for secDNS, so `extensions` has nothing true to say about DNSSEC.
- Core §12.4 says the server MUST provide its supported profiles in `profiles`, and json §8.7.1 shows `urn:ietf:params:rpp:profile:epp-compatibility`, and data-objects §2.8 defines the EPP Compatibility Profile. Data-objects §19.13 only creates the RPP Profiles registry, with that URN as an example, so the draft registers no profile name. `GET /profiles/{name}` is still 501, and the proxy does not process the profile parameters of a client (core §14.2, §14.3), so a client can read the name in discovery but not the profile. Core §14.2 requires an error for an unsupported profile, while `RPP-Profile: profile=urn:bogus;version=9.9` gives 200 (#41). Core §12.4 tells clients to use the profile "version information", but discovery `profiles` is a list of strings with no version.
- `links` is omitted because the proxy has no such documents. Data-objects §17.2 only says a server SHOULD provide privacy-policy and terms-of-service links.
- The 400 without `RPP-Cltrid` follows core §6.1 and the OpenAPI, but sits awkwardly with data-objects §17.3.1 ("Input: (None)") and an anonymous read.
- **Proxy:** answers 200 from configuration and constants, without EPP: `versions` (`1.0`), `environment`, `tlds`, `profiles` (`epp-compatibility`), `objects` (`domainName`, `host`, `contact`) and `datetime`. It omits `extensions`, `links`, `idnLgr` and `notices`, and sends no `Cache-Control`. The media type is not negotiated (#41): `version` is ignored and `Accept` is not checked. Configuration that is missing or of the wrong shape, or a base URL that is not `https`, is 500 (`02400`) (#38).

## Messages

- Core §16.10.1 says the messages endpoint retrieves "exactly one message", while the OpenAPI and json §6.8.3 define an array, and nothing says what an empty queue returns. EPP answers `1300`, which Table 10 maps to 200.
- **Proxy:** follows the schema: an array with the one message, and `[]` for an empty queue, with `RPP-Code` `01300` and `RPP-Queue-Size: 0`.
- The core has no read-by-id section, although the OpenAPI has `messages_read`. EPP cannot read past the head of the queue, so a queued message that is not the head, an acknowledged one and an unknown one look the same.
- **Proxy:** a read of the head id is 200. An empty queue is 404 (`02303`), any other id is 501 (`02102`). The backend answers an ack of an unknown id with `2303`, so that DELETE is 404.
- Data-objects §9.19.1 and §9.19.3 (and §9.19.4) give the transfer messages no member for the human-readable text that the EPP `msg` carries, only the review response (`message`) and the service notice have one.
- **Proxy:** the `msg` text of a transfer message is not returned. It is generated from the structured data. `Content-Language` is the `lang` of the EPP `msg`.
- EPP can send messages RPP has no type for: no `resData`, other object data, several `resData` elements, an `extension`, markup in `msg` with attributes, and `qDate` is optional in EPP while `creationDate` is required in RPP.
- **Proxy:** such a message, any message whose mapping fails the `.read` schema (for example a `paTRID` without `svTRID`, a `paResult` that is no boolean, or an object without a name or id, which data-objects §9.19.1 forbids), and any reply that does not follow the EPP schema (an unknown child, a repeated element, a non-namespaced `resData` element, a `qDate` that is no date, no `trID`), is a `serviceNoticeMessage` with the `msg` text and a sentence naming the elements (never their content, which is not logged either). It can still be read and acknowledged, and is never a 500. For a reply that does not follow the schema the typed data is not read at all. A result code the proxy has no name for keeps its number (core §18.1: a code not in Table 9 uses Table 10, `RPP-Code` is the EPP code with a leading 0, the status comes from the class), with its `msg` and svTRID. A reply with no readable result code, also an ack's, is a 500 (`02400`).
- **Proxy:** a missing or unreadable `qDate` becomes the `reDate` of a transfer, the `paDate` of a pending-action reply, else the time of the read, so without a `qDate` a notice can show another `creationDate` on each read.
- **Proxy, the one exception:** a `1301` without `msgQ`, without an `id` or with an empty one cannot be acknowledged, and claiming an empty queue would hide it. It is a 500 (`02400`) with a fixed detail, and is logged.
- `RPP-Queue-Size` is a MAY in core §6.2. **Proxy:** sent on the messages operations only, from `msgQ/@count` (0 on `1300`), also on the 404 and 501 of a read, and omitted when an ack reply has no `msgQ` or the count is not an integer of at least 0. `type` is ignored (core §16.10.1, EPP Compatibility Profile), `status` is always `queued`, and `process` has no `processId`.
- **Proxy:** `Content-Language` is the `lang` of the EPP `msg`, `en` when the attribute is absent (the EPP default), and omitted when there is no `msg` or the value is no language tag. A message id that XML 1.0 cannot hold (a control character other than tab, line feed and carriage return, a lone surrogate, U+FFFE or U+FFFF) is 400 (`02005`) on GET and DELETE, before anything reaches EPP. A line feed in the path id (`%0A`, also `/hosts/a%0Ab`) is a framework-level 500 before the handler (#98), so a message whose id has a line feed can be read but not acknowledged. An id sent by the server is logged with `%r`, so it cannot add a log line. Comments in an EPP reply are removed before typed parsing, and a reply that is not well-formed (`<msg>a & b</msg>`, trailing junk) fails typed parsing on every operation, where lxml's `recover` repaired it before. For messages that is the notice path.
- Only the server creates messages (data-objects §15.3.1), and EPP has no command for it.
- **Proxy:** `POST /messages` is 501 (`02101`), after the body is validated, so the json §8.6.1 example answers 501 (`draft_message/test1`).
