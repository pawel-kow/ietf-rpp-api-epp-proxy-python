# RRI gap analysis

This document maps every DENIC RRI 5.0 transaction to the proxy's existing interfaces: the RPP operations in
[openapi.yaml](../../src/openapi.yaml) and the internal model in [models/](../../src/models/). It also lists what the
proxy offers today that RRI cannot serve, and what RRI offers that RPP cannot express.

The RRI facts come from [rri-5.0-reference.md](rri-5.0-reference.md), cited as **ref §n**. The structural changes
are in [refactoring.md](refactoring.md). Decisions that are the maintainer's to make are collected in
[Open questions](#7-open-questions). Each one is a point where a wrong assumption would be expensive to unwind
(see [process.project.md](../agents/process.project.md)).

Status: analysis only. No code has been changed.

## 1. Summary

| | Count |
|---|---|
| RRI transactions (ref §6) | 21 |
| …that map to an existing RPP operation with little friction | 9 (LOGIN, LOGOUT, contact CHECK, contact INFO, domain CHECK, domain INFO, domain DELETE, QUEUE-READ, QUEUE-DELETE) |
| …that map, but need new orchestration in the proxy | 7 (contact CREATE/UPDATE, domain CREATE/UPDATE/CHHOLDER, CREATE-AUTHINFO1, DELETE-AUTHINFO1) |
| …that map only after a maintainer decision | 2 (CHPROV, RESTORE) |
| …that have no RPP operation | 3 (CREATE-AUTHINFO2, TRANSIT, regacc INFO) |
| RPP operations the proxy implements over EPP that RRI cannot serve | hosts (all 7), contact delete, contact transfer (6), domain renew, domain transfer query/cancel/approve/reject |

The main findings:

1. **No host objects.** RRI holds name servers as attributes of the domain (`Nserver`, with glue). Every
   `/hosts` operation answers 501 on RRI, and domain `nameservers` (host references) must be sent as attributes.
2. **Updates replace the whole object.** A domain or contact UPDATE in RRI replaces the object, and an omitted
   optional value is deleted (ref §3.1, §6.4, §6.8). The proxy's flows produce EPP add/remove/change deltas. Every
   RRI update therefore needs a read first and must send the full object, and that includes a PATCH that EPP
   can send without a read.
3. **A holder change is a different command.** The registrant changes through CHHOLDER, not UPDATE. An UPDATE
   whose holders differ from the stored ones fails (`54300062506`).
4. **AuthInfo is a separate command.** The domain `authInfo` is not a domain attribute. Setting it is
   CREATE-AUTHINFO1, which carries a SHA-256 hash with a lifetime of at most 30 days. Clearing it is DELETE-AUTHINFO1.
   RRI never returns the secret.
5. **Transfer happens at once and carries the whole domain.** CHPROV is immediate, cannot be rejected, and has no
   pending state. It needs the complete domain data with contact handles that belong to the *gaining* registrar.
   RPP's transfer request carries none of this (§4.3).
6. **No renewal and no expiry.** Domains run until deleted. Renew answers 501, and `expiryDate` is never read.
7. **NIS2 data has no place in RPP.** Contact verification blocks, risk deadlines, and the
   `pendingCreate`/`serverHold` lifecycle are central to RRI 5.0. Of these, RPP can carry only the two status labels.
8. **Result codes.** RRI uses 11-digit DENIC codes, and the outcome (`success`/`failed`) is separate from the
   messages. A `success` can carry errors, for example a domain created in status `failed`. The proxy's
   `ResultCode` and the core §18.1 HTTP mapping need a translation table (§5).

## 2. Mapping by RRI transaction

Legend for **Fit**: ✅ direct; 🟡 maps, with new orchestration or partial data; 🟠 needs a maintainer decision;
⛔ no RPP operation.

| RRI transaction (ref) | RPP operation(s) | Fit | Notes |
|---|---|---|---|
| LOGIN (§6.1) | HTTP Basic → session (`EppSessionAuthenticator`) | ✅ | User and password are passed through, as for EPP. The RRI user is a login handle (`DENIC-1000022-RRI`), not the RegAccId, see §4.6. 10 failed logins block the user for 1 h, see §6. |
| LOGOUT (§6.2) | session teardown | ✅ | |
| contact CREATE (§6.3) | `contacts_create` | 🟡 | See §3.2 for the Card mapping. The response has no data, so a follow-up INFO is needed, as with EPP. |
| contact UPDATE (§6.4) | `contacts_update` (PUT), `contacts_updatePartial` (PATCH) | 🟡 | Full replacement: always INFO, then the complete UPDATE. `Name` is immutable (`63220080801`). |
| contact CHECK (§6.5) | `contacts_availability`, `contacts_availabilityHead` | ✅ | `free` → available. `exist`/`invalid` → not available. Only works on your **own** handles. |
| contact INFO (§6.6) | `contacts_read` | 🟡 | Own contacts only. No creation date, no sponsor, no status, see §3.2. |
| domain CREATE (§6.7) | `domainNames_create` | 🟡 | See §3.1. Can end in `failed` or `pendingCreate` with result `success`. `authInfo` needs a second command. |
| domain UPDATE (§6.8) | `domainNames_update`, `domainNames_updatePartial` | 🟡 | INFO first, then the complete UPDATE. Not for holder changes. |
| domain CHHOLDER (§6.9) | `domainNames_update`/`updatePartial` when `registrant` changes | 🟡 | Carries all domain data like UPDATE. Invalidates all AuthInfos. |
| domain DELETE (§6.10) | `domainNames_delete` | ✅ | Moves to `redemptionPeriod` (30 days). The optional `Holder` cross-check is not used. |
| domain RESTORE (§6.11) | `domainNameRestoreProcesses_create` | 🟠 | One step, no restore report. The EPP proxy does not implement restore today (501). See Q6. |
| domain TRANSIT (§6.12) | — | ⛔ | Hands the domain to DENIC. Closest RPP is a push transfer to DENIC, see Q8. |
| domain CHECK (§6.13) | `domainNames_availability`, `domainNames_availabilityHead` | ✅ | `free` → available. Every other status → not available, with the status as `reason`. Accepts the U-label and the A-label, see §3.1. |
| domain INFO (§6.14) | `domainNames_read`, plus each read-back | 🟡 | `recursive=false` for reads. `RPP-Authorization` → `AuthInfo` for foreign domains. See §3.1 for the fields. |
| domain CREATE-AUTHINFO1 (§6.15) | `authInfo` in domain create, PUT and PATCH | 🟡 | The proxy hashes `authdata` (SHA-256, hex) and sends `AuthInfoHash`. Lifetime is ≤ 30 days, see Q4. |
| domain DELETE-AUTHINFO1 (§6.16) | removing `authInfo` in PUT and PATCH; replacing it (delete, then create) | 🟡 | Only one AuthInfo1 per domain, so a change is DELETE then CREATE, which is not atomic. |
| domain CREATE-AUTHINFO2 (§6.17) | — | ⛔ | Any registrar asks DENIC to post a code to the holders. Nothing in RPP fits, see Q9. |
| domain CHPROV (§6.18) | `domainNameTransferProcesses_transferCreate` (pull, with `RPP-Authorization`) | 🟠 | Immediate. Needs complete domain data with the gainer's handles, see §4.3 and Q3. |
| regacc INFO (§6.19) | `organisations_read`? | ⛔ | Public registrar data. `/organisations` is 501 in the proxy today, see Q10. |
| QUEUE-READ (§6.20) | `messages_query`, `messages_read` | ✅ | Oldest message. `Msgcnt` → `RPP-Queue-Size`. The `msgType` filter could serve the RPP `type` parameter, see §3.4. |
| QUEUE-DELETE (§6.21) | `messages_delete` | ✅ | Only the oldest message can be deleted (`63650063607`), as with EPP `poll ack`. |

## 3. Mapping by RPP object

### 3.1 Domain names

**Create (`domainNames_create` → domain CREATE, then CREATE-AUTHINFO1 if `authInfo`, then INFO)**

| RPP `domainName.create` | RRI | Gap |
|---|---|---|
| `name` | `Domain-Ace` (A-label) and `Domain` | RRI takes the U-label in `Domain`. The proxy sends `uName` there when given, or else the A-label. |
| `uName` | `Domain` | EPP needs the IDN extension for this. RRI takes it natively. |
| `lgr` | — | DENIC has one fixed character repertoire (ref §5.2). Accept no `lgr`, or one configured name, see Q11. |
| `registrant` | `Holder` (1) | RRI allows 1–5 holders. RPP has one `registrant`, so a create sends one holder. See §4.4 for reading several. |
| `contacts[label]` | `GeneralRequest` / `AbuseContact` (REQUEST handles) | RPP labels are open. Proposal: `generalRequest` and `abuse`. `admin`, `tech` and `billing` do not exist in RRI → 501 (`NotSupportedByBackend`). See Q2. |
| `nameservers[]` (host references) | `Nserver: <host>` (2–13) | There is no host object to reference, so the name becomes an attribute. In-bailiwick hosts need glue, which a reference does not carry, so DENIC refuses them (`53300102902`). |
| `dns.records` `ns` + glue `a`/`aaaa` | `Nserver: <host> <ip>` | Same shape as EPP `hostAttr`. The K/V syntax for several IPs is unverified (ref §14.2). XML (`dnsentry:NS` with `address*` and `addressV6*`) is clear. |
| `dns.records` `a`/`aaaa`/`mx` at the apex or below | `Nsentry` (1–5), instead of `Nserver` | RRI can do this and EPP cannot, so the EPP proxy answers 501 today. It is a new capability. |
| `dns.records` `dnskey` | `Dnskey` (0–20) | DENIC computes the DS. |
| `dns.records` `ds` | — | Not accepted by DENIC → 501. |
| `dns.controls` (TTL, sig lifetime) | — | 501, as with EPP. |
| `status` (client statuses) | — | RRI statuses are set only by the server → 501. |
| `authInfo` | CREATE-AUTHINFO1 after the create | This takes two commands and is not atomic. See Q4 for the hash, lifetime and charset (8–16 characters from `authinfo-val`). |
| `processes.createProcess.period` | — | No registration period → 501. |

The response is built as the proxy builds it today: a read-back with INFO, or 202 if the read-back fails. New
cases to define:

- **Result `success` with status `failed`** (predelegation check failed). The domain exists but is not in the zone,
  and it is deleted after 30 days unless fixed. Proposal: answer 201 with status `inactive` and a `due` date. Q5
  covers this and the warning text.
- **Status `pendingCreate`** (NIS2 risk assessment pending). RPP has the status label `pendingCreate`. Whether the
  create answers 201 or 202 is the same question as [spec-issues.md](../../.spec/spec-issues.md#pending-operations-and-202).

**Read (`domainNames_read` → domain INFO, `recursive=false`, with `AuthInfo` from `RPP-Authorization` if given)**

| RPP `domainName.read` | RRI INFO | Gap |
|---|---|---|
| `name`, `uName` | `domain:ace`, `domain:handle` | |
| `status` | `Status` + `RegistryLock` | Mapping in §3.5. |
| `provMetadata.spClientId` (required) | `regAcc/regAccId` | Present for own and foreign domains. |
| `provMetadata.crDate` | `RegistrationDate` | This is a string that can read `before 2011-05-31…`. Such a value is not a date-time, so it is left out. |
| `provMetadata.upDate` | `Changed` | |
| `provMetadata.repositoryId`, `crClientId`, `upClientId`, `trDate` | — | Not present, so left out. |
| `registrant`, `contacts` | `[Holder]`, `[General Request]`, `[Abuse Contact]` (handles) | Handles appear only on your own domain. For a foreign domain they are missing even with an AuthInfo. See §4.4 for several holders. |
| `nameservers` / `dns` | `Nserver` → `ns` records with glue; `Nsentry` → `a`/`aaaa`/`mx`; `Dnskey` → `dnskey` | RRI name servers are always attributes, so a read always produces `dns.records` and never `nameservers`. A client that wrote `nameservers` reads back `dns`, see Q12. |
| `expiryDate` | — | None. `Expire` (deletion date of a `failed` domain) is not an expiry, see §3.5. |
| `authInfo` | `AuthInfo1`/`AuthInfo2` expiry dates; `AuthInfo: true` | RRI never returns the secret. Left out. |
| `subordinateHosts` | — | No hosts. |
| — | `VerificationDeadlineBefore…`, `[Dispute]`, verification blocks, `[RegAcc]` details | No place in RPP, see §4.5. |

**Update (`domainNames_update` PUT, `domainNames_updatePartial` PATCH)**

Today `flows/domains.py` turns PUT and PATCH into an EPP `DomainUpdate` delta (add/remove/change), and it reads
first only when it must. RRI needs the full wanted state. The refactoring keeps partial (PATCH) and full (PUT)
updates apart down to the model and the port. RRI implements the full update natively, and derives the partial
one from it ([refactoring.md §3.5](refactoring.md#35-full-and-partial-updates)):

1. INFO (own, `recursive=false`) gives the current domain. On RRI this read is always needed, which includes the
   PATCHes `domain_patch.rpp_to_model` maps without a read today.
2. The wanted state comes from the request. A PUT, or a PATCH applied to the read representation, gives a
   `DomainReplacement`. A direct PATCH gives a delta, which is applied to the current domain.
3. Choose the commands:
   - The holder set changed → **CHHOLDER** with all data.
   - Anything else changed → **UPDATE** with all data. Every GeneralRequest, AbuseContact and Dnskey must be
     sent again, or it is deleted.
   - `authInfo` set → DELETE-AUTHINFO1 if one exists (INFO shows `AuthInfo1:`), then CREATE-AUTHINFO1.
     `authInfo` removed → DELETE-AUTHINFO1. A CHHOLDER already removes all AuthInfos (`16330088732`).
   - Nothing changed → no command. `flows/sponsor.py` keeps its role.
4. INFO again for the response.

`status` changes answer 501, because there are no client statuses. Registry Lock changes go by e-mail
(`53000080009` on writes).

Several commands are not atomic. If the domain command succeeded and the AuthInfo command failed, the proxy
must not report a plain failure. See Q7.

**Delete (`domainNames_delete` → DELETE)**: direct. The domain enters `redemptionPeriod` (30 days). A domain with
a DISPUTE goes to the dispute holder at once (`13350000001`, info).

**Renew (`domainNameRenewProcesses_renewCreate`)**: no RRI command. Domains have no expiry, so this answers 501.
This is `UNIMPLEMENTED_COMMAND`, and the response says so.

**Restore (`domainNameRestoreProcesses_create`)**: RESTORE is one step, by the registrar that deleted the domain.
The RPP `restoreReport` has no counterpart. See Q6. The restore of a foreign domain from the redemption period
is CHPROV with AuthInfo2 (§4.3).

**Create processes and processes listing**: 501 today, and unchanged.

### 3.2 Contacts

RRI contact types: `PERSON` and `ORG` (holders), and `REQUEST` (a URI template for GeneralRequest/Abuse)
(ref §5.1).

| RPP Card (`contact.create`) | RRI contact | Gap |
|---|---|---|
| `id` | `Handle` | Must be `DENIC-<RegAcc number>-<suffix>`, 9–32 characters. The proxy can check the prefix up front. |
| `kind` `individual` / `org` | `Type` `PERSON` / `ORG` | |
| `name` | `Name` (1) | Required, and **immutable** after create (`63220080801` → 4xx). |
| `organizations` | `Organisation` (0–n) | Allowed only on `PERSON` (`63200080900`). For an `ORG` the organisation is the `Name`, which the mapper must swap. |
| `addresses` | `Address` 1–n, `PostalCode`, `City`, `CountryCode` | No region/state (`sp`) field. A Card `region` → 501. |
| `localizations` (EPP `postalInfo loc`) | — | One form only → 501. |
| `emails` | `Email` (1–n) | EPP allows one email, RRI several. |
| `phones` voice | `Phone` (exactly 1, **mandatory** since 2026-01-28) | A second voice number → 501. A Card without a phone → DENIC refuses it (`63200042402`). Q13: check that up front? |
| `phones` fax | — | No fax in RRI 5.0 → 501. |
| `status`, `authInfo`, `disclose` | — | 501. |
| — | verification blocks (0–5) | NIS2 pre-verification has no place in RPP, see §4.5. Omitting it in an UPDATE **deletes** it, so the adapter must carry it over from the INFO it read. |
| `REQUEST` contacts | `Type: REQUEST`, `URI-Template` | Possible RPP form: a Card with only `links[{uri}]`. But an RFC 6570 template is not a URI. See Q2. |

**Read (`contacts_read` → contact INFO)**: own contacts only. `provMetadata.spClientId` is required in RPP. RRI does
not return it, but it is the RegAccId encoded in the handle prefix. `upDate` ← `Changed`. There is no `crDate`.
`status` is required in RPP but RRI has no contact status, so the proxy would synthesise `ok`, see Q14.

**Update**: full replacement in RRI (§3.1 has the pattern). `contact_difference.py` makes an EPP delta and refuses
what EPP cannot clear. After the split ([refactoring.md §3.5](refactoring.md#35-full-and-partial-updates)),
a PUT reaches the RRI adapter as a `ContactReplacement`, which it sends whole with the verification blocks
carried over. A PATCH reaches it as a delta, which is applied to the contact it read. A contact UPDATE starts a new NIS2 risk assessment for every domain that uses the contact as holder
(ref §6.4). That is a significant side effect of a PATCH, and the response cannot express it.

**Delete (`contacts_delete`)**: no RRI command. DENIC deletes unused contacts itself (ref §5.1) → 501.

**Availability (`contacts_availability*` → contact CHECK)**: works only on your own handles. Another
registrar's handle reads as `free` or `invalid`. The handle namespace is per RegAcc anyway.

**Transfer (all 10 `contactTransferProcesses_*`)**: RRI has no contact transfer → 501.

### 3.3 Hosts

RRI has no host object. All `/hosts` operations (`hosts_create`, `_read`, `_update`, `_updatePartial`, `_delete`,
`_availability`, `_availabilityHead`) answer 501 on RRI, and discovery leaves `host` out of `objects`. Host transfer
is 501 already.

### 3.4 Messages

| RPP | RRI | Notes |
|---|---|---|
| `messages_query` | QUEUE-READ | One message, the oldest. `Msgcnt` → `RPP-Queue-Size`. The RPP `type` query parameter could become `msgType`, but the type names differ, so the proxy would need a type map, see Q15. |
| `messages_read(id)` | QUEUE-READ, then compare ids | As `flows/messages.py` does for EPP. Only the head can be read. |
| `messages_delete(id)` | QUEUE-DELETE `msgid` | Only the oldest (`63650063607` → 409?). |
| `messages_create` | — | 501, unchanged. |

Mapping of the 15 RRI message types (ref §9) to the RPP message data types:

| RRI `msgType` | RPP `data` | Notes |
|---|---|---|
| `chprovAuthInfo` | `transferOutcomeMessage` (`trStatus` `serverApproved`?, gaining client `new`, losing `old`) | No request or action dates beyond `msgtime`. |
| `expire`, `domainDelete` | `expirationDeletionMessage` (`deletionDate` ← `msgtime` or `expire`) | |
| `expireWarning`, `authInfoExpire`, `authInfo2Notify`, `authInfo2Delete`, `domainUpdate`, `domainTransit`, `lockCreate`, `lockDelete`, `domainStatusUpdate`, `contactUpdate`, `contactDelete`, `contactVerificationRequired` | `serviceNoticeMessage` (`objectType`, `objectId`, `message`) | `domainStatusUpdate` (the result of the risk assessment) is close to `reviewResponseMessage` (`approved` ← `connect`, not approved ← `serverHold`). The match is loose, see Q15. `contactDelete` names up to 100 handles, but RPP has one `objectId`. |

Today's rule carries over: anything the proxy cannot translate becomes a `serviceNoticeMessage`, so a client can
always read and acknowledge it. The `QueueMessage.event` union (`TransferEvent | PendingActionEvent`) is EPP-shaped
and gains RRI events, see [refactoring.md](refactoring.md#36-models).

### 3.5 Status mapping

| RRI | RPP `domainStatus` label | Note |
|---|---|---|
| `connect` | `ok` | |
| `failed` | `inactive`, with `due` ← `Expire` and a `reason` | The domain is not in the zone and is deleted at `Expire`. Q5. |
| `pendingCreate` | `pendingCreate` | Exclusive, per DENIC. |
| `serverHold` | `serverHold` | NIS2 quarantine. Exclusive. |
| `redemptionPeriod` | `rgpRedemptionPeriod` + `pendingDelete` (as EPP RGP does) | INFO does not list this status (ref §5.3); only CHECK shows it. Whether INFO works on a domain in RGP is unverified. |
| `RegistryLock: true` | `serverUpdateProhibited`, `serverDeleteProhibited`, `serverTransferProhibited` (reason "registry lock") | |
| `[Dispute]` | — | No label fits. Leave it out, or use `serverTransferProhibited`? (Q5) |
| `free`, `invalid` | CHECK only | → availability `reason`. |

## 4. Cross-cutting gaps

### 4.1 Update semantics (full replacement)

RRI has no add/remove/change. In K/V, any optional keyword that is omitted is deleted (ref §3.1). In XML, an
omitted optional element is deleted (ref §3.2). Consequences:

- Every update is read, then write. The read and the write are not atomic. DENIC refuses concurrent writes
  (`53000000012`) but has no version check, so a change made between the proxy's read and its write is lost.
- The adapter must send back data RPP cannot see: verification blocks on contacts, and the DNSSEC keys and
  `Nsentry` records that RPP does expose. If a newer RRI field ever appears in INFO and the proxy does not know
  it, an UPDATE deletes it silently. With XML and strict XSDs that cannot happen unnoticed, which is one reason
  for XML, see [refactoring.md](refactoring.md#33-rri-wire-format).

### 4.2 AuthInfo

| RPP | RRI |
|---|---|
| `authInfo.authdata` on a domain (sponsor sets it) | AuthInfo1. The proxy sends only the SHA-256 hex hash; DENIC never stores or returns the secret. 8–16 characters from a restricted charset. Lifetime ≤ 30 days, default 30. |
| `RPP-Authorization` on a read of a foreign domain | INFO `AuthInfo`. This shows holder data, but no handles. |
| `RPP-Authorization` on a transfer | CHPROV `AuthInfo` (AuthInfo1 or AuthInfo2). |
| — | AuthInfo2, which DENIC posts to the holders on request by any registrar. No RPP operation. |

The `method` of `authInfo.create` must be the plain-password method. Any other method → 501.

### 4.3 Transfer (CHPROV)

RPP `domainTransferProcess.create` carries `transferDir`, `gainingClientId` and `transferPeriod`, and the
authorisation travels in `RPP-Authorization`. CHPROV needs, in the same request (ref §6.18):

- 1–5 holder handles, and optionally GeneralRequest and Abuse handles. All must belong to the **gaining** RegAcc.
- the complete DNS data (`Nserver`/`Nsentry`/`Dnskey`).
- the AuthInfo.

Options (Q3):

- **A. The proxy builds the data.** It sends INFO with the AuthInfo and `recursive=true` to get the holder data
  (without handles) and the DNS data. It creates new contacts in the gainer's RegAcc, with generated handles, then
  sends CHPROV. This leaves contacts behind if CHPROV fails, and it re-registers personal data the gainer may not
  be permitted to process (NIS2 verification). Not recommended without the maintainer's agreement.
- **B. A request extension.** The client passes `registrant`, `contacts` and `dns`/`nameservers` with the transfer
  request. That is not in the RPP drafts, so it goes to [spec-issues.md](../../.spec/spec-issues.md) and into a
  profile of its own.
- **C. 501.** Transfer is not available over RPP on RRI.

Whichever option is chosen, the result is immediate. That matches the existing "completed at once" path of
`TransferHandlers.create` (200 with no `Location`). `transferRead`, `transferDelete`, `transferApprove` and
`transferReject` answer 501, because RRI has no query, cancel, approve or reject, and the losing registrar cannot
object. A push transfer (`transferDir: push`) → 501, unless TRANSIT is mapped to it (Q8).

### 4.4 Several holders

RRI allows 1–5 holders. RPP `domainName` has one `registrant`. Reading a domain with more than one holder
cannot be represented faithfully. Options (Q1):

- render the first as `registrant` and the others as `contacts` with the label `registrant`;
- refuse to render (500), which is bad for a read;
- a `holder` label for all of them.

Writing several holders needs the same decision.

### 4.5 NIS2 data

RRI 5.0 carries, with no RPP place for it:

- contact verification blocks (claims, result, reference, timestamp, evidence, method, trust framework);
- domain `VerificationDeadlineBeforeDedelegation` / `…BeforeDeletion`, and the deadline infos `16350000040`/`41`
  in write responses;
- the `domainStatusUpdate` and `contactVerificationRequired` messages, which become service notices (§3.4).

A registrar that uses RPP alone could not pre-verify holders, and a domain would then go to `serverHold` and be
deleted after 90 days. This is the largest functional gap. It needs an RPP extension or a DENIC profile (Q16).
Until then the adapter must at least keep the stored verification blocks across updates (§4.1).

### 4.6 Sponsor identity

`core/flows/sponsor.py` compares the sponsor of the object with `backend.sponsor_id`, and in EPP the login id is the
`clID`. In RRI the login (`DENIC-1000022-RRI`) is not the RegAccId (`DENIC-1000022`). The backend session must
expose a sponsor id of its own. It is derived from the login handle (`DENIC-<n>`), not set in configuration, because one
deployment can serve several RegAccs. The maintainer confirmed the derivation, see Q17.

### 4.7 Client transaction id

RRI CTIDs are 3–64 characters, unique per RegAcc for 24 months (`63000060504`), and meant for write requests.
Sending one on INFO may be refused (`63000000007`, unverified). The RRI adapter therefore:

- sends `RPP-Cltrid` as CTID on writes only, and refuses a value outside 3–64 characters with a 400 before
  sending;
- never sends it on the INFO read-backs (the EPP code already omits it there);
- when a request causes several commands (create plus AuthInfo, update plus AuthInfo), derives distinct CTIDs from
  the client's, for example `<cltrid>-1`. That changes the echo, so Q18 asks which value `RPP-Cltrid` echoes.

## 5. Result code mapping

RRI codes have 11 digits, `A B CCC DDDDDD`: class, interface, module and code (ref §4). The outcome is the
separate `Result` value. The proposal:

1. `Result: success` → `1000`. With status `pendingCreate`, `1001` (action pending)?, see the 202 question in §3.1.
2. `Result: failed` → map the **first `error`-level message code** through a table. If the code is not in the table,
   map the class digit:

| DENIC code(s) | Meaning | `ResultCode` | HTTP (core §18.1) |
|---|---|---|---|
| `83000000010` | login failed | `2200` / `2501` | 401 |
| `63100020005`, `73100000005` | login blocked / too many sessions | `2502` | 429 |
| `63300022003`, `63200020603` | object of another registrar | `2201` | 403 |
| `63300062009`, `63300062010` | domain / RegAcc does not exist | `2303` | 404 |
| `63310062004` | domain exists | `2302` | 409 |
| `56310082011` | domain in redemption period | `2304` | 409 |
| `53000080009`, `53000080011` | locked / dispute | `2304` | 409 |
| `63370088701`, `56000088709` | AuthInfo does not match / does not exist | `2202` | 401 |
| `63380063209` | CHPROV of own domain | `2002` | 409 |
| `63391068704`, `63393068704` | AuthInfo already exists | `2302` | 409 |
| `63392068709` | AuthInfo1 does not exist | `2303` | 404 |
| `63220080801`, `53000080002` | value immutable / cannot be deleted | `2306` | 422 |
| `63650063607`, `63650063609` | not the oldest / unknown message | `2303`? | 404 |
| `53300102902`, `53300102912`, `56300108812`, `63300102913` | DNS / predelegation | `2306` | 422 |
| `53000060009`, `63300080700` | contact missing / wrong type for role | `2305`? / `2306` | 409 / 422 |
| `53000000008`, `56000020021`, `55000000002` | quota / ACL exceeded | `2502` | 429 |
| `53000000012` | concurrent write | `2400` | 500 (or 409? Q19) |
| `63000060504` | CTID reused | `2306` | 422 (the EPP backend in the devcontainer answers `2400` for this) |
| `83000000004` | XML schema validation failed | `2400` | 500, because it is a proxy defect |
| class `6x…` (permanent error), otherwise | | `2306`/`2005` by module | 422 / 400 |
| class `5x…` (temporary error), otherwise | | `2400` | 500 |
| class `7x…`/`8x…` (technical) | | `2400` / `2500` | 500 |

The RPP error `detail` should carry the DENIC code and text (`DENIC 63300022003: This domain is administered by
another provider`). DENIC tells clients to parse the code, not the text. `success` with `warning`/`error`
messages (for example the predelegation warnings) has no RPP place except the response body. The proxy logs it.

## 6. Operational constraints the proxy must respect

| Constraint (ref §2) | Effect on the proxy |
|---|---|
| TLS on `rri.denic.de:51131`, test `rri.test.denic.de:51131`. IPv4 allowlist (mandatory). | The proxy host must be allowlisted. The MTEST integration run needs an allowlisted machine, see [refactoring.md §5.4](refactoring.md#54-rri-integration-tests-on-mtest). |
| Framing: 4-byte length counts the **payload only**. | EPP (RFC 5734) counts the header too. `TCPClient` adds 4 today, so the framing must become a parameter. |
| No greeting. | `EPPClient.connect` reads a greeting first. An RRI client must not. |
| 64 KB maximum request. | Fine for single objects. |
| 7 parallel sessions per RegAcc (4 in test). | One cached session per user is fine. Per-request sessions under load could exceed this (`73100000005`). |
| Idle timeout 5 min, pre-login timeout 15 s. | A cached session dies when idle. The client must reconnect and retry once on a dead socket before the first byte of a command is sent. A write that may have reached DENIC must not be retried, because RRI is not idempotent. |
| 10 failed logins → user blocked 1 h. | Every HTTP Basic attempt with an unknown password for a username without a session costs a LOGIN. Anyone can lock the registrar out of RRI this way. Not addressed for now, listed as a risk in [refactoring.md §7](refactoring.md#7-risks). |
| ACL 2000 requests/min (200/min 02:00–04:00); quota 50,000/day. | Each read-back and each read-before-write costs a request. A PATCH on RRI is 3–4 requests. |
| The test environment always answers info `13000000011`. | Ignore it. |

## 7. Open questions

Each needs the maintainer's decision before implementation.

| # | Question | Proposal |
|---|---|---|
| Q1 | How to read and write domains with 2–5 holders, given one RPP `registrant`. | First holder as `registrant`, the others as `contacts` labelled `registrant`. Spec issue. |
| Q2 | Contact labels for GeneralRequest and Abuse, and how a `REQUEST` contact (URI template) appears in RPP. | Labels `generalRequest` and `abuse`. A REQUEST contact is a Card with only one `links` entry. Spec issue. |
| Q3 | Transfer (CHPROV): proxy-built data (A), a request extension (B), or 501 (C). | C first, then B through the spec. |
| Q4 | AuthInfo1: lifetime (always 30 days, or from a client value), and whether the proxy checks the 8–16 character charset itself. | Default 30 days. Check up front → 422 `2306`. |
| Q5 | RPP status for `failed` and for DISPUTE. | `failed` → `inactive` with `due`. DISPUTE left out. |
| Q6 | Restore: one-step RESTORE on `restoreProcesses_create`, and what to do with a `restoreReport`. | RESTORE when no report is given. With a report → 501. |
| Q7 | Answer when the second command of a request fails (e.g. CREATE succeeded, CREATE-AUTHINFO1 failed). | 202 with the first command's headers and a logged warning, like the failed read-back today. Or a Problem with the second error and a detail that the domain was created. |
| Q8 | TRANSIT: expose it (push transfer to `DENIC`?) or not. | Not exposed. |
| Q9 | CREATE-AUTHINFO2: expose it, and where. | Not exposed in the first version. |
| Q10 | regacc INFO as `organisations_read`. | Later. Read-only. |
| Q11 | `lgr` on RRI. | Refuse any `lgr`, unless one configured name for the DENIC repertoire is given. |
| Q12 | Reads always render name servers as `dns` records (RRI has no host objects). Is that acceptable for clients that wrote `nameservers`? | Yes. Document it in a spec issue. |
| Q13 | Check the mandatory phone in the proxy (400/422) or let DENIC refuse it. | Let DENIC refuse it. One rule source. |
| Q14 | Contact `status` (required in RPP, absent in RRI). | Synthesise `ok`. |
| Q15 | Message type names for the RPP `type` filter, and `domainStatusUpdate` → `reviewResponseMessage` or `serviceNoticeMessage`. | `serviceNoticeMessage` for everything except `chprovAuthInfo` and `expire`/`domainDelete`. Ignore `type`, as the EPP profile does. |
| Q16 | NIS2 verification and deadlines in RPP. | An RPP extension or DENIC profile. Out of scope for the first version. Spec issue. |
| Q17 | The sponsor id of an RRI session. | Per session, derived from the login handle (`DENIC-<n>`), because one deployment serves several RegAccs (the MTEST run uses two). Confirmed by the maintainer, see [refactoring.md §3.2](refactoring.md#32-session-and-authentication) (P1). |
| Q18 | The CTID echo when a request causes several commands. | Echo the client's `RPP-Cltrid` unchanged and send `<cltrid>-n` on the extra commands. |
| Q19 | Concurrent write `53000000012`: 409 or 500. | 409 (`2304`?), because the client may retry. |
| Q20 | K/V or XML on the wire. | XML, see [refactoring.md](refactoring.md#33-rri-wire-format). |
