# Integration test review: coverage of the data object fields

Status: 2026-11-14, branch `feature/136-limit-probes` (#136). §2 to §4 show the suite with the probe cases of §6 and
the cases added for the gaps this review found on `main` at 414a86e (§6.3). §6 has the outcomes on both backends,
the EPP test server and DENIC RRI MTEST. Companion file: [backend-limits.yaml](backend-limits.yaml).

This review checks the data-driven integration suite (`tests/integration/test_case_data/`, 515 cases) against
three criteria, for every writable field of the Domain Name, Contact and Host data objects and of the component
objects they carry:

1. **Presence and transitions.** Create with the value and without it; update from absent to present, from one
   value to another, and from present to absent, by full update (PUT) and by partial update (PATCH), within the
   mutability the data-objects draft defines (`create-only` fields must be refused on update).
2. **Arrays and aggregations.** Add an element, remove one, clear the array, fill it to the maximum, and go over the
   maximum.
3. **Value boundaries.** Minimum and maximum length or value, and the allowed character set or format.

Where the drafts leave a boundary undefined, the backend's own limit has to be found by a case that goes over it.
§5 lists the boundaries the drafts leave open, §6 the probe cases for them, and
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
| LD | `limits_domain` | LC | `limits_contact` |
| LH | `limits_host` | | |

A case runs on both backends unless marked **(E)**, the EPP test server only, or **(R)**, RRI MTEST only. Of the
515 cases, 170 run on both, 284 on EPP only, 36 on RRI only and 25 are skipped for a known
defect or a limit of the test environment (§6). All host cases are (E), because RRI has no host objects; the host
tables do not repeat the mark. A case skipped for a defect still counts as covering its point: it asserts what the
drafts require and names the issue.

| Mark | Meaning |
|---|---|
| ✅ | Covered: the transition or boundary is exercised and its outcome asserted |
| ◐ | Partly: on one backend only where both support it, only one of PUT/PATCH, the outcome is not read back, or MTEST lets only the refusal be asserted (§6.3) |
| ❌ | Not covered |
| ➖ | Does not apply (mutability, or a refusal is the whole contract and is covered elsewhere) |
| 501 | The proxy refuses it with 501; the cell names the case that pins the refusal |

## 2. Summary

A point is one mark in the tables below, so a cell with a PUT and a PATCH part counts twice. ✅ includes the
refusals pinned by a 501 case. The figures on `main` at 414a86e are in brackets; the number of points changed where
a cell was split by backend or method, or a ❌ turned out not to apply (➖).

| Object | Points | ✅ | ◐ | ❌ |
|---|---|---|---|---|
| Domain: presence and transitions (§3.1) | 103 (108) | 91 (63) | 12 (7) | 0 (38) |
| Domain: arrays (§3.2) | 46 (50) | 37 (11) | 7 (1) | 2 (38) |
| Domain: boundaries (§3.3) | 28 (27) | 26 (9) | 0 (0) | 2 (18) |
| Contact: presence and transitions (§3.4) | 108 (113) | 100 (69) | 7 (7) | 1 (37) |
| Contact: arrays (§3.5) | 33 (33) | 32 (18) | 1 (1) | 0 (14) |
| Contact: boundaries (§3.6) | 32 (29) | 26 (7) | 1 (1) | 5 (21) |
| Host: presence and transitions (§4.1) | 48 (47) | 45 (36) | 3 (3) | 0 (8) |
| Host: arrays (§4.2) | 13 (13) | 13 (8) | 0 (0) | 0 (5) |
| Host: boundaries (§4.3) | 9 (9) | 9 (4) | 0 (0) | 0 (5) |
| **All** | **420** (429) | **379** (225) | **31** (20) | **10** (184) |

The suite is strong on **transitions of the EPP mapping**: PUT versus PATCH, `match` semantics, refusals of what EPP
cannot express (501), and the proof of absence by a 422 `02308` `match`. Every limit is now probed on either side
(§6.1, §6.2), every array is filled to its maximum and past it where a backend has one, and every field has at least
one case. What remains open:

- **Delegation changes on RRI.** MTEST checks the name servers of every update, and the cases have none that serve
  their zone, so adding, removing or replacing `ns` and `dnskey` records can only be asserted as a refusal there
  (`DU48`, `DU52`, `DU53`, `DU56`, `DU57`, `DU69`). On the EPP test server `ns` records cannot be added to a domain
  either (pawel-kow/epp#33). A positive case needs name servers that serve the test zones.
- **Dropped boundaries** (§6.4): lengths only the EPP test server limits (and cuts, pawel-kow/epp#21), a `uName`
  valid in IDNA2003 only, the Bidi rule, the length of a DNSKEY key, and the same address record twice.
- `status[].reason` is not read back on either backend (#54), so a change of a reason is not shown.

## 3. Domain Name and Contact

### 3.1 Domain Name: presence and transitions

C+ create with the value, C− create without it, U+ absent → present, U~ change, U− present → absent.

| Field | Mutability | C+ | C− | U+ | U~ | U− |
|---|---|---|---|---|---|---|
| `name` | create-only | ✅ every create | ◐ `DC9` (wrong member name, generic 400) | ➖ | PUT ✅ `DU20` 400 · PATCH ✅ `DU38` 400 | ➖ |
| `uName` | create-only | ✅ `DC24`, read `XD7` | ✅ `DC25` | PATCH ✅ `DU39` 400 | PATCH ✅ `DU65` 400 | ✅ PUT keeps it `DU33`, PATCH keeps it `DU34`(E) |
| `lgr` | create-only | ✅ `DC24`, `DC25` | ✅ `DC26` (IDN without lgr, by env) | PATCH ✅ `DU40` 400 | ➖ (the path is refused whatever the value, `DU40`) | ✅ `DU33` |
| `status` (client labels) | read-write | 501 `DC32`(E) (RFC 5731 create has no status) | ✅ every create | PATCH ✅ `DU12`(E) `DU13`(E) · PUT ✅ `DU22`(E) | PATCH ✅ `DU12`(E) `XP2`(E) `DU34`(E) · PUT ✅ `DU41`(E) | PATCH ✅ `DU14`(E), `replace []` `DU13`(E) · PUT ✅ `DU22`(E) |
| `status[].reason` | create-only in the status | ➖ (`DC32`) | ✅ | PUT ◐ `DU22`(E), not read back (#54) | PATCH ◐ `DU22`(E) | ◐ `DU22`(E) |
| `status[].due` | read-write | 501 `DC33`(E) | ✅ | 501 `DU42`(E) | ➖ (no due can be set) | ➖ |
| `registrant` | read-write | ✅ `DC3`, `DC4`, `DL1` | ✅ `DC1`(E) | PATCH ✅ `DU43`(E) | PATCH ✅ `DU1`(E) `DU4`(E) `XP1`(E) · PUT ✅ `XD8`(E) | PUT ✅ `DU32`(E) · PATCH ◐ (only as the 422 proof in `DU32`) |
| `contacts` | read-write | ✅ `DC3`, `DC4` | ✅ `DC1` | PATCH ✅ `DU1`(E) `DU4`(E) `XP3`(E) `DU37`(R) · PUT ✅ `DU44`(E) | PATCH ✅ `DU17`(E) · PUT ✅ `DU17`(E) | PATCH ✅ `DU4`(E) `DU9`(E) `DU37`(R) · PUT ✅ `DU17`(E) |
| `nameservers` | read-write | ✅ `DC6`(E) `XD5`(E) · 501 `DL6`(R) | ✅ `DC1` | PATCH ✅ `DU3`(E) `DU8`(E) · PUT ✅ `DU17`(E) | PATCH ✅ `DU8`(E) `DU17`(E) `XP4`(E) · PUT ✅ `DU17`(E) | PATCH ✅ `DU3`(E) · PUT ✅ `DU17`(E) (2 → 1) |
| `dns.records` `ns` | read-write | ✅ `DC18`(E), `LD26`(R) | ✅ `DC1` | PUT ✅ `DU29`(E) · PATCH ✅ `DU47`(E, skip pawel-kow/epp#33) | PUT ◐ `DU48`(R, refusal) | PATCH ◐ `DU15`, `DU53`(R, refusal) |
| `dns.records` `a`/`aaaa` | read-write | ✅ `DC1` (`a`, R fixture), `DC5`, `LD29`(R) | ✅ `DC1`(E) | PATCH ✅ `DL2`(R) · PUT ✅ `DU51`(R) | PUT ✅ `DU50`(R) | PATCH ✅ `DU49`(R) · PUT ◐ `DU48`(R, refusal) |
| `dns.records` `mx` | read-write | ✅ `DC40`(R), null MX `LD32`(R) | ✅ | PATCH ✅ `DU54`(R) | PATCH ✅ `DU68`(R) | PATCH ✅ `DU55`(R) |
| `dns.records` `ds` | read-write | ✅ `DC16`(E), refused next to `dnskey` `DC21`(E) | ✅ | PATCH ✅ `DU58`(E) | PATCH ✅ `DU16`(E) `DU23`(E) · PUT ✅ `DU24`(E) | PUT ✅ `DU23`(E) · PATCH ✅ `DU59`(E) |
| `dns.records` `dnskey` | read-write | ◐ `DC17`(E, refused: the server takes DS records only) · ✅ `LD37`(R) | ✅ | PATCH ◐ `DU56`(R, refusal) | PUT ◐ `DU69`(R, refusal) | PUT ◐ `DU57`(R, refusal) |
| `dns` with `nameservers` | — | ✅ `DC19`(E) 400 | ➖ | PUT ✅ `DU25`(E) 400 | ➖ | ➖ |
| `dns.controls.ttl` | read-write | 501 `DC20` | ✅ | PUT 501 `DU28` | ➖ | ➖ |
| `dns.controls.maxSigLifetime` | read-write | 501 `DC39` | ✅ | PATCH 501 `DU64` | ➖ | ➖ |
| `authInfo` | read-write (immutable object) | ✅ every create, read `DU26`(E) | ✅ `DC34`(E), 400 `02003` (RFC 5731 requires it) | ➖ | PATCH ✅ `DU1`(E) `DU2` `DL4` · PUT ✅ `DU26`(E) `XD8`(E) | PUT omitted keeps it ✅ `DU26`(E) · PATCH ✅ `DU60`(E) |
| `processes.createProcess[].period` | create input | ✅ `DC2`(E) `XD5`(E) | ✅ `DC1` | ➖ | ➖ | ➖ |
| `provMetadata`, `expiryDate`, `subordinateHosts` | read-only | read ✅ `DT1`(E), `DR6`(E), `DC23`(E); write refused ✅ `DC41` | ➖ | write refused: PATCH ✅ `DU61` · PUT ✅ `DU62` | ➖ | ➖ |

### 3.2 Domain Name: arrays and aggregations

| Array | Add | Remove | Clear | At maximum | Over maximum | Duplicate |
|---|---|---|---|---|---|---|
| `status` | ✅ `DU12`(E) | ✅ `DU14`(E) `DU22`(E) | ✅ `DU13`(E) | ✅ `LD12`(E) | ✅ server label `DU21`, unknown label `DU66`(E) | ✅ `LD13`(E) |
| `contacts` (per label) | ✅ `DU1`(E) `DU4`(E) `DU37`(R) | ✅ full match `DU4`(E), partial `DU9`(E), `DU37`(R) | ✅ `DU45`(E) | ✅ `LD17`(E) | ✅ `LD18`(E), by update `LD19`(E, skip pawel-kow/epp#29), 2nd abuse `LD20`(R, skipped: one REQUEST handle) | ✅ `LD55`(E, skip pawel-kow/epp#32) |
| `contacts` unknown label | ➖ | ➖ | ➖ | ➖ | ✅ `LD21` | ➖ |
| `contacts` match | ➖ | ✅ none matches `DU10`(E), ambiguous `DU11`(E) | ➖ | ➖ | ➖ | ➖ |
| `registrant` (RRI holders) | ✅ `DL3`(R) | ✅ `DU67`(R) | ➖ | ✅ `LD14`(R) | ✅ `LD15`(R, skip #140) | ✅ `LD16`(R) |
| `nameservers` | ✅ `DU3`(E) `DU8`(E) | ✅ `DU3`(E) | ✅ `DU46`(E) | ✅ `LD22`(E) | ✅ `LD23`(E), by update `LD24`(E, skip pawel-kow/epp#29) | ✅ `LD56`(E) |
| `dns.records` `ns` (RRI Nserver) | ◐ `DU52`(R, refusal) | ◐ `DU53`(R, refusal) | ➖ (required) | ✅ `LD27`(R) | ✅ 14 `LD28`, 1 `LD25`(R, skip #139) | ✅ `LD57`(R) |
| `dns.records` `a`/`aaaa`/`mx` (RRI Nsentry) | ✅ `DL2`(R) `DU54`(R) | ✅ `DU49`(R) `DU55`(R) | ◐ `DU48`(R, refusal) | ✅ `LD29`(R) | ✅ `LD30`(R); `aaaa` without `a` `LD31`(R) | ❌ |
| `dns.records` `ds` | ✅ `DU58`(E) | ✅ `DU59`(E) | ◐ PUT `DU23`(E) | ➖ (no limit on E) | ➖ | ✅ `LD58`(E) |
| `dns.records` `dnskey` (R) | ◐ `DU56`(R, refusal) | ◐ `DU57`(R, refusal) | ◐ `DU57`(R, refusal) | ✅ 5 `LD53`(R) | ✅ 6 `LD54`(R) | ❌ |
| `dns.records` (all, R) | ➖ | ➖ | ➖ | ➖ (20 not reachable, backend-limits.yaml) | ➖ | ➖ |

### 3.3 Domain Name: value boundaries

| Field | Boundary | Covered by |
|---|---|---|
| `name` | label length 63 / 64 (DNS) | ✅ `LD1`–`LD4` (`LD2`, `LD3` do not run on E, pawel-kow/epp#30; `LD4` skip #138) |
| `name` | total length within the DNS limit (E stores 68 characters, R takes 66) | ✅ `LD1`, `LD3` |
| `name` | leading `-`, `--` in positions 3–4, `_` | ✅ `LD5`–`LD7` |
| `name` | upper case input, trailing dot, a TLD the server does not serve | ✅ `LD8`–`LD10` |
| `name` | IDN A-label | ✅ `DC24`–`DC26` |
| `uName` | not matching `name` | ✅ `DC30` |
| `uName` | code point outside the LGR | ✅ `DC29`(E) |
| `uName` | not NFC | ✅ `LD11` |
| `uName` | IDNA2003-only code point, Bidi rule | ❌ (dropped, §6.4) |
| `lgr` | unknown LGR | ✅ `DC28` |
| `lgr` | on an ASCII name | ✅ `DC31` |
| `uName` | without `lgr` | ✅ `DC27` |
| `authInfo.authdata` | length (E 6–16, R 8–16) both sides | ✅ `LD39`–`LD42` |
| `authInfo.authdata` | character set (E needs upper case and digit, R excludes `I O l o 0 1`) | ✅ `LD43`(E), `LD44`(R) |
| `authInfo.method` | other than `authinfo` | ✅ `LD45` |
| `period` | value 0 and 100 (schema 1–99) | ✅ `LD46`, `LD47` |
| `period` | 11 months, 10 and 11 years (E: 1–10 years in whole years) | ✅ `LD48`–`LD50` |
| `renewalPeriod` | 11 months, past 10 years ahead (E) | ✅ `LD51`, `LD52`(E) |
| `ds` `keyTag` | 65535 / 65536 | ✅ `LD33`, `LD34` |
| `ds` `digest` | not hex | ✅ `DC22`(E) |
| `ds` `digestType` | 4 (SHA-384, E cannot store) | ✅ `LD35` |
| `dnskey` | flags 256/257, protocol 3, algorithm list (R) | ✅ `LD37`, `LD38`(R) |
| `dnskey` | `publicKey` length (E 255, R 30–999) | ❌ (dropped, §6.4) |
| `dns.controls` | any value | 501 `DC20`, `DU28`, `DC39`, `DU64` |
| `status.label` | server label on update | ✅ `DU21` |
| `contacts[].object.id` | a contact that does not exist, one of another registrar | ✅ `DC35`, `DU63`; another registrar `DC38`(E) |
| `registrant.id` | a contact that does not exist, one of another registrar | ✅ `DC36`; another registrar `DC42`(E) |
| `nameservers[].hostName` | a host that does not exist | ✅ `DC37`(E) |

### 3.4 Contact: presence and transitions

| Field | Mutability | C+ | C− | U+ | U~ | U− |
|---|---|---|---|---|---|---|
| `id` | create-only | ✅ every create | ◐ `CC9` (wrong members) | ➖ | PUT ✅ `CU10` 400 · PATCH ✅ `CU27` 400 | ➖ |
| `id` read in other case | — | ➖ | ➖ | ➖ | ✅ `CU15` | ➖ |
| `status` (client labels) | read-write | 501 `CC22`(E) (RFC 5733 create has no status) | ✅ | PATCH ✅ `CU19`(E) · PUT ✅ `CU6`(E) | PUT ✅ `CU54`(E) | PATCH ✅ `CU19`(E) · PUT ✅ `CU6`(E) · `replace []` ✅ `CU53`(E) |
| `status[].reason` | create-only in the status | ➖ (`CC22`) | ✅ | PUT ◐ `CU7`(E), not read back | ❌ | ◐ `CU7`(E) |
| `contactInfo.kind` | read-write | ✅ `CC1` individual, `CC2` org | ✅ `CC26` (reads back individual) | ➖ | PUT ✅ `CU2`(E) org → individual, `CU16` org without org 400 · PATCH ◐ `CU35`(R) | ➖ |
| `contactInfo.language` | read-write | ✅ `CC16`(E) | ✅ | ✅ `CU36` | ✅ `CU37` | ✅ `CU38` (stored by neither backend: 422, spec-issues *Localization language*) |
| `contactInfo.name.full` | read-write (R immutable) | ✅ every create | ✅ `CC23` | ➖ | PATCH ✅ `CU18` (E 200, R 422) · PUT ✅ `CU58`(E) | PATCH ✅ `CU20` (E 501, R 422) · PUT ✅ `CU5`, `XC5` 501 |
| `organizations.org.name` | read-write | ✅ `CC2`, `CC3` | ✅ `CC1` | PATCH ✅ `CU24` · PUT ✅ `CU56`(E) | PUT ✅ `CU35`(R) · PATCH ✅ `CU57`(E) | PATCH ✅ `CU25`(E) `CU35`(R) · PUT ✅ `CU2`(E) |
| `addresses` street lines | read-write | ✅ `CC3` (3) | ✅ `CC16`(E) (none), `LC11`(R, skip #139) | ✅ `CU39` | ◐ `XC5` (select by backend) | ✅ `CU40` |
| `addresses` locality | read-write, required | ✅ | ✅ `CC24` 400 | ➖ | PUT ✅ `CU1` · PATCH ✅ `CU45` | ➖ |
| `addresses` region | read-write | ✅ `CC3`(E) | ✅ `CC1` | ✅ `CU41`(E) | PUT ✅ `CU1`(E) | ✅ `CU42`(E) |
| `addresses` postcode | read-write (R required) | ✅ `CC1` | ✅ `CC16`(E) | ✅ `CU43`(E) | PUT ✅ `CU1` | ✅ `CU44`(E) |
| `addresses.countryCode` | read-write, required | ✅ | ✅ `CC40` 400 | ➖ | ◐ `CU5` (`select`) | ➖ |
| `emails.email` | read-write, required | ✅ | ✅ `CC25` | ➖ | PATCH ✅ `CU17` `DL7` · PUT ✅ `CU1` | PATCH ✅ `CU21` (E 501, R 422) |
| `phones.voice` | read-write (R required) | ✅ `CC1` | ✅ `CC16`(E), `LC22`(R) | ✅ `CU51`(E) | PATCH ✅ `CU31` · PUT ✅ `CU1` | PATCH ✅ `CU2`(E) · PUT ✅ `CU2`(E) |
| `phones.voice` extension | read-write | ✅ `CC3` | ✅ | ✅ `CU46` | ✅ `CU47` | ✅ `CU48` |
| `phones.fax` | read-write (E) | ✅ `CC3`(E) | ✅ | ✅ `CU49`(E) | ✅ `CU50`(E) | PATCH ✅ `CU2`(E) · PUT ✅ `CU2`(E) |
| `links` | read-write | 501 `LC24` | ✅ | 501 `CU60` | ➖ | ➖ |
| `localizations` | read-write (E) | ✅ `CC16`(E) `CC20`(E) | ✅ | PUT ✅ `CU33`(E) · PATCH ✅ `CU34`(E) (500, the backend ignores it) | PUT ✅ `CU8`(E) | PUT 501 `CU9`(E) · PATCH 501 `CU32`(E), part of it ✅ `CU8`(E) |
| `authInfo` | read-write | ✅ (E) | ◐ `CU35`(R) | ➖ | PUT ✅ `CU14`(E) · PATCH ✅ `CU23`(E) | PATCH 501 `CU22`(E) · PUT omitted keeps it ✅ `CU14`(E) |
| `disclose` | read-write | 501 `CC21` | ✅ | PUT 501 `CU12` · PATCH 501 `CU30` | ➖ | ➖ |
| `provMetadata` | read-only | read ✅ `CT1`(E) | ➖ | write refused ✅ `CU59` | ➖ | ➖ |

### 3.5 Contact: arrays and maps

| Array or map | Add | Remove | Clear | At maximum | Over maximum | Duplicate |
|---|---|---|---|---|---|---|
| `status` | ✅ `CU19`(E) | ✅ `CU19`(E) | ✅ `CU53`(E) | ✅ `LC5`(E) | ✅ server label `CU55`(E) | ✅ `LC27`(E) |
| street lines (`components` kind `name`) | ✅ `CU39` | ✅ `CU40` | ✅ none at create `CC16`(E) | ✅ 3 `CC3` | ✅ 4 `LC10`(E) (R allows more) | ➖ |
| `components` locality / region / postcode | ➖ | ✅ region `CU42`(E), postcode `CU44`(E) | ➖ | ✅ one each | ✅ two localities `CC39` | ➖ |
| `emails` | ➖ | ✅ refused `CU21` (E 501, R 422) | ➖ | ✅ 1 | `email-1` 501 `CC18` | ➖ |
| `phones` | ◐ `CU31` (adds over an existing voice) | ✅ `CU2`(E) | ✅ `CU52`(E) | ✅ voice and fax `CC3`(E) | ✅ `voice-1` `LC21` | ✅ key and features disagree `CC33`, both features `CC34` |
| `localizations` | ✅ `CC16`(E) | 501 `CU32`(E) | 501 `CU9`(E) | ✅ 1 `CC16`(E) | ✅ 2 `LC23`(E) | ➖ |
| `organizations` | ✅ `CU24` | ✅ `CU25`(E) `CU35`(R) | ✅ `CU35`(R) | ✅ 1 | ✅ `org-1` `CC38` | ➖ |

### 3.6 Contact: value boundaries

| Field | Boundary | Covered by |
|---|---|---|
| `id` | length (E 3–16, R 9–32) both sides | ✅ `LC1`, `LC2` (skip #139) |
| `id` | character set, prefix of another registrar | ✅ `LC4` (skip #139), `LC3` |
| `id` | case on update | ✅ `CU15` |
| `name.full` | US-ASCII in the internationalized form | ✅ `CC19` |
| `name.full` | non-ASCII in a localization | ✅ `CC20`(E) |
| `name.full` | minimum (E 5, R 3) | ✅ `LC8`, `LC9` |
| `name.full` | maximum 255 / 256 (E cuts it, pawel-kow/epp#21) | ✅ `LC6`, `LC7` (does not run on E; skip #139) |
| `name.full` | punctuation outside E's set (`'`), a character outside the BMP in a localization | ✅ `CC31`(E) and `CC44`(R), `CC41`(E) |
| `name.full` | RRI completeness rules (digits only) | ✅ `CC32`(R), `CC45`(E) |
| `organizations.org.name` | minimum (E 5) and maximum 255 | ❌ (dropped, §6.4) |
| street line | minimum (E 5) and maximum 255 | ❌ (dropped, §6.4) |
| locality | maximum (R 80) | ✅ `LC12`, `LC13` (skip #139) |
| locality | minimum (E 4), a digit (E refuses) | ❌ (dropped, §6.4) |
| region | lower case first letter (E refuses) | ✅ `CC28`(E) |
| postcode | maximum (E 16, R 20), lower case (E refuses), DE with 4 digits (R) | ✅ `LC14`, `CC29`(E) and `CC42`(R), `CC30`(R) and `CC43`(E) |
| postcode | minimum (E 3) | ❌ (dropped, §6.4) |
| `countryCode` | lower case (schema), unknown code `XX` | ✅ `CC27`, `LC15` |
| email | without `@` | ✅ `LC16` |
| email | over 255 | ❌ (dropped, §6.4) |
| phone | hyphens | ✅ `CC17` |
| phone | 15 and 16 digits, subscriber of 3 digits (R needs 4), extension over 10 digits (E stores int(10)) | ✅ `LC17`, `LC18`, `LC19`, `LC20` (does not run on E) |
| phone | extension present | ✅ `CC3` |
| `features` | key and features that disagree, both features | ✅ `CC33`, `CC34` |
| `kind` | `org` without organisation | ✅ `CU16` |
| `kind` | individual with organisation | ◐ `XC2`, `CU35`(R) |
| `authInfo.authdata` | length (E 6–16) and character rule both sides | ✅ `LC25`, `LC26`(E) |
| `localizations` key | not a BCP 47 tag | ✅ `CC35`(E) |
| `version` | other than `2.0` | ✅ `CC36` |
| undeclared member | in `name` | ✅ `CU11`, `CU29` |
| unknown JSContact property | e.g. `nicknames` | ✅ `CC37` |
| `contactInfo` | missing locality, email, name, country code | ✅ `CC24`, `CC25`, `CC23`, `CC40` |
| `contactInfo` | RRI without phone | ✅ `LC22` |

## 4. Host (EPP only)

### 4.1 Presence and transitions

| Field | Mutability | C+ | C− | U+ | U~ | U− |
|---|---|---|---|---|---|---|
| `hostName` external | read-write | ✅ `HC1` | ➖ required | ➖ | ✅ `HU38` | ➖ |
| `hostName` internal | read-write | ✅ `HC3`, without its domain `HC4` 404 | ➖ | ➖ | PATCH ✅ `HU4` · PUT ✅ `HU13` | ➖ |
| `status` | read-write | 501 `HC6` | ✅ | PATCH ✅ `HU1` · PUT ✅ `HU10` | PUT ✅ `HU39` | PATCH ✅ `HU2` `HU23` · `replace []` ✅ `HU22` · PUT ✅ `HU12` |
| `status[].reason` | create-only in the status | ➖ | ✅ | PATCH ◐ `HU18` · PUT ◐ `HU19`, read back skipped `HU17` (#54) | PUT ◐ `HU20` | ✅ `HU12` |
| own `ns` record | required | ✅ `HC1` | ✅ `HC11`, `HC12` 400 | PATCH ✅ `HU36` 400, `HU37` | ➖ | PATCH 501 `HU34`, `HU35` · PUT ✅ `HU33` 400 |
| `a` record | read-write | ✅ `HC2`, `HC3` | ✅ `HC1` | PATCH ✅ `HU3` `HU16` · PUT ✅ `HU10` | PATCH ✅ `HU9` `HU21` · PUT ✅ `HU11` | PATCH ✅ `HU16` `HU26` · PUT ✅ `HU43` |
| `aaaa` record | read-write | ✅ `HC2` | ✅ `HC1` | PATCH ✅ `HU26` · PUT ✅ `HU40` | PUT ✅ `HU41` | PATCH ✅ `HU44` · PUT ✅ `HU42` |
| record of another type or name | — | 501 `HC8`, `HC9` | ➖ | 501 `HU45` | ➖ | ➖ |
| `dns` as a whole | read-write | ✅ | ✅ `HC11` | ➖ | ➖ | 501 `HU27` |
| `dns.controls` | read-write | 501 `HC7`, `XH2` | ✅ | 501 `HU28` | ➖ | ➖ |
| `provMetadata` | read-only | read ✅ `HG4` | ➖ | ✅ refused `HU8` | ➖ | ➖ |

### 4.2 Arrays

| Array | Add | Remove | Clear | At maximum | Over maximum | Duplicate |
|---|---|---|---|---|---|---|
| `status` | ✅ `HU1` | ✅ `HU2` | ✅ `HU22` | ✅ `LH11` | ✅ server label `HU29`, unknown label `HU46` | ✅ `LH12` |
| addresses | ✅ `HU3` `HU16` `HU26` | ✅ by full match `HU16`, by partial match `HU26` | ✅ `HU44` | ✅ 13 `LH5` | ✅ 14 by create `LH6`, by update `LH7` (skip pawel-kow/epp#29) | ✅ `HU32` 422 |
| `match` | ➖ | ✅ none matches `HU24`, ambiguous `HU25` | ➖ | ➖ | ➖ | ➖ |

### 4.3 Value boundaries

| Field | Boundary | Covered by |
|---|---|---|
| `hostName` | label 63 / 64, name 253 / 254 | ✅ `LH1`–`LH4` |
| `hostName` | character set, upper case input | ✅ `HC14`, `HC13` |
| `a` address | IPv6 in an `a` record | ✅ `HC10` |
| `a` address | `256.0.0.1`, private and reserved ranges | ✅ `LH8`, `LH9` |
| `aaaa` address | uncompressed form | ✅ `LH10` (skip #137) |
| PATCH | empty patch | ✅ `HU5` |
| PATCH | no change | ✅ `HU30` |
| PUT | no change | ✅ `HU15` |
| `status.label` | unknown label | ✅ `HU46` |

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

## 6. Probe and gap cases

What the drafts define is the oracle (DNS lengths, the 15 digits of a phone number, the period of 1 to 99,
ISO 3166-1, RFC 5322, US-ASCII, the mutability rules of json §4.4); a limit they leave to the server is expected to
be refused with 400 (`02001`, `02004`, `02005`) or 422 (`02306`), never 500 or 501. A duplicate the drafts leave
open may also be taken, or refused with 409 (`02302`). Limits that differ by server are facts of the environment,
such as `contact.city.max_length` (testing.project.md, *Selectors* and *Limits*). Each limit and its cases are in [backend-limits.yaml](backend-limits.yaml),
with the outcome per backend under `verified`.

### 6.1 Probes of the limits

The limits are probed by 97 cases in `limits_domain/` (58), `limits_contact/` (27) and `limits_host/` (12).
Each limit gets the value at it and the value past it, so a change of the backend shows as a failure of exactly one
of the two.

| Group | Cases | Limits |
|---|---|---|
| `limits_domain` | `test1`–`test11` | label of 60/61/63/64, leading hyphen, `_`, `--` in positions 3–4, trailing dot, other TLD, upper case, `uName` not NFC |
| `limits_domain` | `test12`–`test21` | all client statuses, a status twice, 5/6 holders and one holder twice (R), 5/6 tech contacts by create and a 6th by update (E), a 2nd abuse contact (R), an unknown label |
| `limits_domain` | `test22`–`test32` | 13/14 nameservers and a 14th by update (E), 1/2/13/14 `ns` records (R), 5/6 address records, `aaaa` without `a`, a null MX (R) |
| `limits_domain` | `test33`–`test38` | `keyTag` 65535/65536, `digestType` 4, two DS records (E), DNSKEY flags 256 and algorithm 9 with two `ns` records (R) |
| `limits_domain` | `test39`–`test52` | `authdata` at and under the minimum, 16/17, without a digit (E), with `O` (R), unknown `method`, `period` 0/100/11 months/10 and 11 years, renew of 11 months and past 10 years (E) |
| `limits_domain` | `test53`–`test58` | 5/6 DNSKEY records (R); one tech contact, nameserver (E), `ns` record (R) or DS record (E) given twice |
| `limits_contact` | `test1`–`test5` | `id` at and over the maximum (E 16, R 32), prefix of another registrar, `_`, all client statuses |
| `limits_contact` | `test6`–`test16` | `name.full` 255/256 and at and under the minimum (E 5, R 3), 4 street lines (E) and none (R), city 80/81, postcode 16, country `XX`, email without `@` |
| `limits_contact` | `test17`–`test27` | phone of 15/16 digits, subscriber of 3 digits (R), extension of 11 digits, `voice-1`, no phone (R), 2 localizations, a link, contact `authdata` 5/17 (E), a status twice (E) |
| `limits_host` | `test1`–`test12` | label 63/64, name 253/254, 13/14 addresses and a 14th by update, `256.0.0.1`, a private address, uncompressed IPv6, both client statuses, a status twice |

### 6.2 Outcome of the probes

On the EPP test server:

| Case | Expected | Got | Issue |
|---|---|---|---|
| `limits_domain/test4`, `limits_host/test2` | 400 for a label of 64 | 422 `02306` from the registry (domain); host as expected | #138 |
| `limits_domain/test19`, `test24`, `limits_host/test7` | 4xx for a 6th tech contact, a 14th nameserver, a 14th address added by update | 200: limits counted per command | pawel-kow/epp#29 |
| `limits_domain/test2`, `test3` (do not run there) | 201 for a label of 61 to 63 | the name is cut to 68 characters, the server dies and the proxy times out (500 `02400`) | pawel-kow/epp#30 |
| `limits_domain/test55` | 4xx, or 201 with the contact once, for one tech contact given twice | no reply, 500 `02400` after the read timeout | pawel-kow/epp#32 |
| `limits_contact/test20` (does not run there) | the extension read back whole | 11 digits read back as 2147483647 | pawel-kow/epp#31 |
| `limits_contact/test7` (does not run there) | 4xx for a name of 256 | 201, cut to 255 | pawel-kow/epp#21 |
| `limits_host/test10` | `2001:db8::1` (RFC 5952) | `2001:0db8::1` | #137 |

A nameserver given twice is refused with 409 `02302` (`limits_domain/test56`), a DS record given twice with 422
`02306` (`test58`), DS digest type 4 with 422 `02306` (`test35`), and a DNSKEY at create with 422 `02306`
(`domain_create/test17`: the server takes DS records only); a private host address is taken (`limits_host/test9`).
A status given twice in one PATCH is taken for a domain and a contact (`limits_domain/test13`,
`limits_contact/test27`: the proxy sends the end state) and refused for a host (`limits_host/test12`: the proxy
sends both adds, the server answers 2306 for the second). `limits_domain/test55` expects a contact given twice to be
refused like a nameserver, 409 `02302`.

Confirmed limits of the EPP test server: labels up to 60 under `.example`, 13 nameservers and 5 contacts a role at
create, 13 host addresses at create, `keyTag` up to 65535, `authdata` of 6 to 16 characters with an upper case letter
and a digit, contact ids of 16, names of at least 5 characters, cities of 80 and postcodes of 16, phone numbers of 15
digits, periods of 1 to 10 whole years and an expiry at most 10 years ahead.

`limits_contact/test2` and `test4` passed on the EPP test server but are skipped on both backends for #139, since a
skip cannot be limited to one backend.

On RRI MTEST (2026-11-12, and the new cases on 2026-11-14), the first run failed 11 cases:

| Case | Expected | Got | Outcome |
|---|---|---|---|
| `limits_contact/test2`, `test4`, `test7`, `test11`, `test13` | 4xx for an id of 33 or with `_`, a name of 256, no street line, a city of 81 | 500 `02400`: RRI refuses them in its XSD (`83000000004`) | defect #139, skipped |
| `limits_domain/test25`, `test28` | 4xx for 1 and 14 `ns` records | 500 `02400`: RRI answers the class-5 code `53300102920` | defect #139, skipped |
| `limits_domain/test15` | 4xx for six holders | 501 `02102` from the proxy | defect #140, skipped |
| `limits_domain/test20` | 4xx for a second abuse contact | 200: on MTEST the abuse and general request handles in `.env` are one handle, so the second add is the same contact again and changes nothing | skipped until a second `REQUEST` handle exists |
| `limits_domain/test31` | 4xx for an `aaaa` record without an `a` record (`docs/rri/`) | 201 | expectation changed to 201 |
| `limits_domain/test37` | 201 for a DNSKEY with flags 256 next to an `a` record | 422 `02306`, RRI `66300048905` "Invalid DNS Data (Nsentry, Dnskey)"; flags 257 is refused the same way | the case now delegates with two `ns` records and passes; `test38` the same, so its refusal is of algorithm 9 |

`docs/rri/` names 20 DNS entries in all and no count of DNSKEY records; MTEST refuses a sixth DNSKEY
(`66300068807` "too many dnskeys", 422 `02306`, `limits_domain/test54`) and a key that is not a valid key of its
algorithm the same way. An `ns` record given twice is taken (`test57`).

Confirmed limits of RRI MTEST: labels up to 63 under `.de`, 1 to 5 holders, all different, 2 to 13 `ns` records, 1 to
5 address records of the domain itself and an `aaaa` record without an `a` record, a null MX, 1 to 5 DNSKEY records
only with name servers, flags 256, algorithm 9 refused, `authdata` of 8 to 16 characters without `I O l o 0 1`,
contact ids of 32, names of at least 3 characters, cities of 80, a postcode required, a subscriber number of at least
4 digits, one voice number required.

### 6.3 Cases for the gaps

113 cases close the gaps §3 and §4 showed on `main`: `domain_create/test32`–`test42`, `domain_update/test38`–`test69`,
`limits_domain/test53`–`test58`, `contact_create/test21`–`test45`, `contact_update/test36`–`test60`,
`limits_contact/test27`, `host_create/test13`–`test15`, `host_update/test38`–`test46` and `host_get/test4`. They
assert what the drafts require: a create-only or read-only member in an update, an undeclared member, a key the
JSContact profile does not have and a value outside a schema pattern are 400 `02001` (json §4.4); a member EPP or RRI
has no place for is 501 `02102`; a change is read back, and a removal is proven by a `match` that answers 422 `02308`
(testing.project.md, *Isolating cases*). Where the drafts leave the answer to the registry, each case pins the answer
of one server: where the two backends decide differently, there is one case for each, selected by an `env` fact of
server policy (`contact.region.lower_case_supported`, `contact.postcode.lower_case_supported`,
`contact.postcode.format_by_country`, `contact.name.charset_restricted`, `contact.name.digits_only_supported`,
`domainName.contacts.foreign_supported`, `domainName.dns.dnskey_supported`). No case accepts a success and a refusal at once. The answers:

| Case | EPP test server | RRI MTEST |
|---|---|---|
| `domain_create/test32`, `contact_create/test22` (a status at create) | 501 `02102`: the create commands have no status | — |
| `domain_create/test34` (no authInfo) | 400 `02003` from the registry: RFC 5731 requires it | — |
| `domain_create/test35`, `test36`, `test37`, `domain_update/test63` (a contact, registrant or host that does not exist) | 404 `02303` | 409 `02305` (`53000060009`) |
| `domain_create/test38`, `test42` (a contact or registrant of another registrar) | 403 `02201` | — |
| `contact_create/test23` (no name) | 400 `02003` from the registry | 422 `02306` (`63200040810`) |
| `contact_create/test25` (no email) | 400 `02005`: the proxy sends an empty email | 422 `02306` (`63200041610`) |
| `contact_create/test24`, `test40` (no locality, no country code) | 400 `02001` (schema) | 400 `02001` |
| `contact_create/test28`, `test29`, `test31`, `test41` (lower case region or postcode, `'` or a character outside the BMP in a name) | 400 `02005` | — |
| `contact_create/test42`, `test44` (lower case postcode, `'` in a name) | — | taken (201) |
| `contact_create/test30`, `test32` (DE postcode of 4 digits, name of digits) | — | 422 `02306` (`63400000004`, `63400000001`) |
| `contact_create/test43`, `test45` (DE postcode of 4 digits, name of digits) | taken (201) | — |
| `contact_create/test35`, `test37`, `test38`, `test39` (localization key not BCP 47, `nicknames`, `org-1`, two localities) | 400 `02001` (schema) | 400 `02001` (`test35` does not run there) |
| `host_create/test14` (`_` in a host name) | 400 `02005` from the registry | — |
| `host_create/test15` (an invalid IPv6 address) | 400 `02001` from the proxy | — |

Three groups of transitions cannot pass on a backend for a reason of the server, so their cases are skipped there:

| Case | Expected | Got | Issue |
|---|---|---|---|
| `domain_update/test47` (E) | 200 for `ns` records added to a domain without delegation | 400 `02005` "Invalid domain:hostName": the server refuses a `hostAttr` without addresses | pawel-kow/epp#33 |
| `domain_update/test52`, `test53`, `test56` (R) | the refusal of MTEST below | 501 `02102` "'due' cannot be expressed in RRI": the domain reads back `inactive` with a `due`, which the proxy refuses in a PATCH | #143 |
| `domain_update/test48`, `test57`, `test69` (R) | 4xx: MTEST checks the delegation of an update, and the name servers of the cases do not serve the zone | 500 `02400`: class-5 `53300102912` "Nameserver error" | #139 |

So on RRI a change of `ns` or `dnskey` records is asserted only as a refusal; the changes of `a`, `aaaa` and `mx`
records (`domain_update/test49`–`test51`, `test54`, `test55`, `test68`) pass and are read back.

Two expectations of the first outline were wrong and were corrected before the run: a JSON Patch reaches an array
element by `match`, not by index or `-` (json §5.2.2: "the path must point to an existing property"), and the list of
records or address components is compared whole, so the cases read back every element.

### 6.4 Dropped

Dropped from the outline: a label of 1 (no name of one character is unique between runs), a `uName` valid in IDNA2003
only and the Bidi rule (the LGR of both backends refuses the code points first), 21 RRI records (13 `ns` and 5 DNSKEY
records are the most, and an address record cannot go with a DNSKEY), a request over 64 KiB, a dot in a contact id,
a city with a digit or under 4 characters, organisation and street lengths, a postcode under 3 or of 17 characters
and an email of 256 (only the EPP test server limits them, and it cuts them, pawel-kow/epp#21), the length of a
DNSKEY key (it follows from the algorithm, and MTEST checks the key), the same address or DNSKEY record twice, and a
change of a status reason (not read back, #54).

## 7. Other findings

- **F1.** `tests/integration/test_domain_create.py` and `test_domain_delete.py` collect no test (#141).
- **F2.** `DC9` and `CC9` are named "invalid schema" but send a body with renamed members, so they prove an unknown
  member and a missing required member at once. A missing name, locality, email and country code now have cases of
  their own (`CC23`–`CC25`, `CC40`); a missing domain `name` or contact `id` has none.
- **F3.** `DU6` ("invalid_schema") sends a contact without `object` and is EPP-only for no reason of the field; the
  same refusal would hold on RRI with `generalRequest`.
- **F4.** A PATCH of an RRI domain whose name servers failed the predelegation check is refused with 501, because
  the proxy refuses the `due` of the server status `inactive` (#143).
- **F5.** A contact created without email reaches the EPP registry with an empty email and is refused as a syntax
  error (400 `02005`), where RFC 5733 would make it a missing parameter (`02003`). The drafts do not say which.
