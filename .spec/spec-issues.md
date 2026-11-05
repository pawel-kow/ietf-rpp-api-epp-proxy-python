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
