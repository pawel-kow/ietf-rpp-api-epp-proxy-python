# Integration test review: coverage of the data object fields

Status: draft, 2026-11-12, `main` at 414a86e. Companion file: [backend-limits.yaml](backend-limits.yaml).

This review checks the data-driven integration suite (`tests/integration/test_case_data/`, 312 cases) against
three criteria, for every writable field of the Domain Name, Contact and Host data objects and of the component
objects they carry:

1. **Presence and transitions.** Create with the value and without it; update from absent to present, from one
   value to another, and from present to absent, by full update (PUT) and by partial update (PATCH), within the
   mutability the data-objects draft defines (`create-only` fields must be refused on update).
2. **Arrays and aggregations.** Add an element, remove one, clear the array, fill it to the maximum, and go over the
   maximum.
3. **Value boundaries.** Minimum and maximum length or value, and the allowed character set or format.

Where the drafts leave a boundary undefined, the backend's own limit has to be found by a case that goes over it.
§5 lists the boundaries the drafts leave open, §6 the probe cases proposed for them, and
[backend-limits.yaml](backend-limits.yaml) the limits of the EPP test server and of DENIC RRI MTEST, each with its
source and its probe.

The two Python modules `tests/integration/test_domain_create.py` and `test_domain_delete.py` define `test_cases = []`
and keep their old cases in an unassigned list literal, so they collect no test. They are not counted here
(finding F1 in §7).

## 1. How to read the tables

Case references are `<group><number>`:

| Prefix | Group | Prefix | Group |
|---|---|---|---|
| DC | `domain_create` | CC | `contact_create` |
| DU | `domain_update` | CU | `contact_update` |
| DL | `domain_lifecycle` | CT | `contact_transfer` |
| DR | `domain_renew` | CX | `contact_delete` |
| DS | `domain_restore` | HC | `host_create` |
| DT | `domain_transfer` | HU | `host_update` |
| DX | `domain_delete` | HG | `host_get` |
| XD | `draft_domain` | XC | `draft_contact` |
| XP | `draft_patch` | XH | `draft_host` |

