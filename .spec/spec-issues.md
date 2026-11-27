# Spec issues

Points in the RPP drafts that could not be implemented, or where the intended behaviour is unclear.
Each entry says what the proxy does today.

## Phone numbers

- The JSContact profile -02 requires `tel:+CC.number`, but the `contactInfo` examples (json §8.2) still use `tel:+1-703-555-5555`, which the profile rejects.
- **Proxy:** follows the profile, anything else is a 400. `;ext=` maps to EPP `x`. The tests based on json §8.2 use the profile form.
- A registry may hold numbers in another format: DENIC RRI gives the phone and fax numbers of a RegAcc in E.123 (`\+[/\-\.\s0-9x]{1,254}`, [rri-5.0-reference.md](../docs/rri/rri-5.0-reference.md) §3.6), without the `.` after the country code. The profile's format applies to what a server returns as well, and says nothing of a number that a server reads from such a registry.
- **Proxy (RRI):** an organisation read takes the digits before the first separator as the country code, and leaves out a number that does not give an rpp-telephone-uri.

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
- Profile §4.1.10 defines additional keys (`-1`, `-2`) for `emails` and `phones` only. A registry may hold several URLs, as DENIC RRI does for a RegAcc (`regacc:url`, 0 to n in the XSD, 0 to 1 in its documentation).
- **Proxy (RRI):** an organisation read gives the first URL as `url`. The Card of the drafts (`RecordLink`) has no `url-1`, so further URLs are left out, and logged by the name of the field.

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

## Case sensitivity of names and identifiers

