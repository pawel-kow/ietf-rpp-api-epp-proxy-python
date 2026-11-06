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
- **Proxy:** a patch of `/status` applies as if the object had no server statuses, on hosts and domains. `remove /status` and `replace /status []` clear the client statuses (a deviation from Figure 3), and server statuses are left alone. A value that names a server status is 400 (`02001`), even if the object has it, and a `match` that names one finds no element (422, `02308`). `ok` is the exception, it stays visible because the draft's example in §5.3.1 replaces it.

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

## `authdata` in read responses

- json §6.2.7 says `authdata` MAY be omitted from read responses, but `authInfo.read` requires it.
- **Proxy:** returns `authInfo` only when the registry returned a password.

## Undeclared properties

- json §4.9.1 requires schemas to be enriched with `unevaluatedProperties: false` before validation. The generated schemas and OpenAPI do not contain it.
- **Proxy:** `rpp_models` rejects undeclared properties with a 400.

## `authInfo` on create

- `authInfo` is optional in `domainName.create`, but EPP requires it, and the backend answers `2003` (400).
- **Proxy:** passes that through. Should the EPP Compatibility Profile make it required?

## Domain `dns` and EPP

- Nothing says how `dnsData` maps to EPP. Core §5 refers to a mapping document that does not exist yet ([TODO REF]).
- **Proxy:** on create, `ns` records and their glue are `ns.hostAttr`, `ds` and `dnskey` records are secDNS. `ns`, `ds` and `dnskey` must be owned by the domain, and `a` and `aaaa` by a nameserver given in the same request and subordinate to the domain. Other records, and `ds` or `dnskey` below the domain, are 501 (`02102`). A read returns `ns.hostAttr` as `dns` and `ns.hostObj` as `nameservers`.
- A registry can store `hostAttr` as host objects, as the test backend does. The create then reads back as `nameservers`, and the glue is at `GET /hosts/{name}`.

## DNSSEC with `nameservers`

- Data-objects §11.2 forbids `nameservers` together with DNS Data entries, without excepting `ds` and `dnskey`. Read literally, a domain delegated through host objects cannot have DNSSEC, and a client has to give its delegation as `ns` records. Should the rule be limited to `ns`, `a` and `aaaa`?
- **Proxy:** a create with `nameservers` and any `dns` record is a 400. A read of such a domain returns both, because it would otherwise lose data.

## `ds` with `dnskey`

- Data-objects §9.9.1 has a TBC on `keyData` inside `dsData`, and §9.11 lets a client send both record types. RFC 5910 has a DS and a key data interface, and a server uses one.
- **Proxy:** both in one request are 501 (`02102`). A read leaves out a `keyData` nested in a `dsData`.

## IDN

- json §6.4 requires `lgr` whenever `uName` is present, and core EPP has no element for either. So `uName` cannot be computed from the A-label on read without breaking that rule.
- **Proxy:** both are 501 (`02102`) on create and are left out of a read (#58).

## Disclose

- The Disclose Object is TBD in data-objects §9.13, and `disclose.read` has only `@type`.
- **Proxy:** 501 (`02102`) (#59).

## Host DNS records

- The EPP Compatibility Profile (data-objects §13.2) limits the entries of `dns` to A and AAAA, but the host examples (json §8.3.2 to §8.3.4) include an `ns` record.
- The same section allows entries subordinate to the host name, but EPP has one address list per host, so a record for another name has no place in EPP.
- **Proxy:** follows the examples. An `ns` record is accepted only as the self-reference (`@` with the host as `nsdname`), and A and AAAA records must name the host itself (`@` or its name), anything else is 501 (`02102`). A read emits the `ns` record plus A and AAAA records when the host has addresses, and no `dns` when it has none.

## Data the EPP Compatibility Profile cannot hold

- The host create example (json §8.3.2) has `dns.controls.ttl`, which core EPP has no element for (RFC 9803 adds one), and the data-objects draft does not limit `controls` in the EPP Compatibility Profile. An example the profile cannot carry leaves open what a server should do: reject it, ignore it, or apply a default. Should the profile forbid `controls`, and with which result code?
- **Proxy:** `ttl` is 501 (`02103`), because the proxy does not implement RFC 9803, on hosts and domains, so the §8.3.2 example answers 501 as written (`draft_host/test2`). `maxSigLifetime` is 501 (`02102`), and a read leaves out the secDNS `maxSigLife`. Nothing is dropped silently.

## `status` on host create

- `status` is read-write on a host, and `host.create` accepts `clientDeleteProhibited` and `clientUpdateProhibited`. EPP `<host:create>` has no status element, so honouring it takes a create and an update, which is not atomic. Should the EPP Compatibility Profile exclude `status` from create?
- The same applies to domain create.
- **Proxy:** 501 (`02102`).

## Host transfer

- Data-objects §13.4 gives the host a Transfer Process and the OpenAPI has the operations. RFC 5732 defines no host transfer: subordinate hosts move with their domain, and data-objects §11.4.2 disallows anything that breaks that relationship.
- **Proxy:** 501 (`02101`).

## Full update without a change

- A host update must provide at least one change (data-objects §13.3.4), but a PUT repeating the stored state is a valid full update (core §16.8) and PUT is idempotent in HTTP.
- **Proxy:** passes the empty update on, the backend answers `2003` (400).

## Transfer process

- `GET .../transferProcesses/latest` with nothing pending gets EPP `2301`. Table 9 maps `02301` to 409, but the OpenAPI has no 409 on that GET, and core §16.9.5.2 says the resource "may not exist", which suggests 404 (#68).
- **Proxy:** 409 (`02301`).
- Core §16.9.5.5 shows approve with no content and the OpenAPI declares no `requestBody`, but json §8.1.10 sends `{"@type": "domainTransferProcess"}`.
- **Proxy:** accepts both.
- Json §8.2.9 gives an example with `reason`, which data-objects §10.1.1.5 forbids in the EPP Compatibility Profile, without naming the rejection.
- **Proxy:** 501 (`02102`).
- EPP has no process ids and no transfer history, so the list and `/{processId}` operations have nothing to map to.
- **Proxy:** 501 (`02101`), and responses have no `processId`.
- EPP has no push transfer, and its response does not say the direction.
- **Proxy:** `transferDir: push` and `gainingClientId` are 501 (`02102`), and responses always have `transferDir: pull`.