A case runs on both backends unless marked **(E)**, the EPP test server only, or **(R)**, RRI MTEST only. Of the 312
cases, 103 run on both, 201 on EPP only, 5 on RRI only and 3 are skipped (`XH5` #49, `HX4` #50, `HU17` #54). All host
cases are (E), because RRI has no host objects; the host tables do not repeat the mark.

| Mark | Meaning |
|---|---|
| ✅ | Covered: the transition or boundary is exercised and its outcome asserted |
| ◐ | Partly: on one backend only where both support it, only one of PUT/PATCH, or the outcome is not read back |
| ❌ | Not covered |
| ➖ | Does not apply (mutability, or a refusal is the whole contract and is covered elsewhere) |
| 501 | The proxy refuses it with 501; the cell names the case that pins the refusal |

## 2. Summary

A point is one mark in the tables below, so a cell with a PUT and a PATCH part counts twice. ✅ includes the
refusals pinned by a 501 case.

| Object | Points | ✅ | ◐ | ❌ |
|---|---|---|---|---|
| Domain: presence and transitions (§3.1) | 108 | 63 | 7 | 38 |
| Domain: arrays (§3.2) | 50 | 11 | 1 | 38 |
| Domain: boundaries (§3.3) | 27 | 9 | 0 | 18 |
| Contact: presence and transitions (§3.4) | 113 | 69 | 7 | 37 |
| Contact: arrays (§3.5) | 33 | 18 | 1 | 14 |
| Contact: boundaries (§3.6) | 29 | 7 | 1 | 21 |
| Host: presence and transitions (§4.1) | 47 | 36 | 3 | 8 |
| Host: arrays (§4.2) | 13 | 8 | 0 | 5 |
| Host: boundaries (§4.3) | 9 | 4 | 0 | 5 |
| **All** | **429** | **225** | **20** | **184** |

The suite is strong on **transitions of the EPP mapping**: PUT versus PATCH, `match` semantics, refusals of what EPP
cannot express (501), and the proof of absence by a 422 `02308` `match`. It is weak on three things:

- **No value boundary is tested on either side of a limit.** Every length, count and range in the suite is a
  comfortable middle value. The only boundary cases are format refusals (phone with hyphens `CC17`, non-ASCII
  internationalized name `CC19`, IPv6 in an `a` record `HC10`, DS digest `XY` `DC22`) and the IDN rules.
- **No array is filled to its maximum or past it**: nameservers (13 on both backends), contacts per role (5 on EPP),
  holders (5 on RRI), DS and DNSKEY records, host addresses (13), street lines (3 on EPP), localizations (1).
- **RRI coverage of updates is thin.** Of the 37 `domain_update` cases 13 run on RRI, and none of them changes `dns` (`DU15` only pins the 501 for clearing it),
  the field RRI depends on (name servers, `a`/`aaaa`/`mx` entries, `dnskey`). `mx` is in the RRI profile and has no
  case at all.

Fields with no case at all: domain `status.due`, domain `dns.controls.maxSigLifetime`, domain `dns` records of type
`mx`, contact `links`, contact `language` on update, contact `disclose` on create.

## 3. Domain Name and Contact

### 3.1 Domain Name: presence and transitions

C+ create with the value, C− create without it, U+ absent → present, U~ change, U− present → absent.

| Field | Mutability | C+ | C− | U+ | U~ | U− |
|---|---|---|---|---|---|---|
| `name` | create-only | ✅ every create | ◐ `DC9` (wrong member name, generic 400) | ➖ | PUT ✅ `DU20` 400 · PATCH ❌ | ➖ |
| `uName` | create-only | ✅ `DC24`, read `XD7` | ✅ `DC25` | PATCH ❌ (`add /uName` must be refused) | PATCH ❌ | ✅ PUT keeps it `DU33`, PATCH keeps it `DU34`(E) |
| `lgr` | create-only | ✅ `DC24`, `DC25` | ✅ `DC26` (IDN without lgr, by env) | PATCH ❌ | PATCH ❌ | ✅ `DU33` |
| `status` (client labels) | read-write | ❌ (create with `clientHold`) | ✅ every create | PATCH ✅ `DU12`(E) `DU13`(E) · PUT ✅ `DU22`(E) | PATCH ✅ `DU12`(E) `XP2`(E) `DU34`(E) · PUT ❌ (one label for another) | PATCH ✅ `DU14`(E), `replace []` `DU13`(E) · PUT ✅ `DU22`(E) |
| `status[].reason` | create-only in the status | ❌ | ✅ | PUT ◐ `DU22`(E), not read back (#54) | PATCH ◐ `DU22`(E) | ◐ `DU22`(E) |
| `status[].due` | read-write | ❌ | ✅ | ❌ | ❌ | ❌ |
| `registrant` | read-write | ✅ `DC3`, `DC4`, `DL1` | ✅ `DC1`(E) | ❌ (domain created without one) | PATCH ✅ `DU1`(E) `DU4`(E) `XP1`(E) · PUT ✅ `XD8`(E) | PUT ✅ `DU32`(E) · PATCH ◐ (only as the 422 proof in `DU32`) |
| `contacts` | read-write | ✅ `DC3`, `DC4` | ✅ `DC1` | PATCH ✅ `DU1`(E) `DU4`(E) `XP3`(E) `DU37`(R) · PUT ❌ | PATCH ✅ `DU17`(E) · PUT ✅ `DU17`(E) | PATCH ✅ `DU4`(E) `DU9`(E) `DU37`(R) · PUT ✅ `DU17`(E) |
| `nameservers` | read-write | ✅ `DC6`(E) `XD5`(E) · 501 `DL6`(R) | ✅ `DC1` | PATCH ✅ `DU3`(E) `DU8`(E) · PUT ✅ `DU17`(E) | PATCH ✅ `DU8`(E) `DU17`(E) `XP4`(E) · PUT ✅ `DU17`(E) | PATCH ✅ `DU3`(E) · PUT ✅ `DU17`(E) (2 → 1) |
| `dns.records` `ns` | read-write | ✅ `DC18`(E) | ✅ `DC1` | PUT ✅ `DU29`(E) · PATCH ❌ | ❌ | PATCH ◐ `DU15` (`replace []` on a domain without dns) |
| `dns.records` `a`/`aaaa` | read-write | ✅ `DC1` (`a`, R fixture), `DC5` | ✅ `DC1`(E) | PATCH ✅ `DL2`(R) · PUT ❌ | ❌ | ❌ |
| `dns.records` `mx` | read-write | ❌ (R) | ✅ | ❌ | ❌ | ❌ |
| `dns.records` `ds` | read-write | ✅ `DC16`(E), refused next to `dnskey` `DC21`(E) | ✅ | ❌ (DS on an unsigned domain) | PATCH ✅ `DU16`(E) `DU23`(E) · PUT ✅ `DU24`(E) | PUT ✅ `DU23`(E) · PATCH ❌ |
| `dns.records` `dnskey` | read-write | ◐ `DC17`(E) (`any_of`) · RRI ❌ | ✅ | ❌ | ❌ | ❌ (RRI: omitting it deletes the keys) |
| `dns` with `nameservers` | — | ✅ `DC19`(E) 400 | ➖ | PUT ✅ `DU25`(E) 400 | ➖ | ➖ |
| `dns.controls.ttl` | read-write | 501 `DC20` | ✅ | PUT 501 `DU28` | ➖ | ➖ |
| `dns.controls.maxSigLifetime` | read-write | ❌ | ✅ | ❌ | ❌ | ❌ |
| `authInfo` | read-write (immutable object) | ✅ every create, read `DU26`(E) | ❌ | ➖ | PATCH ✅ `DU1`(E) `DU2` `DL4` · PUT ✅ `DU26`(E) `XD8`(E) | PUT omitted keeps it ✅ `DU26`(E) · PATCH `remove /authInfo` ❌ |
| `processes.createProcess[].period` | create input | ✅ `DC2`(E) `XD5`(E) | ✅ `DC1` | ➖ | ➖ | ➖ |
| `provMetadata`, `expiryDate`, `subordinateHosts` | read-only | read ✅ `DT1`(E), `DR6`(E), `DC23`(E) | ➖ | write refused ❌ (PUT and PATCH) | ❌ | ❌ |

### 3.2 Domain Name: arrays and aggregations

| Array | Add | Remove | Clear | At maximum | Over maximum | Duplicate |
|---|---|---|---|---|---|---|
| `status` | ✅ `DU12`(E) | ✅ `DU14`(E) `DU22`(E) | ✅ `DU13`(E) | ❌ (all five client labels) | ✅ server label refused `DU21` · ❌ unknown label | ❌ |
| `contacts` (per label) | ✅ `DU1`(E) `DU4`(E) `DU37`(R) | ✅ full match `DU4`(E), partial `DU9`(E), `DU37`(R) | ❌ (`replace /contacts []`) | ❌ (5 per role, E) | ❌ (6th by create and by update, E; 2nd abuse, R) | ❌ |
| `contacts` unknown label | ➖ | ➖ | ➖ | ➖ | ❌ (501 by spec-issues) | ➖ |
| `contacts` match | ➖ | ✅ none matches `DU10`(E), ambiguous `DU11`(E) | ➖ | ➖ | ➖ | ➖ |
| `registrant` (RRI holders) | ✅ `DL3`(R) | ❌ | ➖ | ❌ (5) | ❌ (6) | ❌ (same holder twice) |
| `nameservers` | ✅ `DU3`(E) `DU8`(E) | ✅ `DU3`(E) | ❌ | ❌ (13) | ❌ (14 by create; 14 by adding to an existing set, E) | ❌ |
| `dns.records` `ns` (RRI Nserver) | ❌ | ❌ | ➖ (required) | ❌ (13) | ❌ (14; and 1, under the minimum of 2) | ❌ |
| `dns.records` `a`/`aaaa`/`mx` (RRI Nsentry) | ✅ `DL2`(R) | ❌ | ❌ | ❌ (5) | ❌ (6; `aaaa` without `a`) | ❌ |
| `dns.records` `ds` | ❌ (a second DS) | ❌ (one of two) | ◐ PUT `DU23`(E) | ❌ | ➖ (no limit on E) | ❌ (same digest twice, E refuses with 2306) |
| `dns.records` `dnskey` (R) | ❌ | ❌ | ❌ | ❌ (20) | ❌ (21) | ❌ |
| `dns.records` (all, R) | ➖ | ➖ | ➖ | ❌ (20 entries) | ❌ (21) | ➖ |

### 3.3 Domain Name: value boundaries

| Field | Boundary | Covered by |
|---|---|---|
| `name` | label length 63 / 64 (DNS) and the E minimum of 2 | ❌ |
| `name` | total length within the DNS limit (E stores 68 characters, R takes 66) | ❌ |
| `name` | leading or trailing `-`, `--` in positions 3–4, `_` | ❌ |
| `name` | upper case input, trailing dot, a TLD the server does not serve | ❌ |
| `name` | IDN A-label | ✅ `DC24`–`DC26` |
| `uName` | not matching `name` | ✅ `DC30` |
| `uName` | code point outside the LGR | ✅ `DC29`(E) |
| `uName` | not NFC, IDNA2003-only code point, Bidi rule | ❌ |
| `lgr` | unknown LGR | ✅ `DC28` |
| `lgr` | on an ASCII name | ✅ `DC31` |
| `uName` | without `lgr` | ✅ `DC27` |
| `authInfo.authdata` | length (E 6–16, R 8–16) both sides | ❌ |
| `authInfo.authdata` | character set (E needs upper case and digit, R excludes `I O l o 0 1`) | ❌ |
| `authInfo.method` | other than `authinfo` | ❌ |
| `period` | value 0 and 100 (schema 1–99) | ❌ |
| `period` | 11 months, 10 and 11 years (E: 1–10 years in whole years) | ❌ |
| `renewalPeriod` | 11 months, past 10 years ahead (E) | ❌ (`DR3` 24 months in range) |
| `ds` `keyTag` | 65535 / 65536 | ❌ |
| `ds` `digest` | not hex | ✅ `DC22`(E) |
| `ds` `digestType` | 4 (SHA-384, E cannot store) | ❌ |
| `dnskey` | flags 256/257, protocol 3, algorithm list (R) | ❌ |
| `dnskey` | `publicKey` length (E 255, R 30–999) | ❌ |
| `dns.controls` | any value | 501 `DC20`, `DU28` |
| `status.label` | server label on update | ✅ `DU21` |
| `contacts[].object.id` | a contact that does not exist, one of another registrar | ❌ |
| `registrant.id` | a contact that does not exist, one of another registrar | ❌ |
| `nameservers[].hostName` | a host that does not exist | ❌ |

### 3.4 Contact: presence and transitions

| Field | Mutability | C+ | C− | U+ | U~ | U− |
|---|---|---|---|---|---|---|
| `id` | create-only | ✅ every create | ◐ `CC9` (wrong members) | ➖ | PUT ✅ `CU10` 400 · PATCH ✅ `CU27` 400 | ➖ |
| `id` read in other case | — | ➖ | ➖ | ➖ | ✅ `CU15` | ➖ |
| `status` (client labels) | read-write | ❌ | ✅ | PATCH ✅ `CU19`(E) · PUT ✅ `CU6`(E) | ❌ | PATCH ✅ `CU19`(E) · PUT ✅ `CU6`(E) · `replace []` ❌ |
| `status[].reason` | create-only in the status | ❌ | ✅ | PUT ◐ `CU7`(E), not read back | ❌ | ◐ `CU7`(E) |
| `contactInfo.kind` | read-write | ✅ `CC1` individual, `CC2` org | ❌ (omitted, default individual) | ➖ | PUT ✅ `CU2`(E) org → individual, `CU16` org without org 400 · PATCH ◐ `CU35`(R) | ➖ |
| `contactInfo.language` | read-write | ✅ `CC16`(E) | ✅ | ❌ | ❌ | ❌ |
| `contactInfo.name.full` | read-write (R immutable) | ✅ every create | ❌ (missing name) | ➖ | PATCH ✅ `CU18` (E 200, R 422) · PUT ❌ (`CU9`, `XC5` change it but are refused for other reasons) | PATCH ✅ `CU20` (E 501, R 422) · PUT ✅ `CU5`, `XC5` 501 |
| `organizations.org.name` | read-write | ✅ `CC2`, `CC3` | ✅ `CC1` | PATCH ✅ `CU24` · PUT ❌ | PUT ✅ `CU35`(R) · PATCH ❌ | PATCH ✅ `CU25`(E) `CU35`(R) · PUT ✅ `CU2`(E) |
| `addresses` street lines | read-write | ✅ `CC3` (3) | ✅ `CC16`(E) (none) | ❌ (a line added) | ◐ `XC5` (select by backend) | ❌ (a line removed) |
| `addresses` locality | read-write, required | ✅ | ❌ (missing locality) | ➖ | PUT ✅ `CU1` · PATCH ❌ | ➖ |
| `addresses` region | read-write | ✅ `CC3`(E) | ✅ `CC1` | ❌ | PUT ✅ `CU1`(E) | ❌ |
| `addresses` postcode | read-write | ✅ `CC1` | ✅ `CC16`(E) | ❌ | PUT ✅ `CU1` | ❌ |
| `addresses.countryCode` | read-write, required | ✅ | ❌ (missing) | ➖ | ◐ `CU5` (`select`) | ➖ |
| `emails.email` | read-write, required | ✅ | ❌ (missing) | ➖ | PATCH ✅ `CU17` `DL7` · PUT ✅ `CU1` | PATCH ✅ `CU21` (E 501, R 422) |
| `phones.voice` | read-write (R required) | ✅ `CC1` | ✅ `CC16`(E) | ❌ | PATCH ✅ `CU31` · PUT ✅ `CU1` | PATCH ✅ `CU2`(E) · PUT ✅ `CU2`(E) |
| `phones.voice` extension | read-write | ✅ `CC3` | ✅ | ❌ | ❌ | ❌ |
| `phones.fax` | read-write (E) | ✅ `CC3`(E) | ✅ | ❌ | ❌ | PATCH ✅ `CU2`(E) · PUT ✅ `CU2`(E) |
| `links` | read-write | ❌ (501 by spec-issues) | ✅ | ❌ | ❌ | ❌ |
| `localizations` | read-write (E) | ✅ `CC16`(E) `CC20`(E) | ✅ | PUT ✅ `CU33`(E) · PATCH ✅ `CU34`(E) (500, the backend ignores it) | PUT ✅ `CU8`(E) | PUT 501 `CU9`(E) · PATCH 501 `CU32`(E), part of it ✅ `CU8`(E) |
| `authInfo` | read-write | ✅ (E) | ◐ `CU35`(R) | ➖ | PUT ✅ `CU14`(E) · PATCH ✅ `CU23`(E) | PATCH 501 `CU22`(E) · PUT omitted keeps it ✅ `CU14`(E) |
| `disclose` | read-write | ❌ | ✅ | PUT 501 `CU12` · PATCH 501 `CU30` | ➖ | ➖ |
| `provMetadata` | read-only | read ✅ `CT1`(E) | ➖ | write refused ❌ | ❌ | ❌ |

### 3.5 Contact: arrays and maps

| Array or map | Add | Remove | Clear | At maximum | Over maximum | Duplicate |
|---|---|---|---|---|---|---|
| `status` | ✅ `CU19`(E) | ✅ `CU19`(E) | ❌ | ❌ (three client labels) | ❌ (server label) | ❌ |
| street lines (`components` kind `name`) | ❌ | ❌ | ✅ none at create `CC16`(E) | ✅ 3 `CC3` | ❌ (4: E 501; R allows more) | ➖ |
| `components` locality / region / postcode | ➖ | ❌ region, postcode | ➖ | ✅ one each | ❌ (two of a kind) | ➖ |
| `emails` | ➖ | ✅ refused `CU21` (E 501, R 422) | ➖ | ✅ 1 | `email-1` 501 `CC18` | ➖ |
| `phones` | ◐ `CU31` (adds over an existing voice) | ✅ `CU2`(E) | ❌ | ✅ voice and fax `CC3`(E) | ❌ (`voice-1`; a `fax` on R) | ❌ (key and features that disagree) |
| `localizations` | ✅ `CC16`(E) | 501 `CU32`(E) | 501 `CU9`(E) | ✅ 1 `CC16`(E) | ❌ (2 → 501) | ➖ |
| `organizations` | ✅ `CU24` | ✅ `CU25`(E) `CU35`(R) | ✅ `CU35`(R) | ✅ 1 | ❌ (`org-1`) | ➖ |

### 3.6 Contact: value boundaries

| Field | Boundary | Covered by |
|---|---|---|
| `id` | length (E 3–16, R 9–32) both sides | ❌ |
| `id` | character set, prefix of another registrar | ❌ |
| `id` | case on update | ✅ `CU15` |
| `name.full` | US-ASCII in the internationalized form | ✅ `CC19` |
| `name.full` | non-ASCII in a localization | ✅ `CC20`(E) |
| `name.full` | minimum (E 5, R 3) | ❌ |
| `name.full` | maximum 255 / 256 (E cuts it, pawel-kow/epp#21) | ❌ |
| `name.full` | punctuation outside E's set (`'`), a character outside the BMP in a localization | ❌ |
| `name.full` | RRI completeness rules (digits only, repeated letters) | ❌ |
| `organizations.org.name` | minimum (E 5) and maximum 255 | ❌ |
| street line | minimum (E 5) and maximum 255 | ❌ |
| locality | minimum (E 4), a digit (E refuses), maximum (R 80) | ❌ |
| region | lower case first letter (E refuses) | ❌ |
| postcode | minimum (E 3), maximum (E 16, R 20), lower case (E refuses), DE with 4 digits (R) | ❌ |
| `countryCode` | lower case (schema), unknown code `XX` | ❌ |
| email | without `@`, over 255 | ❌ |
| phone | hyphens | ✅ `CC17` |
| phone | 15 and 16 digits, subscriber of 3 digits (R needs 4), extension over 10 digits (E stores int(10)) | ❌ |
| phone | extension present | ✅ `CC3` |
| `features` | key and features that disagree, both features | ❌ |
| `kind` | `org` without organisation | ✅ `CU16` |
| `kind` | individual with organisation | ◐ `XC2`, `CU35`(R) |
| `authInfo.authdata` | length (E 6–16) and character rule both sides | ❌ |
| `localizations` key | not a BCP 47 tag | ❌ |
| `version` | other than `2.0` | ❌ |
| undeclared member | in `name` | ✅ `CU11`, `CU29` |
| unknown JSContact property | e.g. `nicknames` | ❌ |
| `contactInfo` | missing locality, missing email, missing name | ❌ |
| `contactInfo` | RRI without phone | ❌ |

## 4. Host (EPP only)

### 4.1 Presence and transitions

| Field | Mutability | C+ | C− | U+ | U~ | U− |
|---|---|---|---|---|---|---|
| `hostName` external | read-write | ✅ `HC1` | ➖ required | ➖ | ❌ (rename of an external host) | ➖ |
| `hostName` internal | read-write | ✅ `HC3`, without its domain `HC4` 404 | ➖ | ➖ | PATCH ✅ `HU4` · PUT ✅ `HU13` | ➖ |
| `status` | read-write | 501 `HC6` | ✅ | PATCH ✅ `HU1` · PUT ✅ `HU10` | ❌ (one label for another) | PATCH ✅ `HU2` `HU23` · `replace []` ✅ `HU22` · PUT ✅ `HU12` |
| `status[].reason` | create-only in the status | ➖ | ✅ | PATCH ◐ `HU18` · PUT ◐ `HU19`, read back skipped `HU17` (#54) | PUT ◐ `HU20` | ✅ `HU12` |
| own `ns` record | required | ✅ `HC1` | ✅ `HC11`, `HC12` 400 | PATCH ✅ `HU36` 400, `HU37` | ➖ | PATCH 501 `HU34`, `HU35` · PUT ✅ `HU33` 400 |
| `a` record | read-write | ✅ `HC2`, `HC3` | ✅ `HC1` | PATCH ✅ `HU3` `HU16` · PUT ✅ `HU10` | PATCH ✅ `HU9` `HU21` · PUT ✅ `HU11` | PATCH ✅ `HU16` `HU26` · PUT ❌ |
| `aaaa` record | read-write | ✅ `HC2` | ✅ `HC1` | PATCH ✅ `HU26` · PUT ❌ | ❌ | ❌ |
| record of another type or name | — | 501 `HC8`, `HC9` | ➖ | ❌ | ➖ | ➖ |
| `dns` as a whole | read-write | ✅ | ✅ `HC11` | ➖ | ➖ | 501 `HU27` |
| `dns.controls` | read-write | 501 `HC7`, `XH2` | ✅ | 501 `HU28` | ➖ | ➖ |
| `provMetadata` | read-only | ❌ read | ➖ | ✅ refused `HU8` | ➖ | ➖ |

### 4.2 Arrays

| Array | Add | Remove | Clear | At maximum | Over maximum | Duplicate |
|---|---|---|---|---|---|---|
| `status` | ✅ `HU1` | ✅ `HU2` | ✅ `HU22` | ❌ (both client labels) | ✅ server label `HU29` | ❌ |
| addresses | ✅ `HU3` `HU16` `HU26` | ✅ by full match `HU16`, by partial match `HU26` | ❌ | ❌ (13) | ❌ (14 by create; 14 by update, which E does not count) | ✅ `HU32` 422 |
| `match` | ➖ | ✅ none matches `HU24`, ambiguous `HU25` | ➖ | ➖ | ➖ | ➖ |

### 4.3 Value boundaries

| Field | Boundary | Covered by |
|---|---|---|
| `hostName` | label 63 / 64, name 253 / 254 | ❌ |
| `hostName` | character set, upper case input | ❌ |
| `a` address | IPv6 in an `a` record | ✅ `HC10` |
| `a` address | `256.0.0.1`, private and reserved ranges | ❌ |
| `aaaa` address | invalid, uncompressed form | ❌ |
| PATCH | empty patch | ✅ `HU5` |
| PATCH | no change | ✅ `HU30` |
| PUT | no change | ✅ `HU15` |
| `status.label` | unknown label | ❌ |

## 5. Boundaries the drafts leave open

What the drafts in `.spec/` say, and what an implementation has to guess. [spec-issues.md](../../.spec/spec-issues.md)
already has *Length of contact fields* (item 3 here), *Contact labels* (6) and *Localized and additional entries*
(part of 4); the others are new. Name lengths are not among them: the FQDN type (§2.1.11) takes the DNS limits of RFC
9499 and RFC 1035 §2.3.4, 63 octets a label and 255 octets a name (253 characters in text form), and a `uName` is bounded by the A-label it
must convert to.

1. **Identifier** (data-objects §7.1) names "a specified minimum length, a specified maximum length" without
   values. The JSON draft §6.1.1 then prescribes RFC 5730 `roidType`, `^(\w|_){1,8}-\w{1,}$`, at most 89
   characters. A contact id is a `clIDType` in EPP (3–16 characters, any non-space), and a DENIC handle
   `DENIC-1000022-EXAMPLE` has a second hyphen, which `roidType` does not allow. The proxy's schema puts no
   constraint on `identifier`. The EPP Compatibility Profile should say a contact `id` is a `clIDType`.
2. **Status** arrays have no maximum and no rule for a label given twice. `reason` has no maximum length. `due` has
   no rule for a value in the past.
3. **JSContact fields** (`name.full`, `organizations.*.name`, address component values, email) have no maximum
   length. RFC 5733 has 255 for postal lines and 16 for `pc`, which the EPP Compatibility Profile could state. The
   profile also has no minimum for any of them.
4. **Street lines**: "the server MAY constrain the maximum number"; the EPP Compatibility Profile says "up to
   three" in data-objects but not in the JSContact profile. More localizations than supported "MUST be rejected"
   without a result code.
5. **Associations**: no minimum or maximum for `nameservers`, `contacts` per label ("MAY be restricted by server
   policy") or holders, and no way for a client to discover them.
6. **Contact labels** are an open string.
7. **DNS records**: no maximum count per type; `rdata` member names are given for `ns`, `a`, `aaaa`, `ds`, `dnskey`,
   but no value ranges (`keyTag` 0–65535, `algorithm` 0–255, digest length by `digestType`, `flags`); `mx`, which a
   server may accept as a parent-side record (RRI does), has no `rdata` structure at all.
8. **DNS controls**: `ttl` and `maxSigLifetime` have a minimum of 1 and no maximum.
9. **`authInfo.authdata`** has no length or character set for `method: authinfo`. The `method` registry is not
    defined yet.
10. **Restore report**: json §8 allows 1–2 statements; the EPP Compatibility Profile needs exactly 2 (RFC 3915) and
    does not say so.
11. **Request size**: no maximum and no result code (RRI refuses a PDU over 64 KiB).
12. **Result code of a limit violation**: data-objects §2.1 says type violations "MUST be treated as errors" but
    not which. EPP has 2004 (range), 2005 (syntax) and 2306 (policy); 02004 and 02005 are not in core Table 9, so they
    fall to 400 by class, while 02306 is 422. The same over-long value is 400 on one server and 422 on another.
13. **Discovery** has no element to announce any limit, so every limit above is learnt by failing.

## 6. Proposed probe cases

Cases that go over each limit, in three new groups, `limits_domain/`, `limits_contact/` and `limits_host/` (the last
with `_group.json` `{"when": {"profile.host_objects": true}}`). Each limit gets the value at the limit and the value
past it, so a change of the backend shows as a failure of exactly one of the two. The full list with the expected
answer per backend is in [backend-limits.yaml](backend-limits.yaml) under `probe`; the outline:

| Group | Cases | Limits |
|---|---|---|
| `limits_domain` | `test1`–`test12` | label length 1/63/64, total length (E column of 68 characters), hyphens, `_`, upper case, trailing dot, other TLD, `uName` NFC and IDNA2003 |
| `limits_domain` | `test13`–`test22` | all client statuses, a status twice, 5/6 holders and one holder twice (R), 5/6 tech contacts by create and by update (E), a 2nd abuse contact (R), unknown label |
| `limits_domain` | `test23`–`test33` | 13/14 nameservers by create and by update (E), 1/13/14 `ns` records, 5/6 address records, `aaaa` without `a`, `mx` (R), 21 records (R) |
| `limits_domain` | `test34`–`test39` | `keyTag` 65535/65536, `digestType` 4, two DS records (E), DNSKEY flags and algorithm (R) |
| `limits_domain` | `test40`–`test53` | request over 64 KiB, `authdata` 5/16/17 and character rules, unknown `method`, `period` 0/100/11 months/10 and 11 years, renew 11 months and past 10 years (E) |
| `limits_contact` | `test1`–`test8` | `id` 16/17 (E) and 32/33 (R), prefix of another registrar, `_` and `.`, all client statuses |
| `limits_contact` | `test9`–`test31` | `name.full` 4/255/256, `'`, a character outside the BMP, org 4/256, 0 and 4 street lines, street 4/256, city 3/81 and with a digit, region in lower case, postcode 2/16/17, lower case and DE with 4 digits, country `XX`, email without `@` and of 256 |
| `limits_contact` | `test32`–`test41` | phone of 15/16 digits, subscriber of 3, extension of 11, `voice-1`, no phone (R), 2 localizations, a link, `authdata` 5/17 |
| `limits_host` | `test1`–`test12` | label 63/64, name 253/254, 13/14 addresses by create and by update, `256.0.0.1`, a private address, uncompressed IPv6, both client statuses, a status twice |

Expected answers follow core Table 9: a value the proxy can tell is wrong is 400 `02001` or `02005`, a value a
server's policy refuses is 422 `02306`, and a count over a limit is 422 `02306`. Several probes are expected to fail
on the current code, which is their purpose:

- **E cuts values instead of refusing them** (MariaDB without `STRICT_*`): a 61–63 character label under `.example`
  is stored as 68 characters and answers 201 (`test2`, `test4`); `name.full` of 256 is cut to 255 (pawel-kow/epp#21).
- **E counts nameservers, contacts per role and host addresses per command**, so the update probes (`test20`,
  `test25`, `limits_host/test7`) are expected to pass where create refuses.
- **R refuses many over-limit values in its XSD** (`83000000004`) or with a class-5 code (`53300102920`, name
  servers out of range), which the proxy maps to 500 `02400` as its own defect. Over-limit handles, city, record
  counts and contacts per domain are expected to answer 500 today, where 4xx is right.

Probes that cost a lot or change shared state need care before they run on MTEST: the 64 KiB request counts against
the ACL like any other, and every probe that creates must use `{handle:a:…}` and `{random_name}` as the suite does.

## 7. Other findings

- **F1.** `tests/integration/test_domain_create.py` and `test_domain_delete.py` collect no test: `test_cases = []`,
  followed by an unassigned list of old cases in a pre-RPP format (`/domains`, `authInfo.pw`). Dead code.
- **F2.** `DC9` and `CC9` are named "invalid schema" but send a body with renamed members, so they prove an unknown
  member and a missing required member at once. A missing `name`, `id`, locality or email has no case of its own.
- **F3.** `DU6` ("invalid_schema") sends a contact without `object` and is EPP-only for no reason of the field; the
  same refusal would hold on RRI with `generalRequest`.
- **F4.** No case creates a domain without `authInfo` (except the 501 in `DL6`), and none creates a domain, contact or
  host with a client status, though the drafts allow both.
- **F5.** `dns` of RRI domains is created in every case (`profile.domain_dns_required`) but never changed: no
  update case replaces, adds or removes a name server or `nsentry` on RRI.

Per [process.md](../agents/process.md#issues), the defects here (F1, the cut values and per-command counts of the
EPP test server, the 500 for RRI limit refusals) belong in GitHub issues, not in this file, once confirmed by the
probes.