- The drafts do not specify clearly which values are compared with regard to case. Data-objects §2.1.11 says two FQDNs are compared without regard to case and the server generates them in lower case. json §5.2.1 says a primitive in a `match` matches when it has "the same type and the same value", without saying whether "the same value" follows the data type of the element (an FQDN) or is plain string equality. json §10 makes clients lowercase `name` before they compare it, which suggests the latter.
- The Identifier (data-objects §7.1) and the Client Identifier (§7.2) refer to RFC 5730 §2.8 and `clIDType`, which say nothing about case either. EPP servers differ: the test server reads host names and contact ids back in upper case (`NS1.EXAMPLE.NET`, `FO-0E6F867C-0UF1` for `fo-0e6f867c-0uf1`), others keep the case the client sent.
- Open questions: does a `match` compare an FQDN, an Identifier or a Client Identifier by the rules of its data type? Are identifiers case-sensitive, case-insensitive, or server policy, and if policy, how does a client find out? Must a server read back an identifier in the case it was created with?
- **Proxy:** where it applies a patch to the object it read, a `match` compares `hostName` in `/nameservers` and the contact `id` in `/contacts` without regard to case (#234), and every other value exactly. A PUT and the difference it sends to EPP compare host names and contact ids without regard to case, and the sponsor's login id with the `clID` too. A read passes on the case the registry returns.

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
- `expiryDate` must be an RFC 3339 date-time (the schema's `format`).
- **Proxy:** checks the schema's `format` (#233) and the RFC 3339 §5.6 form itself, with `T` and `Z` in either case. A leap second (`:60`) is a 400.
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

## Sponsor of a deleted domain

- Data-objects requires `provMetadata.spClientId` in every read of a domain. DENIC RRI shows no RegAcc for a domain in
  its redemption period (status `redemptionPeriod`), whoever reads it, so a registry may hold an object whose sponsor it
  does not disclose.
- **Proxy:** such a domain reads with what RRI shows (`name`, status `pendingDelete`, `upDate`) and `spClientId`
  `unknown`, a placeholder, until RPP lets a read leave the sponsor out.

## Organisation read from registrar data

- An Organisation Data Object read from a registry that holds no organisation objects has data the drafts require and the registry does not hold. DENIC RRI regacc INFO ([rri-5.0-reference.md §6.19](../docs/rri/rri-5.0-reference.md#619-regacc-info)) gives a RegAcc's public contact data, but no status, no sponsor and no role.
- Data-objects §9.2 requires `provMetadata.spClientId`. A RegAcc maintains its own profile, in the registry's web interface, so no client sponsors it in the sense of §9.2.
- `parent` (data-objects §14.2) is an aggregation, but nothing says whether it must name an organisation the server can read. The member account of a RegAcc (`memberacc`) groups RegAccs and is not one, so regacc INFO may not find it.
- **Proxy (RRI):** `spClientId` is the RegAccId itself, `status` and the status of the role `registrar` are `ok`, and `parent` is the MemberAccId, unless it equals the RegAccId. Its read may be 404.

## Discovery

- Core §11 and data-objects §17.3.1 require the document without authentication. The drafts give no caching rule, and `datetime` is the current time, so a cached document goes stale.
- Json §6.10 and data-objects §17.2 say the same about `objects`: each value MUST be a valid object identifier of the RPP Data Object Registry. In data-objects §17.2 that rule sits in a stray description and constraint after Notices, detached from `Objects`, whose own constraint says "(None)". The description of `Objects` ("The list of identifiers of data objects supported by the server") covers `message`, which is not a provisioning object, so it is unclear whether `message` belongs in `objects` (#99).
- Json §5.2.1 shows `idnLgr` elements without `url` and `default`, which `discoveryIdnLgr.read` requires.
- No RPP extension identifier exists for secDNS, so `extensions` has nothing true to say about DNSSEC.
- Core §12.4 says the server MUST provide its supported profiles in `profiles`, and json §8.7.1 shows `urn:ietf:params:rpp:profile:epp-compatibility`, and data-objects §2.8 defines the EPP Compatibility Profile. Data-objects §19.13 only creates the RPP Profiles registry, with that URN as an example, so the draft registers no profile name. `GET /profiles/{name}` is still 501, and the proxy does not process the profile parameters of a client (core §14.2, §14.3), so a client can read the name in discovery but not the profile. Core §14.2 requires an error for an unsupported profile, while `RPP-Profile: profile=urn:bogus;version=9.9` gives 200 (#41). Core §12.4 tells clients to use the profile "version information", but discovery `profiles` is a list of strings with no version.
- `links` is omitted because the proxy has no such documents. Data-objects §17.2 only says a server SHOULD provide privacy-policy and terms-of-service links.
- The 400 without `RPP-Cltrid` follows core §6.1 and the OpenAPI, but sits awkwardly with data-objects §17.3.1 ("Input: (None)") and an anonymous read.
- **Proxy:** answers 200 from configuration, constants and the backend's profile, without EPP: `versions` (`1.0`), `environment`, `tlds`, `profiles` (`epp-compatibility`), `objects` and `datetime`. `objects` holds the data objects of the backend (`domainName`, `host` and `contact` on EPP, `domainName`, `contact` and `organisation` on RRI), `message` on both, read as covered by the description of `Objects`, and the data objects of the extensions offered (`requestContact`). `extensions` lists the extensions of the offered presets. It omits `links`, `idnLgr` and `notices`, and sends no `Cache-Control`. The media type is not negotiated (#41): `version` is ignored and `Accept` is not checked. Configuration that is missing or of the wrong shape, or a base URL that is not `https`, is 500 (`02400`) (#38).

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
- `RPP-Queue-Size` is a MAY in core §6.2. **Proxy:** sent on the messages operations only, from `msgQ/@count` (0 on `1300`), also on the 404 and 501 of a read, and omitted when an ack reply has no `msgQ` or the count is not an integer of at least 0. `type` is ignored by the EPP backend (core §16.10.1, EPP Compatibility Profile; the RRI backend selects by it, see Message types of an extension), `status` is always `queued`, and `process` has no `processId`.
- **Proxy:** `Content-Language` is the `lang` of the EPP `msg`, `en` when the attribute is absent (the EPP default), and omitted when there is no `msg` or the value is no language tag. A message id that XML 1.0 cannot hold (a control character other than tab, line feed and carriage return, a lone surrogate, U+FFFE or U+FFFF) is 400 (`02005`) on GET and DELETE, before anything reaches EPP. A line feed in the path id (`%0A`, also `/hosts/a%0Ab`) is a framework-level 500 before the handler (#98), so a message whose id has a line feed can be read but not acknowledged. An id sent by the server is logged with `%r`, so it cannot add a log line. Comments in an EPP reply are removed before typed parsing, and a reply that is not well-formed (`<msg>a & b</msg>`, trailing junk) fails typed parsing on every operation, where lxml's `recover` repaired it before. For messages that is the notice path.
- Only the server creates messages (data-objects §15.3.1), and EPP has no command for it.
- **Proxy:** `POST /messages` is 501 (`02101`), after the body is validated, so the json §8.6.1 example answers 501 (`draft_message/test1`).

## Identifier length and syntax

- Data-objects §7.1 says identifiers have "a specified minimum length, a specified maximum length" but gives neither. Json §6.1.1 prescribes RFC 5730 `roidType`, `^(\w|_){1,8}-\w{1,}$`, at most 89 characters. A contact id is a `clIDType` in EPP (RFC 5730 §2.8, 3 to 16 characters), and a DENIC handle (`DENIC-1000022-EXAMPLE`, up to 32) has a second hyphen, which `roidType` does not allow. Neither fits the json rule.
- Should the EPP Compatibility Profile say that a contact `id` is a `clIDType`, and leave other ids to server policy?
- **Proxy:** puts no constraint on `id` and passes it on, so the registry refuses an id it does not take (`limits_contact/test1` to `test4`).

## Limits of associations and status lists

- Data-objects gives no minimum or maximum for `nameservers`, `contacts` per label ("MAY be restricted by server policy"), holders, `dns.records` per type, or `status`, and does not say whether a status label given twice is one status or an error. EPP itself has none: servers set them (13 nameservers and 13 addresses a host on the EPP test server, 5 contacts a role; 2 to 13 name servers, 1 to 5 address records, 0 to 20 DNSKEY, 1 to 5 holders on DENIC).
- Which result code does a count over the limit get? It is a parameter value policy error (`2306`, 422) in EPP terms, but nothing says so.
- **Proxy:** passes counts on, except holders beyond `max_registrants`, which are 501 (`02102`) before anything is sent. `limits_domain/test15` expects 4xx for that, as for a limit of the registry.

## DNS record values

- Data-objects §9.9.1 names the `rdata` members of `ns`, `a`, `aaaa`, `ds` and `dnskey`, but not their ranges: `keyTag` 0 to 65535, `algorithm` and `digestType` 0 to 255, the digest length a digest type implies, `flags`, `protocol`. A server may take `mx` as a parent-side record (DENIC does), and the drafts have no `rdata` structure for it.
- `dnsControls` `ttl` and `maxSigLifetime` have a minimum of 1 and no maximum (RFC 5910 `maxSigLife` is an int).
- **Proxy:** `mx` is `preference` and `exchange`. Other values are passed on, so the registry decides (`limits_domain/test33` to `test38`).

## `authdata` length and characters

- Data-objects §9.12 gives `authdata` no length or character set for `method: authinfo`, and the registry of methods the constraint of `method` refers to does not exist yet. The EPP test server takes 6 to 16 characters with an upper case letter and a digit, DENIC 8 to 16 characters without `I O l o 0 1`.
- **Proxy:** checks the DENIC character set for RRI (422 `02306`, gap Q4) and passes anything else on (`limits_domain/test39` to `test45`).

## Restore report statements

- Json §8 allows one or two statements in a restore report. RFC 3915 needs exactly two, which the EPP Compatibility Profile does not say.
- **Proxy:** one statement is 400 (`02001`) (`domain_restore/test9`).

## Size of a request

- No draft limits the size of a request or names the result code for one that is too large. DENIC refuses an RRI message over 64 KiB.
- **Proxy:** no limit of its own.

## Result code of a value over a limit

- Data-objects §2.1 says type violations "MUST be treated as errors", without a code. EPP answers 2004 (range), 2005 (syntax) or 2306 (policy) for the same kind of value, depending on the server. Core Table 9 lists `02306` (422) but not `02004` or `02005`, which fall to 400 by class (Table 10). So a name one character too long is 400 on one server and 422 on another.
- A server that cannot announce its limits (discovery has no member for them) leaves the client to learn each by failing.
- **Proxy:** passes the registry's code on. An RRI refusal by its XSD (`83000000004`) or with a class-5 code (e.g. `53300102920`, name servers out of range) is 500 (`02400`), which is wrong for a value the client sent.

## Extension guidelines

Points of [draft-wullink-rpp-extension-guidelines-00](draft-wullink-rpp-extension-guidelines.clean.txt) that are
unclear, found while writing [docs/rri/rri-extension.md](../docs/rri/rri-extension.md) (#131).

### Identifier of a private extension

- §7 requires of a private extension "a URL using the reverse domain name notation, for example
  example.rpp.myextension". Reverse domain notation is no URL. Data-objects §2.3.1 recommends the same prefix for
  "private extension identifiers" of data elements (`org.example.rpp.myElement`), while the guidelines' example
  extension (Appendix A) adds `extProperty1` unprefixed. Whether a private extension prefixes the names of its members,
  objects and `@type` values is not said.
- **Proxy:** the extension's identifier is `de.denic.rpp.rri`; its members (`generalRequest`, `abuse`, `uriTemplate`)
  and its object (`requestContact`) are not prefixed.

### Inheritance in an extension

- Data-objects §2.5 lets an object inherit another (`Extends`), and §2.3.2 lets an extension define objects. The
  guidelines name neither as an extension point (§5, §6), give the specification format no place to state a base object
  (§9, items 9 and 11), and do not say whether a derived data object has a collection endpoint of its own or is served
  in its base object's (§5.7), nor how its schema refers to the base definition. The keyword `Extends` and the
  Extension Mapper `rpp:extends` also read alike but mean different things.
- A derived object inherits every data element with its cardinality (data-objects §2.5), so a base object with a
  required element cannot be the base of an object that lacks it, such as a contact without a Card.
- **Proxy:** the request contact is a data object of its own, not derived from the Contact Data Object. Its
  availability object states `Extends: Base Availability Object`, as data-objects §9.18 does for the base objects.

### Referring to a base definition

- §8.1 and §8.2 require an extension to refer to a base definition by the fully qualified `$id` of the base schema.
  The JSON Schema bundle of the drafts has no `$id`.
- **Proxy:** `rpp:extends` and the `$ref`s name base definitions by their local names (`#/$defs/contact.reference`),
  and the proxy adds the extension's definitions to the bundle.

### Where a schema states its extension

- §9 requires the Extension Overview (name, identifier, version, RPP version, schema `$id`, changed and new objects),
  and §8.5 a registration with the same values, but the schema document has no place for them: json §7 and the example
  of Appendix A.13 have only `$id` and `rpp:extends`.
- **Proxy:** the schema states them in `rpp:extension` (`name`, `id`, `version`, `objects`); `url` is the `$id`.

### RPP version of an extension

- §9 item 2 requires "the minimum RPP version with which the extension is compatible". The drafts define no version
  of RPP beyond the `version` of discovery, which a server states.
- **Proxy:** the overview names the draft versions in `.spec/`.

### New data objects in discovery

- §5.13 requires a server to list every supported extension in discovery, but not whether it lists the data objects
  an extension defines in `objects` (core §12.3).
- **Proxy:** lists `requestContact` in `objects` where the extension is offered.

### Endpoints and operations of a new data object

- §5.7 derives the endpoints of a new data object from its identifier, and §9 item 9.2 asks for "the operations of
  each new object". Whether a new data object has the uniform interface of data-objects §2.7.4 (and an Availability
  Object of its own, data-objects §9.18) by default, or only the operations its specification lists, is not said.
  Neither is how the OpenAPI document of a deployment gets the paths of an extension's objects.
- **Proxy:** the specification lists every operation; Delete answers 501 on RRI. The paths are made when the app is
  built, from those of the Contact Data Object. The OpenAPI document served is OpenAPI 3.1 with the body schemas of the
  default preset's Preset Schema (#204): the drafts' OpenAPI is 3.0, which cannot hold a 2020-12 Preset Schema, and the
  schema of a body differs per preset, see [The body schemas of every preset in OpenAPI](#the-body-schemas-of-every-preset-in-openapi).
  Two switches, off by default, leave out of it the operations on objects the backend does not hold and those no handler
  serves (`rpp_openapi_omit_*`), against the API contract, which lists them; the demo turns them on.

### Members of two extensions with the same name

- §8.3 makes extensions independent and §8.4 merges their members flat into the base object, but nothing keeps two
  extensions from adding a member of the same name to the same object, whose Effective Schema then requires both
  definitions at once.
- **Proxy:** offers one extension, so the case does not arise.

## Identifier pattern and registry handles

- Json -01 §6.1.1 gives the Identifier the pattern `^(\w|_){1,8}-\w{1,}$` (one hyphen, after one to eight word characters), from the EPP `roidType`. EPP contact ids are `clIDType` (RFC 5730 §2.8 gives `roidType` to repository ids only), and DENIC handles have several hyphens (`DENIC-1000022-GR`), so neither fits.
- **Proxy:** the bundle in `src/` predates json -01 and has no pattern for `identifier`; the examples of [docs/rri/rri-extension.md](../docs/rri/rri-extension.md) use DENIC handles.

## Result code of an HTTP-level error

- Core has no result code for a 404 on an unknown path, a 405, a 406 or a 415. Core §18.1 maps a code missing from Table 9 by Table 10, which would make `02001` (x20zz) a 400, so a 404 or 405 with `02001` goes against it.
- **Proxy:** keeps the HTTP status of the framework and sends `02001` through `_default_result` in `problem.py`.
- **Proxy:** a path with a line feed is treated as an unknown path: 404 with `02001`, see `LineFeedPathMiddleware` (#98).

## Profile signalling with the RPP-Profile header

- Core §14.2 gives the version as a Structured Field Decimal (RFC 9651), which has no trailing-zero identity: `1.10` and `1.1` parse to the same number, so a profile cannot have both. The ABNF (`1*DIGIT "." 1*DIGIT`) allows more than three fraction digits, which an SF Decimal does not (it has at most three). The draft should say how versions compare, or give the version as a String.
- §14.2 names no status or RPP result code for a profile or version the server does not support ("an HTTP error response"); §12.4 asks for "an RPP Client error code". It also says nothing about a malformed value, a Dictionary without the `profile` member or its `version` parameter, or members and parameters it does not define.
- §14.2 does not say what a request without the header gets. §14.3 says the default profile of the Discovery document; §14.2 is silent.
- §14 says the two methods "MUST NOT be used simultaneously", without saying what a server that supports one does with the parameters of the other.
- **Proxy:** `rpp_preset_signalling: header` (the default). A request without the header gets the default preset. Every refusal is a 400 with a Problem Detail: `02005` for a value that is not an SF Dictionary (the field lines of a repeated header are combined with a comma first, RFC 9651 §4.2, and a repeated key is the last), a `preset` that is not a Token or a `version` that is not a Decimal (`version=1` is an Integer); `02003` for a missing `preset` member or `version`; `02004` for a preset or version the server does not offer (the version compared as a decimal); `02001` for `preset` or `preset-version` parameters on an `application/rpp+*` media range of `Accept` or `Content-Type` (another media type, such as `application/ld+json;preset=…`, keeps its own `preset` parameter). Other members and parameters are ignored. Only a routed operation selects a preset, so an unrouted path is a 404 and a 401 is before the preset; `/.well-known/rpp` and `/presets/*` are refused like any other. `RPP-Preset` in the response names the applied preset on every response after the selection (core §6.2), also a 5xx Problem Detail of a handler, and `Vary` lists it (RFC 9110 §12.5.5). It is absent on the refusal of the preset itself, on a 401, on an unrouted path and on a 500 that is not a Problem Detail (a framework-level one, #98).

## Profile signalling with media type parameters

- Core §14.3 gives `profile-name = token`, but a profile name such as `urn:ietf:params:rpp:profile:base` holds colons, which a token cannot (RFC 9110 §5.6.2), and the example of §14.3 quotes it. The ABNF also writes the two parameters as one rule joined with `;` OWS, where they are separate media type parameters in any order.
- §13 and §14.3 give the HTTP status of the rejections (415, 406, 400) but no RPP result code, and core §18 Table 9 maps none of them (class 2xxx errors are 400). §12.4 asks for "an RPP Client error code".
- §6.2 says the server MUST use `RPP-Profile` to indicate the profile used in the response, and §14 says the two methods MUST NOT both be used in a single response. With media type signalling both cannot hold.
- §14.3 does not say what a media range without the parameters means in `Accept`, nor a wildcard (`*/*`, `application/*`), which have none. HTTP says a range without parameters matches any parameters, §14.3 says a request without them gets the default profile. Nor what equal weights mean, or an absent or empty `Accept`.
- §14.3 speaks of the profile of "request content" and asks for the parameters in the `Content-Type` of a request with content, while §13 requires a `Content-Type` even without content. The proxy takes the request profile from the `Content-Type` of every request, so the profile of a request without content is not inferred from the `Accept`.
- The request profile and the response profile can differ (the request's must be listed in `Accept`, the response's is the preferred one), and the profile is said to define URL paths, query parameters and header fields (§14.1). What a request under two profiles means for those is open.
- §14.3 says nothing about a response profile that lacks an object or extension member that the request profile has.
- **Proxy:** `rpp_preset_signalling: media-type`. The request preset is that of the `Content-Type` of every request (absent or without parameters: the default preset); it alone governs routing, validation, the mappers and the backend command. The response preset is chosen from `Accept` by weight (RFC 9110 §12.5.1): a range with the parameters stands for that preset, `application/rpp+json` without them for the default preset, `application/*` and `*/*` for every offered one; the most specific range gives the weight, 0 excludes, the request preset wins a tie, else the first range (a wildcard: the default). No `Accept` is the default preset. The request preset must be listed in the `Accept` of every request. Values are a token or a quoted string, versions compare as decimals, as for the header. A data object must be in the request preset; the response is rendered with the extensions of the response preset. A preset or version of the `Content-Type` that is not offered is 415, an `Accept` without an offered preset is 406, both with `02004` (as the header method's `02004`); a request preset the `Accept` does not list is 400 `02001`; a missing `preset` or `preset-version` is 400 `02003`, a value that does not parse 400 `02005`. The `RPP-Preset` request header on this server is 400 `02001`, as the media type parameters are in header mode. A successful RPP response has the parameters of the response preset in its `Content-Type`, a Problem Detail none, `Vary` lists `Accept` on every response of a routed operation, and there is no `RPP-Preset` response header (§14 over §6.2). The refusals are before the selection and name no preset. Where the response preset lacks something the request preset has, a response is rendered with the extensions of the response preset, leaving out the extension members of the request preset. An empty `Accept` is an absent one (the default preset): RFC 9110 gives "nothing acceptable" no clear reading for it.

## Presets, profiles and extensions

The accepted proposals of #174 (`.spec/proposals/174-presets/`) replace the profile model of the drafts (core §12.4, §14,
json §6.11, §7.2, data-objects §2.8, §15) and the two sections about profile signalling above, which describe the drafts as
they were. The proxy follows the proposals, with the following.

- **Preset Schema and the injection.** Json C5 declares `schema` of the Preset Data Object as `{ "type": "object", "readOnly": true }`.
  The injection of `unevaluatedProperties: false` (json §4.9.1) at every object-schema node makes that object accept no member, so
  the embedded schema (`includeElements=schema`) would be refused. **Proxy:** `.spec/auto` has `"additionalProperties": true` there.
- **Published schema.** The proposals say the Preset Schema has no `unevaluatedProperties` and a validator adds them (json C6).
  **Proxy:** follows that. The effective schema of an earlier proxy (the `profile-schemas` extension) published them, and is removed.
- **An extension used outside the preset.** Core RC4 says 400 as for any non-conforming content, and no result code. **Proxy:** a path of
  a data object of an extension that the preset does not contain is 400 `02001`, the code the proxy gives to content that fails the schema
  (`_default_result` in `problem.py`), where the profile model gave 501 `02307`. A data object the backend does not hold stays 501 `02307`.
- **The native media type.** Core C5 says the client lists `application/schema+json` or a range that includes it. **Proxy:** that, or no
  `Accept`, else 406 `02004`; `application/json` does not include it, so it is a 406, where the profile schema endpoint of the proxy accepted
  it. The most specific range decides (`application/schema+json;q=0, */*` is a 406). The request is outside preset signalling in both
  methods (core RC7), and public (RC3: server policy).
- **Operations a profile makes unavailable.** Core RC6 says 02308. **Proxy:** not implemented: no Profile Schema of the proxy makes an
  operation unavailable. The prose constraints of the EPP Compatibility Profile (the Read of a Restore Process, the transfer operations)
  keep 501 or the backend's error, as the issue decided.
- **The EPP Compatibility Profile Schema** is the one of draft-kowalik-rpp-epp-compatibility, in full: the check at start (json C6: a
  profile sub-schema declares no property its target does not) found no violation against the bundle, because `Localization` declares the
  members of an entry. The draft's own note about that (SIDN/ietf-rpp-jscontact-profile#36) applies to the draft's text of json, not to
  the bundle of the proxy. Under the EPP compatible preset what the schema refuses is 422 `02308`, where the mapper answered 501 or 400
  before: a contact PATCH that removes `name` (501 `02102` to 422), a restore report without `restoreTime` or with one statement (400
  to 422). A preset without the profile keeps the mapper's answer.
- **Result code and `type` of the error.** The proposals' example uses `type` `https://rpp.example/problems/profile-constraint`. **Proxy:**
  the error `type` stays `urn:ietf:params:rpp:error`, as for every error, with `result` `02308`, `paths` and `profile`. The reason holds no
  value of the request.
- **`url`.** The Profile Data Object requires `url` (data-objects C8), and the IANA registries do not exist. **Proxy:** the documents the
  proposals name as the specification: `https://datatracker.ietf.org/doc/draft-kowalik-rpp-epp-compatibility/` for the profile, and
  `https://datatracker.ietf.org/doc/draft-ietf-rpp-data-objects/` for the presets `base` and `epp-compatible`. A private preset has none.
- **An attribution.** A request that breaks the constraints of several profiles names the first profile (bases first) whose Profile Schema
  alone refuses it, and none where only their conjunction does (core: "a server can omit the field").
- **A constraint stated by RPP and by a profile.** Core §Extensions and Profiles of a Request says a request that conforms to the preset
  but breaks a constraint that RPP or an extension defines "is rejected as defined for that constraint, and not with 02308". Json §Profiles
  and Validation, read literally, makes every failure of step 2 a broken profile constraint, so a request that breaks both a rule of RPP
  that the schema cannot express (the JSContact profile: US-ASCII, the key sequence, the keys and features of a phone) and the Profile
  Schema of the EPP Compatibility Profile (which repeats it as a pattern) would be 422. **Proxy:** follows core: the checks that RPP or
  an extension defines and the schema cannot express run before step 2, on create, PUT and the patched object, and answer 400 `02001`
  under every preset. Json should say that step 2 excludes what RPP or an extension of the preset already states. A constraint only
  a profile states stays 422, also where an EPP mapper would have refused it before presets (a missing `name` or `emails`, a restore
  report without `restoreTime` or with one statement, core's own example for the last).
- **Extension Schemas, a whitelist.** Json §Extension Framework (json.md:300-304) forbids three things and leaves the rest open. **Proxy:**
  the check at start is stricter, a whitelist applied to the sub-schema and, recursively, to what `allOf`, `anyOf`, `if`, `then`, `else` and
  the values of `dependentSchemas` reach: metadata, `type` `object`, `properties` (not of a member the base declares), `required`,
  `dependentRequired` and `dependentSchemas` over the extension's own members, `patternProperties` that match no member of the base, open
  `additionalProperties` and `unevaluatedProperties`, and the schema `true`. It refuses the rest, among it `not` (also over the extension's
  own members, which would be additive), `oneOf` (branches that are each allowed can exclude each other, so that no base object matches),
  an empty `allOf` or `anyOf`, `const`, `enum`, `propertyNames`, `minProperties`, `maxProperties`, `type` other than `object`, and the
  schema `false`. A whitelist cannot let a schema that constrains the base slip through by a keyword the check did not think of.
- **Responses.** The proposals do not say whether a response is validated against the profiles. **Proxy:** never; a response is validated
  against the preset schema without profiles.
- **An operation a profile makes unavailable on an object the server does not offer.** Core RC6 refuses an operation that an
  applicable profile makes unavailable with 02308, and does not say what wins over 501 when the server does not offer the object
  at all. The DENIC RRI profile (`docs/rri/rri-profile.md`, #183) makes every operation of the Host Data Object unavailable.
  **Proxy:** keeps 501 (`02307`, the host transfer `02101`) under every preset, also under `rri-strict`.
- **A constraint stated by an extension and by a profile.** The DENIC RRI extension requires a server to reject the `contacts` labels
  `generalRequest` and `abuse`, and the DENIC RRI profile allows only `registrant`. Core says a constraint an extension defines is
  rejected as defined for it, and not with 02308. **Proxy:** under `rri-strict` the labels `generalRequest` and `abuse` stay 501
  `02102` (the extension's check runs after step 1 and before step 2, as the checks of RPP do), any other label but `registrant` is 422 `02308`. Guidelines C10 says an extension does not constrain, so the extension's
  sentences on `contacts` belong in the profile, which a later revision of the extension could do (it changes the preset `rri`).
  A partial update that adds a host reference or a label other than `registrant` is 501 `02102` under `rri-strict` too, because the
  refusal that needs no read comes first (as for every profile); a create or a full update with them is 422 `02308`, and so is the
  removal of the registrant by a partial update. The drafts do not say which of the two wins for a partial update.
- **A required extension that a profile relies on without constraining it.** The guidelines require an extension of a profile that
  constrains a definition of it. The DENIC RRI profile constrains base definitions only, but relies on the meaning of the label
  `registrant` that the extension defines. **Proxy:** the profile lists `de.denic.rpp.rri` as a required extension.
- **Cardinality `0` of a `0+` data element.** The guidelines show `0-1` constrained to `0` only, and no draft says whether an empty
  array has cardinality 0. **Proxy:** the DENIC RRI profile refuses the member `nameservers` itself (`false`), also as an empty array.

## The body schemas of every preset in OpenAPI

- Core §Preset Signalling lets a client choose the preset of a request, and the body schemas differ per preset (its extensions and
  profiles). Neither core nor json says how a server's OpenAPI document shows the presets other than its default, and OpenAPI 3.1 can
  choose a body schema by the media type, never by a header. Findings of #205 (OpenAPI 3.1, Connexion 3.2; UIs Swagger UI 5.17.14
  and 5.35.0, Scalar 1.80.0 and 1.76.4, Stoplight Elements 9.0.29, RapiDoc 14.1.0, Redoc 3.1.0, in a browser against the demo):
  - Media type signalling, one document with a `content` entry per preset keyed by `application/rpp+json; preset=…; preset-version=…`:
    valid OpenAPI 3.1. Connexion drops the parameters before it looks up the body schema (only such keys: 415 for every request;
    with a bare key as well: every preset validated with the bare key's schema). Swagger UI, Elements and RapiDoc send the chosen
    preset's `Content-Type` (and `Accept`); Redoc shows the schema per entry and sends nothing; Scalar's test client always sends the
    first entry. Possible, but not in every UI.
  - Header signalling, one document: not possible. `oneOf` of the presets' schemas without a discriminator refuses a body valid under
    two presets and `anyOf` accepts a member of an extension under a preset without it; no UI ties an `RPP-Preset` enum to the body
    (the `oneOf` branch is a choice of its own) or reads an `x-` map.
  - Both methods, one document per preset (the preset's `RPP-Preset` as the only value of the parameter, or its media type as the
    key of every body): possible. Swagger UI (definition selector) and Scalar (source switcher) offer them and send the preset;
    Elements, RapiDoc and Redoc have no selector.
  - Media type signalling with a request without a body (a read): the request preset is that of `Content-Type`, so the request
    must carry one, which OpenAPI does not let a document state (a header parameter `Content-Type` "SHALL be ignored") and a UI
    does not send. Without it the request preset is the default one, and an `Accept` that names only the document's preset is a 400.
- **Proxy:** one document per offered preset, `/openapi/{preset-id}.json` and `.yaml` (outside the RPP paths), stating the preset
  as the server's signalling takes it: header, `RPP-Preset` required with the preset as its only value; media type, every RPP body
  keyed by the preset's media type, no `RPP-Preset` parameter, and every operation without a request body given a required
  `Content-Type` header parameter of that media type (against OpenAPI's "SHALL be ignored": Scalar sends it, and a read then has the
  document's preset). A preset's document leaves out the objects of extensions the
  preset does not contain (a request to them is a 400 under it). `/openapi.json` stays the default preset's. `/ui/` is Scalar with a
  source per preset. Routing and validation are unchanged: Connexion routes with the bare media type, and the body validators
  validate with the signalled preset.

## An extension that adds members to the data object of another extension

- Json §Extension Framework (json.md:300-314) maps `rpp:extends` to a base definition, and the guidelines (extension-guidelines.md C10) only say that a profile that constrains a definition of an extension requires it. Neither says how an Extension Schema adds members to a data object that another extension defines (the planet atmosphere extension to the Planet of the planets extension).
- **Proxy:** the key of `rpp:extends` may be `<$id of the owner extension>#/$defs/<definition>`, as `rpp:constraints` names a definition of an extension. The extending extension implicitly requires the owner: a preset that contains it without the owner does not start, and both are named. The additivity check reads the definition of the owner, so "a property the base declares" is one the owner's definition declares. There is no new member of `rpp:extension`. A specification should state the dependency in its Extension Overview ("Changed base objects"). Json should say that an Extension Schema may extend the definitions of another extension, and that this requires it.

## Message types of an extension

- Data-objects §5 says extensions should define new message types on the Base Message Object, but json gives them no extension
  point: the `data` of `message.read` and `message.create` (json §6.8) is a fixed `oneOf` of the base message types, and an
  Extension Mapper (json §7.1) only adds properties to a definition, so it cannot add a branch to that union.
- **Proxy (RRI, #248):** the schema document of an extension maps the identifier of each of its message types to its
  definition in a new member `rpp:messages`, and the Effective Schema of `message.read` and `message.create` adds a reference to
  each mapped definition to the `oneOf` of `data`. Json should define such a member, or say that every definition that extends
  `baseMessage` joins the union.
- Data-objects §2.5 does not say whether a derived object may restate an inherited data element with a derived Data Type, or
  leave out an inherited element. The Bulk Base Message Object of `de.denic.rpp.rri` holds a list of Object Reference Objects, its
  expiry message types restate the list with Dated Object Reference Objects, and its message types leave out `objectType` and
  `objectId` of the Base Message Object. Json §6.2.16 says the schema of each message type repeats the inherited elements.
- **Proxy:** the bulk message types declare neither `objectType` nor `objectId`, so a message with them fails the schema.
- Message type identifiers of extensions share one namespace with those of the base, with no registry and no prefix rule
  (data-objects §15.3.3 only says the `type` value "MUST be a valid identifier for an RPP message component").
- Core §16.10.1 does not say what a Query answers whose `type` values name only message types the server never sends.
- **Proxy (RRI):** as an empty queue. A value that names a message type of an extension the preset of the response lacks is such a type,
  so under `base` a Query of `domainLockMessage` alone is an empty queue. Where the data of a message read for a requested type fails its
  definition, the message is a `serviceNoticeMessage` and does not match the `type`: the Query answers it all the same, so that it can be
  acknowledged (a deviation from core §16.10.1).
- Core §16.1.7 (rule 7) and §16.10.1 say a parameter of 0 or more values is repeated, one value each. The OpenAPI (TypeSpec) states
  `explode: false` for `type`, which is the comma-separated form.
- **Proxy:** takes both: every repeated value is split on commas, empty parts are dropped. The generated OpenAPI should state `explode: true`.

## Two-step validation of a patch

- Json §Profiles and Validation defines the two steps for a request. It does not say what a JSON Patch, which is not a message of the schema,
  is validated as, nor what a profile constraint on a data element the server manages (`provMetadata`, `processes`) means for an object a
  client patched or replaced, which carries the server's own members.
- **Proxy:** a create, a PUT and the object a PATCH results in (the read representation, patched) go through both steps. For a patched or
  replaced object a failure of step 2 that concerns a read-only member of the base definition or the extension, which the server manages,
  is not the client's and is ignored. Under a preset with applicable profiles the patch of a contact, a domain or a host is always applied
  to the object read for it, also where it needs no read without profiles (a status, the authInfo, a phone or the email), so that the
  profiles are enforced on every request (core, Extensions and Profiles of a Request). The native patch of an extension that has no read
  (the planets extension, D24) has no object: the value of each operation is checked against the profiles as the member it sets (a
  error reported at the member's own path or below it counts), and the removal of a member that an applicable profile lists in an
  unconditional `required` (its top level and its `allOf` branches, not `if`, `then`, `else`, `anyOf`, `oneOf` or `not`) is refused with that
  profile, also for the patch of a domain, a contact and a host, whose removal of a whole member the object read for the patch (which a profile may not constrain, as a read of a foreign domain has no registrant) would not show. A constraint reported at the root of the object (`not` that forbids a member, `if` and `then`, `dependentRequired` and
  other constraints between members) is not enforced on a native patch.

## Telephone number in the contact examples of json

- The contact examples of json (for example the Create request of the Contact Data Object) use `tel:+1-703-555-5555`. The RPP JSContact profile (draft-wullink-rpp-jscontact-profile §4.1.8) requires `tel:+<cc>.<digits>`, for example `tel:+1.7035555555`, and an RPP server MUST reject other values. The `Card` schema of json has no `pattern` for `number`, so the examples validate against it. Filed as SIDN/ietf-rpp-jscontact-profile#29.

## Localization entries of the JSContact Card

- Json §6.2.9 declares `localizations` as `{ "type": "object" }`. With the enrichment of json §4.9.1 that rejects every localization, without it the entries are unchecked, and a profile cannot constrain an entry without declaring members the base does not declare. Filed as SIDN/ietf-rpp-jscontact-profile#36, which also asks to move the Card schema from json into the JSContact profile draft.
- **Proxy:** `Localization` and `RecordLocalization` in `.spec/auto/json-schema/rpp.schema.json` declare the entry (`name`, `organizations`, `addresses`, `emails`, keyed by a language tag).
