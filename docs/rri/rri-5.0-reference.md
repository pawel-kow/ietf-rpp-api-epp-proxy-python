# DENIC RRI (Realtime Registry Interface) – Technical Reference (RRI protocol 5.0)

Compiled 2026-11-10 from DENIC's public documentation ("dedocs", English edition), plus the
`DENICeG/pyrri` client. It is the source of the RRI facts in [gap-analysis.md](gap-analysis.md) and
[refactoring.md](refactoring.md). DENIC's pages are authoritative; check them before relying on a detail here. The current protocol version is **5.0** for both K/V and XML
(no "5.x" minor versions are documented).

---

## 0. Sources, method, coverage, caveats

### 0.1 Coverage
- Every page under `https://docs.denic.de/en/Content/DENIC-29/` reachable from the start
  page (123 pages, English edition). Also covered:
  - the **Examples** section `https://docs.denic.de/en/Content/Beispiele/50/...` (58 pages,
    including the **complete 5.0 XSDs** under `Beispiele/50/XMLSchema/`, plus example
    requests and messages for every message type). The Examples section lists 5 message types
    that the DENIC-29 queue chapter does not document (`contactUpdate`, `domainTransit`,
    `domainUpdate`, `lockCreate`, `lockDelete`).
  - the Changelog pages 001–023 (2024-07 … 2026-08), "How to – Experts", "How to – International
    Members", "How to – Domaininvestors", "Generating Hash Values", "Test Environment Mock-Up Tests".
  - `https://raw.githubusercontent.com/DENICeG/pyrri/master/rri.py` (RRI 4.0-era Python client).
- Process diagrams and timeline diagrams are images only, so their contents are not captured.

### 0.2 Citation shorthand
`D29:<Page>` = `https://docs.denic.de/en/Content/DENIC-29/<Page>.htm` (URL-encode spaces as `%20`,
umlauts as UTF-8, e.g. `Auftr%C3%A4ge`).
`EX:<path>` = `https://docs.denic.de/en/Content/Beispiele/50/<path>.htm`.
Start page: `D29:Aufträge an das .de-Registrierungssystem`.

### 0.3 Reliability notes
The DENIC pages contain many copy-paste errors in their examples (wrong action names, duplicated
elements, mismatched codes). Each one noticed is flagged **[DOC-INCONSISTENCY]**. Anything
inferred rather than read is flagged **[UNVERIFIED]** or **[INTERPRETATION]**. Where they disagree,
the XSDs (`EX:XMLSchema/*`) are the most authoritative source for XML structure.

---

## 1. System overview and concepts

Sources: `D29:Registrierungssystem für .de im Überblick`, `D29:Kurzbeschreibung der Frontends`,
`D29:RRI -  Einführung und Zugangsvoraussetzungen`, `Howtos/Internationale_Mitglieder.htm`.

- **RRI** is DENIC's own protocol, developed in 2004, used instead of EPP. It "includes many
  elements of the IETF standard" but is **not EPP**. It has two request formats, **key/value
  (K/V)** and **XML**. The server always answers in the format the request used.
- **Member** = registrar (a cooperative member). A **RegAcc** (registration account) corresponds to
  EPP's sponsoring client. Each RegAcc is identified by a **RegAccId** of the form `DENIC-<digits>`.
  A member has one basic RegAcc and may book more (9 more on Live, unlimited on Rush). A member
  account (MemberAccId, same `DENIC-<n>` syntax) groups the RegAccs.
- **Environments:** RRI Live, RRI Rush (for drop-catching, more throughput during the purge
  window), and a Test environment (two separate member test environments).
- **Transaction model:** one request leads to one response. Concurrent operations on the same object
  are rejected (`53000000012 Concurrent write access to the same business object is prohibited`).
- **Differences from EPP** listed by DENIC (`Howtos/Internationale_Mitglieder.htm`):
  - No RENEW. Billing is monthly and domains run until deleted.
  - RRI is **not idempotent**: repeating a command with the same parameters is rejected with an error.
  - Transfer (CHPROV) cannot be rejected or cancelled by the losing registrar, and there is no
    transfer query. The holder authorises a transfer by handing over an AuthInfo.
  - Registrar, contact and name-server data are **mandatory** in CHPROV.
  - Responses do not echo request data. They carry only short success/error messages.
  - Only one object per request (no multi-domain check).
  - The message queue is a mandatory part of the provisioning model.
  - Name servers that are still connected do not block a DELETE.
  - Status values are set only by the server.
  - Three contact roles per domain: holder (PERSON/ORG), General Request, Abuse Contact
    (both REQUEST type). There are no admin/tech/billing contacts.
- **Front ends:** your own RRI client, or the RRI Web Client at
  `https://member.secure.denic.de/en/service/tools/rri-web-client/` (it has a "Raw" tab for sending
  raw K/V or XML). DENIC also publishes a CLI "DENIC RRI client" on GitHub (`Howtos/Experten.htm`).
- **Locations:** two active-active entry points (Frankfurt, Amsterdam). Clients are routed to the
  nearer one. Continuous delivery can cause brief interruptions. The regular maintenance window is
  Tuesday 16:00–20:00 (`D29:Rahmenbedingungen zur Registrierung`).

---

## 2. Transport

### 2.1 Connection
Sources: `D29:Transportformate`, `D29:Zugang zum RRI`, `D29:Sicherheit im RRI`, `D29:IP Allowlisting`.

| Item | Value |
|---|---|
| Transport | TCP ("RRI supports the transport protocol TCP"), always inside **TLS** |
| Live and Rush host | `rri.denic.de`, TCP port **51131** |
| Test host | `rri.test.denic.de`, TCP port **51131** |
| TLS | TLS 1.3 (`TLS_AES_128_GCM_SHA256`, X25519, preferred) and TLS 1.2 (`ECDHE-RSA-AES256-GCM-SHA384` preferred, `DHE-RSA-AES256-GCM-SHA384`, `ECDHE-RSA-AES256-SHA384`, `DHE-RSA-AES256-SHA256`, `AES128-SHA`) |
| Server auth | X.509v3 server certificate. DENIC recommends validating it via the root CA and checking the name per RFC 6125. No client certificate is used. |
| Client auth | User + password inside the LOGIN request |
| IP allowlisting | **Mandatory since 2026-02-03.** Configured per RegAcc in the RAI: at most 20 entries, IPv4 masks /32–/24, **IPv6 not supported**. It takes effect as soon as the first address is saved. Web-client-only members are exempt. |

The recommended sequence from `D29:Sicherheit im RRI` is: initialise TLS → TCP connect → start TLS →
check the certificate → send request → read response → close.

### 2.2 Message framing
Sources: `D29:Lesen-und-Senden-von-Daten`, `D29:Network-Byte-Order`, `D29:Sessionmanagement`.

- Each request and each response is one frame: a **4-byte unsigned length prefix in network byte
  order (big-endian)** (`htonl`, Perl/PHP `pack "N"`), followed by **exactly that many bytes of
  payload**. The length counts **bytes**, not characters.
- **Payload encoding: UTF-8.** The C example says "C-String, which contains the UTF-8 encoded order".
  The Java example decodes with the protocol charset. For XML, UTF-8 is the default and is
  recommended. UTF-16 or another declared `encoding` is possible in principle, and unsupported
  encodings give `83000000002`.
- **Maximum PDU size: 64 KB.** Larger requests get `83000000000 Request message too long`. The Perl
  example treats a length above 65535 as an error.
- The Java example treats a frame of length 0 as an empty message.
- There is no terminator or delimiter inside the frame. Read the 4 bytes, then loop until the
  full payload has arrived. All the examples loop on partial reads and writes.

Minimal Python, per the docs:
```python
def send(sock, text):            # sock = TLS socket
    data = text.encode("utf-8")
    sock.sendall(struct.pack("!I", len(data)) + data)
def recv(sock):
    n = struct.unpack("!I", _read_exact(sock, 4))[0]
    return _read_exact(sock, n).decode("utf-8")
```

### 2.3 Sessions
Sources: `D29:Sessionmanagement`, `D29:Auftrag Login`, `D29:Auftrag Logout`, `D29:Rahmenbedingungen zur Registrierung`.

- LOGIN must be the first request. Its identity and authorisation apply for the rest of the session.
- Parallel sessions per RegAcc: **Live 7, Test 4.** `D29:RRI Live und RRI Rush - Tabellenübersicht`
  also says "7 per RegAcc" for Rush. Exceeding the limit gives `73100000005 The maximum number of
  permitted login is reached`.
- A connection with no LOGIN is closed after **15 s**. After LOGIN, at least one request every
  **5 min** is needed, or the session is closed.
- After LOGOUT the server ends the session and no further commands are possible on it.
- If you drop the connection without LOGOUT, the session stays active "for a certain period" and
  can keep using one of the 7 slots.
- After **10 consecutive failed logins** the user is blocked for **1 hour** (`63100020005`).
- LOGIN, LOGOUT, QUEUE-READ and QUEUE-DELETE do not use quota points
  (`D29:Kontingentierung und Registrierungsaccount`; queue requests were exempted 2025-05-15).

### 2.4 Throughput, quotas and the ACL
Sources: `D29:Access-Control-Limit (ACL)`, `D29:Kontingentierung und Registrierungsaccount`, `D29:RRI Live und RRI Rush - Tabellenübersicht`.

- **ACL (per RegAcc):**
  - Live: 2000 requests / 60 s from 04:00 to 02:00 CET, and 200 / 60 s during the purge phase
    (02:00–04:00).
  - Rush: 2000 / 60 s all day.
  - Test: 100 / min.
  - Every request counts, valid or not.
  - Exceeding the limit blocks the RegAcc for 120 s. The block lifts once the last 120 s were under
    the limit. The error code is `55000000002` on the ACL page, but `56000020021 Access control
    limit exceeded` in the message-code list **[DOC-INCONSISTENCY]**.
- **Quota:** each request costs 1 point, except the four exempt ones above.
  - Basic RegAcc: 50,000/day, or 2 × domain inventory once the inventory exceeds 50,000.
  - Additional RegAccs: 2 × inventory.
  - Extra quota blocks of 50,000/day can be bought.
  - Warnings are sent at 60/90/100 %: `13000000022` / `33000000022 Used quota`. Exhaustion gives
    `53000000008 Daily quota exceeded`.

### 2.5 Test environment particularities (`D29:Zugang zum RRI`)
- The RGP lasts 1 day and ends between 10:00 and 12:00.
- The AuthInfo2 password is always **`secret`**.
- A domain in status `failed` is deleted after 1 day.
- ACL is 100 requests/min.
- Every response carries info message `13000000011 Request was processed in test environment - not
  valid in real world` with the argument `testing platform`.
- Mock-up test scenarios exist (special domain names or contact addresses such as `NISpendingCreate`
  that force a given status or message) (`Testumgebung Mock Up-Tests.htm`).

---

## 3. Request and response formats

Sources: `D29:Beschreibung der Datenformate Key Value und XML`, `D29:Transaktions-IDs`,
`D29:Datentypen und Wertebereiche für Datenfelder`, `D29:Schreibweisen für Daten in Aufträgen`, `D29:Zeitangaben`, XSDs.

### 3.1 Key/Value (K/V) format
- The current K/V version is **5.0** and is sent as `Version: 5.0`. Every request needs both
  `Version:` and `Action:`.
  - `63000040410` means Version is missing. `63000060402` means its value is not allowed.
  - `63000040110` means Action is missing. `63000060102` means its value is not allowed.
  - The `version-erule` in the ABNF table still says `"3.0"`, which is outdated
    **[DOC-INCONSISTENCY]**. Old examples on the DNSSEC and Registry-Lock pages also use `Version: 3.0`.
- Syntax is one line per field: `Keyword: value`.
  - Keywords are **case-insensitive** and must start at the beginning of the line.
  - The colon must directly follow the keyword (`Action : x` is an error).
  - There must be at least one space or tab after the colon.
  - **Keyword order is free.**
  - Repeating a keyword gives multiple values (Address, Email, Holder, Nserver …).
  - **Unknown keywords are ignored silently.** A typo therefore means the field is simply missing.
- Grouped sub-records use **section header lines** in square brackets: `[VerificationInformation]`
  in requests, and `[Holder]`, `[General Request]`, `[Abuse Contact]`, `[RegAcc]`, `[Dispute]`,
  `[earliest domain for dedelegation]` … in responses.
- **Update semantics:** omitting an optional keyword in an UPDATE **deletes** its stored value, or
  resets it to the default.
- The action selects the operation. The object is chosen by the presence of `Domain:` (domain),
  `Handle:` (contact) or `RegAcc:` (regacc). Error `63000080009` reads "Request type is missing,
  either keyword “Domain” or “Handle”". **[INTERPRETATION]** from that error text and the examples.
- K/V `Action` values seen in the examples: `login`, `logout`, `create`, `update`, `check`, `info`,
  `chholder`, `delete`, `restore`, `transit`, `chprov`, `create-authinfo1`, `delete-authinfo1`,
  `create-authinfo2`, `queue-read`, `queue-delete`. Values are case-insensitive: `CREATE`,
  `QUEUE-READ` and `INFO` also appear.
- **K/V response:** one field per line.
  - The first line is `Result: success|failed|exception`. Examples print both `RESULT:` and
    `Result:`, so **compare case-insensitively**.
  - `STID: <uuid>` and, when the client sent one, `CTID: <ctid>`.
  - Messages appear as `INFO: <code> <text>`, `WARNING: <code> <text>` and `ERROR: <code> <text>`.
    Arguments are appended in square brackets, comma-separated when there are several, e.g.
    `[Date: 2024-06-06T15:51:08+02:00, VerificationClaims: address;name]`.
  - Then the data fields follow.

### 3.2 XML format
- **Strict schema validation** against the 5.0 XSDs. Element order is significant and elements
  are case-sensitive. Unknown elements are an error (`83000000004 Validation of XML request against
  Schema failed`). On that error, the parser's own diagnostics come back as extra `<tr:argument>`
  lines.
- To delete an optional element, omit it. Empty values are not allowed.
- XSD files are `contact-5.0.xsd`, `dnsentry-5.0.xsd`, `domain-5.0.xsd`, `global-5.0.xsd`,
  `message-5.0.xsd`, `monitoring-5.0.xsd`, `regacc-5.0.xsd`, `transaction-5.0.xsd` and
  `verification-5.0.xsd`. The docs list the first eight; `verification-5.0.xsd` is imported by the
  others.
  - Official download is on the member website ("Schemata and BNFs").
  - The full text of all except `monitoring` is published at `EX:XMLSchema/*` and summarised in §13.
- **Namespaces (5.0):**

| Prefix (customary) | URI |
|---|---|
| (default) global | `http://registry.denic.de/global/5.0` |
| `tr` transaction | `http://registry.denic.de/transaction/5.0` |
| `contact` | `http://registry.denic.de/contact/5.0` |
| `domain` | `http://registry.denic.de/domain/5.0` |
| `dnsentry` | `http://registry.denic.de/dnsentry/5.0` |
| `msg` message queue | `http://registry.denic.de/msg/5.0` |
| `regacc` | `http://registry.denic.de/regacc/5.0` |
| `verification` | `http://registry.denic.de/verification/5.0` |
| `xsi` | `http://www.w3.org/2001/XMLSchema-instance` (needed for `xsi:type` on `dnsentry:dnsentry` and `verification:verificationInformation`) |

  Some REQUEST-contact examples use `https://registry.denic.de/...`. That is almost certainly wrong;
  the XSD target namespaces are `http://` **[DOC-INCONSISTENCY]**. The older 3.0 namespaces
  (`.../global/3.0` etc.) still appear in some legacy examples.

- **Request envelope** (global-5.0.xsd):
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<registry-request xmlns="http://registry.denic.de/global/5.0" xmlns:domain="http://registry.denic.de/domain/5.0">
  <domain:info recursive="false"><domain:handle>de-example.de</domain:handle></domain:info>
  <ctid>abc-123</ctid>          <!-- optional, global ns, AFTER the command -->
</registry-request>
```
  The command is exactly one of: `login`, `logout`, `contact:create|update|check|info`,
  `domain:create|update|chholder|delete|restore|check|info|chprov|transit|createAuthInfo1|deleteAuthInfo1|createAuthInfo2`,
  `msg:queue-read`, `msg:delete`, `regacc:info`. It may be followed by `<ctid>`, which has type
  `tr:idType`: a token of 3–64 characters.

- **Response envelope** (transaction-5.0.xsd). The child order is fixed: `stid?`, `ctid?`,
  `result`, `message*`, `data?`.
```xml
<registry-response xmlns="http://registry.denic.de/global/5.0" xmlns:tr="http://registry.denic.de/transaction/5.0">
  <tr:transaction>
    <tr:stid>…</tr:stid>
    <tr:ctid>…</tr:ctid>
    <tr:result>success|failed|exception</tr:result>
    <tr:message level="info|warning|error" code="53000080014">
      <tr:text>Domain "Status" is "pendingCreate"</tr:text>
      <tr:argument>…</tr:argument>      <!-- 0..n -->
    </tr:message>
    <tr:data> … any ##other namespace (domain:infoData, contact:checkData, msg:message, …) … </tr:data>
  </tr:transaction>
</registry-response>
```
  `code` is an `xs:unsignedLong`, which is the 11-digit message code (§4).

### 3.3 Transaction IDs (`D29:Transaktions-IDs`)
- **STID** is assigned by the server. It is globally unique (a UUID in practice) and present for
  write requests and LOGIN. Its rule is `stid-rule` (30–255 characters), while the XSD
  `idType` allows 3–64. For LOGOUT, the STID is only sent when the logout succeeds.
- **CTID** is optional and assigned by the client, for **write requests**.
  - Length 3–64 characters.
  - It must be **unique per RegAcc for 24 months**. Reuse gives `63000060504 “CTID” has been used
    before`.
  - It is echoed only if the request could be parsed.
  - Sending a CTID on a non-writing request such as domain INFO can give `63000000007 Request shows
    semantics error` **[INTERPRETATION of that error's description]**.

### 3.4 Result values
`result-erule` / `tr:resultType`:
- `success`: the request was executed. It **may still carry warnings or errors**, e.g. a domain
  CREATE that ends with status `failed` returns `success` plus a warning.
- `failed`: the request was not executed.
- `exception`: system failure; the request was not executed.

### 3.5 Data conventions
- Dates and times are ISO 8601 with a UTC offset, e.g. `2021-04-07T13:16:00+01:00` (`date-rule`,
  25 characters). The one exception is `AuthInfoExpire` in CREATE-AUTHINFO1 **requests**, which is
  `YYYYMMDD` (8 digits).
- Input is case-insensitive. The server stores and returns DENIC handles in uppercase
  (`DENIC-1000002-DENIC`), domains and name servers in lowercase, and NS-entries with the host in
  lowercase and the type in uppercase (`D29:Schreibweisen für Daten in Aufträgen`).
- Unicode is allowed (IDN domains are given in U-label form in `Domain` / `domain:handle`, with an
  optional ACE form in `Domain-Ace` / `domain:ace`).

### 3.6 Value-range rules (ABNF summary from `D29:Datentypen und Wertebereiche für Datenfelder`)

| Rule | Definition (as documented) |
|---|---|
| contact-rule | 9–32 characters, `"DENIC-"` + digits/letters/hyphen/dot. XSD: `[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+`, maxLength 32 |
| regaccid-rule | `"DENIC-"` + 7–13 digits (the XSD pattern is `DENIC\-[1-9][0-9]*`) |
| domain-rule | 4–66 characters of (idn-val / ace-val) + `.de` |
| domainace-rule | `xn--…` + `.de`. XSD aceType: `[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]` |
| nserver-rule | 1–254 characters of letters, digits, `-`, `.`, `:` and space (a space separates host and IPs in K/V) |
| nsentry-rule / mx-rule | 4–252 characters |
| mxpref-rule | 1–3 digits (0–999) |
| ip-rule | 7–39 characters of digits, `.` and `:` |
| dnskey-rule | 30–999 characters of `A-Za-z0-9-./+` |
| authinfo-val | `A-H J-N P-Z a-k m-n p-z 2-9 + - / *` (no I, O, l, o, 0, 1). authinfo-rule is 1–255 characters in the Chprov object; AuthInfo1 itself must be 8–16 characters |
| authinfohash-rule | exactly 64 hex characters (SHA-256) |
| digit-rule | 8–9 digits (used for AuthInfoExpire `YYYYMMDD`) |
| email-rule | 3–255 characters (RFC 5322). XSD pattern `\S+@\S+` |
| phone-rule (contact) | `^\+[0-9]{1,3}\.[0-9]{4,14}(?:x.+)?` (EPP style, RFC 5733 §2.5), e.g. `+49.69272350`, `+49.69123456x156` |
| phone-rule (regacc) | E.123, XSD `\+[/\-\.\s0-9x]{1,254}` |
| postalcode-rule | 1–20 characters of letters, digits, `-` and space |
| city-rule | 1–80 characters. name-rule / address-rule: 1–255 characters |
| country-erule | ISO 3166-1 alpha-2 |
| msgid-rule | 30–255 characters of letters, digits and `-` (a UUID in practice) |
| message-rule | 1–255 characters |
| status-erule | `connect, failed, invalid, free, pendingCreate, serverHold` (omits `redemptionPeriod`, which the XSD includes) |
| role-erule | `PERSON / ORG / REQUEST` |
| contactstatus-erule | `free / exists / invalid`. The XSD and examples use **`exist`** **[DOC-INCONSISTENCY]** |

---

## 4. Message codes (result codes)

Sources: `D29:Meldungskodierung`, `D29:Aufbau und Bestandteile einer Meldungskodierung`,
`D29:Parsen des Errorcodes in Meldungskodierugs-Antworten`, `D29:Liste-mit-Meldungscodes`,
`D29:Liste-mit-Meldungscodes-zur-Verifikation`.

**Structure.** Every message code has 11 digits, laid out as `A B CCC DDDDDD`:
- **A** (position 1) is the classification:

| A | Meaning |
|---|---|
| 1 | INFO, success |
| 2 | INFO, failed |
| 3 | WARNING, temporary |
| 4 | WARNING, permanent |
| 5 | ERROR, temporary |
| 6 | ERROR, permanent |
| 7 | TECHNICALERROR, temporary |
| 8 | TECHNICALERROR, permanent |

  A WARNING means the request was executed but at least one detail was changed.
- **B** (position 2) is the interface: `3` = RRI (.de), `4` = RRI ENUM, `5` = whois,
  `6` = interface-independent, `9` = web application.
- **CCC** (positions 3–5) is the module:

| CCC | Module | CCC | Module |
|---|---|---|---|
| 000 | none | 345 | Expire (ENUM) |
| 100 | LOGIN/LOGOUT | 348 | Expire (DE) |
| 200 | contact (generic) | 350 | DELETE |
| 210 | contact CREATE | 360 | TRANSIT |
| 220 | contact UPDATE | 370 | CHPROV |
| 300 | domain (generic) | 391 | CREATE-AUTHINFO1 |
| 310 | domain CREATE | 392 | DELETE-AUTHINFO1 |
| 320 | domain UPDATE | 393 | CREATE-AUTHINFO2 |
| 330 | CHHOLDER | 394 | AuthInfo expire |
| 340 | RENEW (ENUM) | 400 | CHECK |
| 450 | INFO | 500 | RAI |
| 600 | QUEUE | 610 | QUEUE-READ |
| 650 | QUEUE-DELETE | | |

- **D** (positions 6–11) is the specific code.

DENIC says to **parse only the code and never the text**, because texts change. The XML gives the
code in `@code` and the level in `@level`. K/V gives `ERROR: <code> <text> [<dynamic>]`. In
practice the classification digit does not always match `level`: for example `53000080014`
pendingCreate is returned as `level="info"`. A client should therefore treat `level` / the K/V
prefix as the message severity and `Result` as the outcome.

Example from `D29:Parsen…`: a CREATE that returns `success` with an error and a warning (the domain
ends up `failed`):
```
RESULT: success
ERROR: 53300102912 Nameserver error [ERROR: 901 Unexpected RCODE (1)]
WARNING: 33300102900 The provided DNS data are not acceptable. Domain "Status" is "failed". [2021-08-20T13:06:05+02:00]
STID: 7767b575-eace-11eb-9ccc-0141a1811e3e
CTID: Test#1626945804-27198095-0
```

The full code list is in §12.

---

## 5. Data objects

### 5.1 Contact (handle) object
Sources: `D29:Datenobjekt Contact`, `D29:Aufträge zu Contacts`, `D29:Auftrag contactCREATE`,
`D29:Auftrag contactUPDATE`, `D29:Informationen-zur-Telefonnummer`, `D29:Erläuterung zum URI-Template`,
`EX:XMLSchema/Contact`.

**Contact types** (`contact:type`):
- `PERSON`: a natural person.
- `ORG`: a legal person.
- `REQUEST`: a URI template (http/https/mailto) used for the **General Request** and
  **Abuse Contact** roles.
- The XSD enumeration also contains **`ROLE`**, a legacy RRI 3/4 type. The 5.0 docs do not list it
  and say a holder must be PERSON/ORG and GR/Abuse must be REQUEST. **[UNVERIFIED whether ROLE is
  still accepted]**.

**Handle:** `DENIC-<RegAcc number>-<free suffix>`, 9–32 characters. It **must start with the
RegAccId of the administering RegAcc**, e.g. `DENIC-1000022-EXAMPLE-PERSON`. A contact is usable
only by its own RegAcc: using another RegAcc's handle gives `63200020603 This Contact is
administered by another provider`.

**Fields for PERSON / ORG.** K/V keywords and their XML elements; the XML order is fixed.

| K/V keyword | XML (contact ns) | Occ. | Type/len | Notes |
|---|---|---|---|---|
| Handle | `handle` | 1 | token 9–32 | |
| Type | `type` | 1 | PERSON/ORG | PERSON↔ORG can be changed by UPDATE (since 2024-11), except when a DISPUTE is on a domain the contact holds |
| Name | `name` | 1 | 1–255 | **Immutable once set** (`63220080801`). The holder must be named here, not in Organisation |
| Organisation | `organisation` | 0–n | 1–255 | **PERSON only** (`63200080900` if used with ORG). Gives no rights to the domain |
| Address | `postal/address` | 1–n | 1–255 | Street lines |
| PostalCode | `postal/postalCode` | 1 | 1–20 | Completeness check for DE (5 digits), AT and CH (4 digits) |
| City | `postal/city` | 1 | 1–80 | |
| CountryCode | `postal/countryCode` | 1 | ISO alpha-2 | |
| Email (examples write `eMail:`) | `email` | 1–n | 3–255 | Mandatory for PERSON/ORG |
| Phone | `phone` | **1** | EPP format | **Mandatory since 2026-01-28** for CREATE/UPDATE. Dummy numbers like `+49.000000` are no longer allowed. Missing or repeated gives `63200042402`; bad format gives `63200062603` |
| [VerificationInformation] block | `verification:verificationInformation xsi:type="verification:verificationInformationType"` | 0–5 | | See §5.5 |
| (response only) Changed | `changed` | 1 | dateTime | |
| (response only) DisputeReference | `disputeReference` | 0–1 | boolean | `true` if the contact is the holder of a domain with a DISPUTE |

Dispute protection: if the contact is the holder of a domain with a DISPUTE entry, Name,
Organisation, Address, PostalCode, City, CountryCode and Type cannot be changed. Verification info
can still be changed.

**Fields for REQUEST:**

| K/V keyword | XML | Occ. | Notes |
|---|---|---|---|
| Handle | `handle` | 1 | |
| Type | `type` | 1 | `REQUEST` |
| URI-Template (K/V example writes `Uri-template:`) | `uri-template` | 1 | 8–1024 characters. RFC 6570 **level 1 only**. Schemes http, https, mailto. Only the case-sensitive variables `{Alabel}` and `{Ulabel}`, each usable any number of times. Variables are expanded **only** in web-whois; INFO returns the raw template. CREATE test-expands the template with a sample domain. Errors are `83000000005 Validation of URI-Template failed [...]`. Verification blocks are not allowed (`63450064002`) |

**XSD element order** for create and update: `handle, type, name?, organisation*,
postal?(address+, postalCode, city, countryCode), email*, phone?, uri-template?,
verificationInformation{0,5}`. The infoData order is `handle, type, name?, organisation*, postal?,
email*, phone?, disputeReference?, uri-template?, changed?, verificationInformation{0,5}`.

**Lifecycle:**
- A registrar cannot delete or deactivate a contact.
- DENIC deletes contacts automatically after retention periods: **6 months** if a contact was never
  used on a domain, **6 full calendar years** after the last domain reference ended. Deletions are
  reported in `contactDelete` messages (§9).
- Contacts used on a Registry-Locked domain are protected against RRI changes.

**Contact status** (`contact:status`, `D29:Contact-Status`): `free` (does not exist), `exist`,
`invalid`.

### 5.2 Domain object
Sources: `D29:Datenobjekt Domain`, `D29:DNSSEC`, `D29:Domain-Status`, `D29:Domainstatus pendingCreate und serverHold`,
`D29:Antworten domainCHECK und domainINFO`, `D29:Auftrag domainINFO`, `EX:XMLSchema/Domain`, `EX:XMLSchema/Dnsentry`.

| K/V keyword | XML | Occ. | Notes |
|---|---|---|---|
| Domain | `domain:handle` | 1 | 4–66 characters, U-label allowed. The XSD `latinToken` allows only Basic Latin, Latin-1 Supplement and Latin Extended-A |
| Domain-Ace | `domain:ace` | 0–1 | A-label. Must match Domain (`53380062206`) |
| Holder | `domain:contact role="holder"` | **1–5** | PERSON/ORG handles, all different. All must have a phone number when the holder changes |
| GeneralRequest | `domain:contact role="generalrequest"` | 0–1 | REQUEST handle |
| AbuseContact | `domain:contact role="abusecontact"` | 0–1 | REQUEST handle |
| Nserver | `dnsentry:dnsentry xsi:type="dnsentry:NS"` | **2–13** (alternatively use Nsentry) | K/V form is `Nserver: <host> [<ip>]`. Glue (IPv4, optional IPv6) is required when the host is in-bailiwick |
| Nsentry | `dnsentry:dnsentry xsi:type="dnsentry:A" / "AAAA" / "MX"` | 1–5 | Used instead of NS delegation. DENIC serves A/AAAA/MX records for the domain or its subdomains directly. Owner in ACE. MX preference 0–999. `*.domain.de` wildcard is allowed for MX. Null MX `.` is supported (RFC 7505). An AAAA entry requires a matching A entry (`66300063023`) |
| Dnskey | `dnsentry:dnsentry xsi:type="dnsentry:DNSKEY"` | 0–20 | K/V form is `Dnskey: <flags> <protocol> <alg> <base64key>` on **one line**. Flags 256 or 257, protocol 3, algorithms 3, 5, 6, 7, 8, 10, 12, 13, 14. DENIC computes the DS. There is no DS input |
| Status | `domain:status` | 1 (response) | Set by the server (§5.3) |
| Expire | `domain:expire` | 0–1 (response) | Date on which a `failed` domain will be deleted |
| RegistryLock | `domain:registryLock` | 0–1 (response) | Shown only when `true` |
| AuthInfo1 / AuthInfo2 | `domain:authInfo1` / `domain:authInfo2` | 0–1 (response, own domain) | Expiry dateTime of the stored AuthInfo |
| AuthInfo | `domain:authInfo` | 0–1 (response, foreign domain) | `true` if an AuthInfo1 or 2 exists |
| RegistrationDate | `domain:registrationDate` | 0–1 | Type `string`, because it can be `before 2011-05-31T00:00:00+02:00` |
| VerificationDeadlineBeforeDedelegation / …BeforeDeletion | `domain:verificationDeadlineBeforeDedelegation` / `…BeforeDeletion` | 0–1 each | NIS2 risk deadlines (§10) |
| [Dispute] | `domain:disputeData` (empty) | 0–1 | Shown on your own domain when a DISPUTE exists |
| Changed | `domain:changed` | 1 | |
| [RegAcc] RegAccId, Name, Email, Phone, Changed | `domain:regAcc/{regAccId,name,email?,phone*,changed?}` | 0–1 | Shown for own and foreign domains |

**XML dnsentry shapes** (dnsentry-5.0.xsd). `owner` is a hostname (a trailing dot is allowed; the
server returns it with a trailing dot).
```xml
<dnsentry:dnsentry xsi:type="dnsentry:NS"><dnsentry:owner>de-example.de</dnsentry:owner>
  <dnsentry:rdata><dnsentry:nameserver>ns2.de-example.de</dnsentry:nameserver>
    <dnsentry:address>81.91.170.12</dnsentry:address>        <!-- 0..n -->
    <dnsentry:addressV6>2001:608:6::11</dnsentry:addressV6>  <!-- 0..n -->
  </dnsentry:rdata></dnsentry:dnsentry>
<dnsentry:dnsentry xsi:type="dnsentry:A"><dnsentry:owner>x.de</dnsentry:owner><dnsentry:rdata><dnsentry:address>127.0.0.1</dnsentry:address></dnsentry:rdata></dnsentry:dnsentry>
<!-- AAAA: same as A; MX: rdata/preference (0-999) + rdata/exchange -->
<dnsentry:dnsentry xsi:type="dnsentry:DNSKEY"><dnsentry:owner>de-example.de.</dnsentry:owner>
  <dnsentry:rdata><dnsentry:flags>257</dnsentry:flags><dnsentry:protocol>3</dnsentry:protocol>
  <dnsentry:algorithm>8</dnsentry:algorithm><dnsentry:publicKey>AwEAA…</dnsentry:publicKey></dnsentry:rdata></dnsentry:dnsentry>
```
- In XML the NS `owner` is the domain (ACE). In K/V the `Nserver` value is the name-server host.
- The XSD allows `dnsentry` 1–20 times in create/update/chholder/chprov, and `contact` 1–7 times
  (5 holders + GR + abuse).
- K/V NS examples: `Nserver: ns1.denic.de`, `Nserver: ns2.de-example.de 81.91.170.12`, and
  `Nserver: ns2.de-example.de 2001:608:6:6:0:0:0:11` on a separate line for the IPv6 address of the
  same host. The DNSSEC page shows `Nserver: ns2.xn--tste-loa.de 192.0.2.1`. **[UNVERIFIED]**
  whether several IPs may be space-separated on one line.
- K/V Nsentry example: `Nsentry: domain-example-nsentry.de IN A 127.0.0.1`. The responses show
  `Nsentry: de-example.de. IN A 81.91.170.12`. The MX and AAAA K/V syntax is not shown in the docs.
  It is presumably `<owner> IN MX <pref> <exchange>` and `<owner> IN AAAA <ip>` **[UNVERIFIED]**.
- All DNS data must pass the **Nameserver Predelegation Check** (see the separate DENIC document;
  tool at `https://nast.denic.de`).
- DNSSEC special cases (`D29:DNSSEC`):
  - A `failed` domain's DS is not published.
  - Omitting `Dnskey` in UPDATE or CHHOLDER deletes the existing keys.
  - TRANSIT deletes all DNSKEYs.
  - DELETE removes the DS.
  - CHPROV is covered by the separate document "Operator Change for DNSSEC Domains" (not crawled).
- Missing SEP flag gives warning `46000108827`.

### 5.3 Domain status values
Sources: `D29:Domain-Status`, `D29:Domainstatus pendingCreate und serverHold`, domain XSD `statusType`.

| Status | Meaning | Allowed requests |
|---|---|---|
| `free` | Not registered | CREATE only |
| `connect` | Registered and delegated (in the zone) | Own: UPDATE, CHHOLDER, CREATE-AUTHINFO1, DELETE-AUTHINFO1, CREATE-AUTHINFO2, TRANSIT, DELETE. Foreign: CREATE-AUTHINFO2, CHPROV |
| `failed` | Registered or restored, but the predelegation check failed, so not in the zone. Must be fixed by UPDATE or CHHOLDER within **30 days**, otherwise deleted (expireWarning/expire messages). Not allowed for TRANSIT | Same as `connect` (but no TRANSIT) |
| `invalid` | The name cannot be registered | – |
| `redemptionPeriod` | Deleted. RGP of 30 days; not in the zone | Own: RESTORE. Anyone: CREATE-AUTHINFO2, then CHPROV with AuthInfo2. CREATE is refused (`56310082011`). Purged at random between 02:00 and 04:00 on the day after the RGP ends |
| `pendingCreate` | Registered but the NIS2 risk assessment is not finished. Not delegated. Becomes `connect` or `serverHold`, announced by a `domainStatusUpdate` message | – |
| `serverHold` | Registry-set **quarantine** (high risk): registered but de-delegated | – |

`pendingCreate` and `serverHold` never combine with other statuses. Domain INFO shows only
`connect`, `failed`, `pendingCreate` and `serverHold`. Status info codes in responses:
- `53000080013 Domain "Status" is "connect"`.
- `53000080014 … "pendingCreate"`.
- `53000080015 … "serverHold"`. Some XML examples show 53000080013 with "serverHold" text
  **[DOC-INCONSISTENCY]**.
- `53000080012 Domain "Status" is "failed"`.

Example status-test domains (live docs): `denic-connect-example.de`, `denic-failed-example.de`,
`denic-invalid-example.de`, `denic-rgp-example.de`.

### 5.4 Chprov / AuthInfo object
Source: `D29:Datenobjekt Chprov`. It supplements the Domain object.

| K/V keyword | XML | Occ. | Notes |
|---|---|---|---|
| AuthInfo | `domain:authInfo` (element) | 1 for CHPROV; 0–1 for INFO | Plaintext AuthInfo1 or AuthInfo2 password |
| AuthInfoHash | `hash` attribute of `domain:createAuthInfo1` | 1 for CREATE-AUTHINFO1 | 64 hex characters: SHA-256 of the password, no salt, 1 iteration |
| AuthInfoExpire | `expire` attribute of `domain:createAuthInfo1` | 0–1 | `YYYYMMDD`, at most 30 days ahead. Default is today + 30 days |

The CREATE-AUTHINFO1/2 and CHPROV responses may include `AuthInfoExpire` (`expire`, ISO
dateTime). The XSD defines `domain:createAuthInfo1Data/expire`. No example shows it being returned
**[UNVERIFIED in practice]**.

### 5.5 Verification information (NIS2)
Sources: `D29:Verifizierung`, `D29:Verifizierung-Formate-Typen-Werte`, `D29:Liste-mit-Meldungscodes-zur-Verifikation`, `EX:XMLSchema/Verification`.

The block is allowed only on PERSON/ORG contacts, at most **5 per contact** (`63200041862`). K/V
puts it after the header line `[VerificationInformation]`.

| K/V | XML (verification ns) | Occ. | Values |
|---|---|---|---|
| VerifiedClaim | `verifiedClaims/claim` | 1–3 | `name`, `address`, `email` (case-insensitive) |
| VerificationResult | `verificationResult` | 1 | `success` / `failed` |
| VerificationReference | `verificationReference` | 1 | Free text (the member's audit or ticket ID) |
| VerificationTimestamp | `verificationTimestamp` | 1 | RFC 3339 dateTime |
| VerificationEvidence | `verificationEvidence` | 1 | `idcard, passport, population_register, residence_permit, proof_of_arrival, drivers_licence, company_register, company_statement, bank_account, online_payment_account, utility_account, bank_statement, tax_statement, written_attestation, digital_attestation, postal_ver_transaction_log, email_ver_transaction_log, address_database` |
| VerificationMethod | `verificationMethod` | 1 | `auth` (eID/eIDAS), `electronic_document`, `physical_document`, `vdig` (PostIdent), `bvr` (photo ident), `pvr` (video ident), `data` (transaction record), `reachability` |
| TrustFramework | `trustFramework` | 1 | Only `de_denic` |

- In requests the XML block uses `xsi:type="verification:verificationInformationType"`, where all
  six elements are mandatory.
- In domain INFO responses it uses `domainVerificationInformationType`, where everything after
  `verifiedClaims` and `verificationResult` is optional. Foreign RegAccs see only the claims and the
  result.
- Allowed evidence × method × claim combinations are tabulated in
  `D29:Verifizierung-Formate-Typen-Werte`. A wrong combination gives `63200041867`.
- Email: if an email check failed, the full block with `failed` must be reported, and a later
  `success` must be reported too.
- Omitting all blocks in a contact UPDATE **deletes** the verification info.
- Members must keep evidence for 12 months.

### 5.6 Public registrar contact details (RegAcc object)
Sources: `D29:Datenobjekt öffentlicher Registrar-Kontaktdaten`, `D29:Antwort regaccINFO`, `EX:XMLSchema/RegAcc`.

| K/V | XML (regacc ns) | Occ. |
|---|---|---|
| RegAccId | `handle` | 1 |
| Name | `name` | 1 |
| Address | `postal/address` | 1–n |
| PostalCode | `postal/postalCode` | 0–1 (docs) / 1 (XSD) |
| City | `postal/city` | 1 |
| CountryCode | `postal/countryCode` | 1 |
| Phone | `phone` | 1–n |
| Fax | `fax` | 1–n (docs) / 0–n (XSD) |
| Email | `email` | 1 |
| URL | `url` | 0–1 |
| MemberAccId | `memberacc` | 1 |
| [General Request] / [Abuse Contact]: Type, URI-Template, Changed | `contact role="generalrequest" / "abusecontact"` holding `contact:type`, `contact:uri-template`, `contact:changed` | 0–2 |
| Changed | `changed` | 1 |

The General Request URI template is mandatory in the RegAcc profile (maintained in the RAI). It is
shown unexpanded. The RegAcc profile itself is maintained only via the RAI, not via RRI.

---

## 6. Transactions

All 19 request types listed in `EX:Request/Overview-Requests` and in the global XSD choice:
`login, logout, contactCHECK, contactCREATE, contactINFO, contactUPDATE, domainCHECK, domainCHHOLDER,
domainCHPROV, domainCREATE, domainCREATE-AUTHINFO1, domainCREATE-AUTHINFO2, domainDELETE,
domainDELETE-AUTHINFO1, domainINFO, domainRESTORE, domainTRANSIT, domainUPDATE, regaccINFO`, plus
**QUEUE-READ** and **QUEUE-DELETE** (documented in the queue chapter, not in Request examples).

The docs list **no** contact DELETE, domain RENEW, transfer query/approve/reject, domain
lock/unlock via RRI (Registry Lock is form/e-mail based), "withdraw", or separate "verify" command
(verification travels inside contact CREATE/UPDATE).

All requests are **synchronous**: the response is final for the request itself. Some follow-on
effects are **asynchronous**: the NIS2 risk assessment (`pendingCreate` → `domainStatusUpdate`
message), AuthInfo2 letter delivery, expiries, and DENIC-initiated actions (queue messages).

### 6.1 LOGIN
Source: `D29:Auftrag Login`, `D29:Antworten-LOGIN-LOGOUT`, `D29:Fehlermeldungen-LOGIN-LOGOUT`, `EX:Request/login`.

- **Object:** session. K/V `Action: login`. XML `<login><user/><password/></login>` (global
  namespace, `user` is an NMTOKEN).
- **Fields:**
  - `Version` (K/V only, 1).
  - `User` / `user` (1): the RRI login, which is a DENIC handle stored in the RegAcc profile's
    "RRI Login".
  - `Password` / `password` (1): 1–255 characters.
- **Password.** The request table says the password is sent "in clear text". The RAI stores only its
  **MD5 hash** (lowercase hex; `D29:Zugang zum RRI`, `Howtos/Experten.htm` "RRILoginPw: MD5-hash;
  lower case", `Howtos/Hash_erstellen.htm`). **[INTERPRETATION]** The RRI LOGIN carries the
  plaintext password over TLS, and the MD5 hash is what you enter in the RAI. pyrri also sends
  plaintext. The policy recommends at least 12 characters and more than 70 bits of entropy.
- **Response:** `Result`, `STID`.
- **Errors:**

| Code | Meaning |
|---|---|
| `83000000010` | Login failed (wrong user or password) |
| `63100020005` | Too many failed logins, temporarily blocked |
| `73100000005` | Maximum number of sessions reached |
| `63100040202` | User keyword not exactly once |
| `63100040302` | Password keyword not exactly once |
| `63000040110` | Action not recognised |
| `83000000004` | XML schema validation failed |
| `63100064002` | Authorization failure (listed in the code list only) |

```
Version: 5.0
Action: login
User: DENIC-1000022-RRI
Password: ********
--> Result: success
    STID: 0b97f9b7-9f0b-11df-a9e2-9519b5688882
```
The example on `D29:Auftrag Login` actually shows a logout **[DOC-INCONSISTENCY]**. Use
`EX:Request/login` instead.

### 6.2 LOGOUT
Source: `D29:Auftrag Logout`.
- K/V `Action: logout`. XML `<logout/>`. No other fields.
- Response: `Result`, plus `STID` only on success. The test-environment info 13000000011 also
  appears only on success.

### 6.3 contact CREATE
Source: `D29:Auftrag contactCREATE`, `D29:Antworten contactCREATE und contactUPDATE`.

- K/V `Action: create` with `Handle:` (contact). XML `<contact:create>`.
- **Fields:** `CtId` (0–1), plus all contact fields (§5.1) and optionally up to 5 verification
  blocks.
- **Requirements:** the handle must not exist (`63200040602`/…), must start with your RegAccId,
  must have Email and Phone for PERSON/ORG, and must not carry Organisation for ORG.
- **Checks:** syntax check, plus the **completeness check** on Name, Address, PostalCode and City.
  Superfluous blanks are trimmed. Examples of rejected input:
  - Name: digits only, specials only, fewer than 3 characters, one repeated letter, 5 or more
    identical characters in a row.
  - Postal codes for DE/AT/CH must be numeric with 5 or 4 digits.
  - Error codes `63400000001`–`63400000004` (`D29:Tabelle Kontaktdaten-Prüfungen`).
- **Response:** `Result`, `STID`, `CTID`, and Info/Warning/Error messages.
- **Authorisation:** only the RegAcc encoded in the handle prefix may create it.
- **Effects:** synchronous. No queue message is documented.

```
Version: 5.0
Action: create
Handle: DENIC-1000022-EXAMPLE-PERSON
Type: PERSON
Name: Max Mustermann
Organisation: DENIC eG
Address: Theodor-Stern-Kai 1
PostalCode: 60596
City: Frankfurt am Main
CountryCode: DE
eMail: email-1@denic.de
Phone: +49.6927235x290
CTID: kv-7bf04fa8
[VerificationInformation]
VerifiedClaim: name
VerifiedClaim: address
VerificationResult: success
VerificationReference: ABC123/45GHT
VerificationTimestamp: 2023-11-11T15:36:21+02:00
VerificationEvidence: idcard
VerificationMethod: auth
TrustFramework: de_denic
--> RESULT: success / STID: … / CTID: kv-7bf04fa8
```
REQUEST type example:
```
Version: 5.0
Action: create
Type: REQUEST
Handle: DENIC-99995-GENREQ
Uri-template: https://denic.de/contact/form{?Alabel,Ulabel}
```
The example `{?Alabel,Ulabel}` is RFC 6570 level 3 syntax, which contradicts the "level 1 only"
statement **[DOC-INCONSISTENCY]**.

### 6.4 contact UPDATE
Source: `D29:Auftrag contactUPDATE`.

- K/V `Action: update` with `Handle:`. XML `<contact:update>` (same structure as create).
- **Full replacement:** mandatory fields must always be sent, and omitted optional fields
  (Organisation, extra Address/Email lines, verification blocks) are deleted.
- **Requirements:** the contact must exist and belong to your RegAcc (`63200020603`).
- **Rules:**
  - Name is immutable (`63220080801`).
  - Type can change between PERSON and ORG unless the contact is used on a DISPUTE domain.
    Error `63220080701` "Type cannot be changed" still exists in the error table.
  - On DISPUTE domains the holder's name, organisation and address fields are frozen; use DENIC
    Business Services instead. Verification info can still be changed.
  - `53000080002` "This value cannot be deleted".
  - Registry-Locked domains' contacts are protected.
- **Semantics:** a contact UPDATE triggers a **new risk assessment** (syntax, completeness, risk)
  for the domains that use it as holder. **[INTERPRETATION]** of "triggers a new verification
  process for a domain". Portfolio domains are not rescanned systematically, only event-driven.
- **Response:** same as CREATE.

### 6.5 contact CHECK
Source: `D29:Auftrag contactCHECK`, `D29:Antwort contactCHECK`.

- K/V `Action: check` with `Handle:`. XML `<contact:check><contact:handle/></contact:check>`.
- You can query **only your own contacts**.
- Response: `Handle`, `Status: free | exist | invalid`. XML in `tr:data/contact:checkData`.

### 6.6 contact INFO
Source: `D29:Auftrag contactINFO`, `D29:Antwort contactINFO`.

- K/V `Action: info` with `Handle:`. XML `<contact:info><contact:handle/></contact:info>`.
- **Own contacts only.** The contact must exist.
- Response: all contact fields plus `Changed`, `DisputeReference` (0–1) and the verification
  blocks. XML in `contact:infoData`. URI templates are returned unexpanded.

### 6.7 domain CREATE
Source: `D29:Auftrag domainCREATE`, `D29:Antworten Domain CREATE, UPDATE, CHHOLDER, RESTORE, DELETE und TRANSIT`.

- K/V `Action: create` with `Domain:`. XML `<domain:create>` with `handle, ace?, contact{1,7},
  dnsentry{1,20}`.
- **Fields:** `CtId`, `Domain`, `Domain-Ace?`, `Holder` 1–5, `GeneralRequest?`, `AbuseContact?`,
  then either `Nserver` 2–13 or `Nsentry` 1–5, and optionally `Dnskey` 0–20.
- **Requirements:**
  - The domain must be free. Status `redemptionPeriod` gives `56310082011`; an existing domain gives
    `63310062004`.
  - All contacts must exist (`53000060009`), belong to you, and have a type that fits the role
    (`63300080700`).
- **Semantics:**
  - The predelegation check runs synchronously.
  - If it **fails**, the domain is still registered with status `failed`. The result is `success`,
    with `ERROR 53300102912` and `WARNING 33300102900 … "failed"` carrying the expiry date as an
    argument. The domain must be fixed within 30 days.
  - If it **passes**, the domain goes to the asynchronous **risk assessment**. If that is not
    immediately final, the status becomes `pendingCreate` (info `53000080014`), and the later
    outcome (`connect` or `serverHold`) comes as a **`domainStatusUpdate`** queue message.
  - A failed domain goes to the risk assessment once it is connected.
  - Contacts without phone or email are accepted for CREATE.
  - A holder with verified contact data (result `success`) makes the domain verified automatically.
- **Response:** `Result`, `STID`, `CTID`, plus messages: status info, predelegation messages, and
  `16000063119 DNS data was checked and accepted`.

```
Version: 5.0
Action: CREATE
Domain: domain-example-nserver.de
Holder: DENIC-1000022-EXAMPLE-PERSON
Generalrequest: DENIC-1000022-EXAMPLE-GR
Abusecontact: DENIC-1000022-EXAMPLE-ABUSE
Nserver: ns1.denic.de
Nserver: ns2.denic.de
CTID: cba-987654321
--> Result: success
    INFO: 53000080014 Domain "Status" is "pendingCreate"
    STID: 3727d839-…   CTID: cba-987654321
```

### 6.8 domain UPDATE
Source: `D29:Auftrag domainUPDATE`.

- K/V `Action: update`. XML `<domain:update>` with the same structure as create.
- **Requirements:** the domain exists and is administered by the requesting RegAcc (`63300022003`
  otherwise).
- **The holder cannot be changed.** The Holder values must equal the current ones (`54300062506
  Holder does not match`); use CHHOLDER to change holders.
- **Full-replace semantics:** omitted optional data (GR, Abuse, Dnskey …) is deleted.
- The whole request is atomic.
- If new name servers fail the predelegation check, the UPDATE is rejected and nothing changes.
  For a `failed` domain, a passing UPDATE connects it.
- The order of name servers may change.
- **Semantics:** it automatically triggers a risk assessment. If the domain was `failed`, the
  transition `failed → pendingCreate` produces a notification. Contacts without phone or email are
  still accepted.
- Response: as for CREATE (e.g. info `53000080014`). Registry-Locked domains are rejected with
  `53000080009`.

### 6.9 domain CHHOLDER
Source: `D29:Auftrag domainCHHOLDER`.

- K/V `Action: chholder`. XML `<domain:chholder>` (same type as update).
- Changes the holder set (add or remove, up to 5). All other domain data is sent as in UPDATE.
- **Requirements:** own domain.
  - Under an active DISPUTE, CHHOLDER is allowed only if the holder's mandatory data stays the same
    (`53000080011`).
  - New holders must have a phone number (`63300085940 Missing phone for holder`). An unchanged
    holder without a phone number is tolerated.
- **Effects:**
  - **All stored AuthInfos are invalidated** when the holder changes (info `16330088732`).
  - The risk assessment is triggered.
  - The response may carry deadline infos: `16350000040` (dedelegation by …) and `16350000041`
    (deletion by …).
  - DNS predelegation behaves as in UPDATE.
- Example response messages: `INFO: 53000080013 Domain "Status" is "connect"` and `INFO: 16350000040
  Verification information must be provided for the holder(s) to avoid dedelegation by
  [2024-12-09T15:45:01+01:00]`.

### 6.10 domain DELETE
Source: `D29:Auftrag domainDELETE`.

- K/V `Action: delete`. XML `<domain:delete>` with `handle, ace?, contact{0,5}`.
- **Fields:** `CtId`, `Domain` (1), `Holder` (0–5). If Holder is given it must match the stored
  holder. Any other data (nserver etc.) is ignored.
- **Requirements:** own domain. Not possible under Registry Lock (by e-mail to DENIC only).
- **Effects:**
  - The domain moves to `redemptionPeriod` (RGP, 30 days). After that it is purged at a random
    time in the 02:00–04:00 window on the following day.
  - AuthInfo1 and AuthInfo2 are deleted, and the DS is removed from the zone.
  - If a **DISPUTE** exists, the domain is immediately re-registered to the dispute holder with no
    RGP (`13350000001 Domain bears a DISPUTE entry and can therefore not be restored`).
  - DENIC-side deletions (e.g. court ruling) have no RGP and are announced via `domainDelete`.
  - Connected name servers do not block deletion.

### 6.11 domain RESTORE
Source: `D29:Auftrag domainRESTORE`.

- K/V `Action: restore`. XML `<domain:restore>` with `handle, ace?`.
- **Requirements:** status `redemptionPeriod` (`66310082014 Domain is not in Redemption Grace
  Period` otherwise) and the domain was administered by the requesting RegAcc. Another RegAcc must
  use CREATE-AUTHINFO2 followed by CHPROV.
- **Effects:**
  - The domain is reactivated.
  - If it was `failed` before deletion, a new 30-day expiry is set.
  - Domains deleted for missing verification have no RGP and cannot be restored.
  - A RESTORE without AuthInfo works even when contacts have no phone number.

### 6.12 domain TRANSIT
Source: `D29:Auftrag domainTRANSIT`, `D29:Rahmenbedingungen zur Registrierung`.

- K/V `Action: transit` with `Disconnect: true|false` (0–1). XML `<domain:transit
  disconnect="true|false"><domain:handle/>…`.
- **Meaning:** the RegAcc gives the domain to DENIC's administration (no holder delete request). The
  RegAcc loses access.
- **Requirements:** own domain, not `failed`. Registry-Locked domains can go to TRANSIT only manually
  via DENIC, and without disconnect.
- **Effects:**
  - `disconnect=true` replaces the NS with an entry pointing to a DENIC web page. `false` keeps them.
  - AuthInfo1 is deleted; the response informs about this (`16330088732`). AuthInfo2 is unaffected.
  - General Request, Abuse Contact and all DNSKEYs are removed.
  - The verification period is lifted if the TRANSIT letter is delivered and its code is used.
  - Moving out of transit to a new provider (via CHPROV) triggers a risk assessment.
- **Errors:** `63360043403` / `63360063402` (Disconnect), and `63360082531 For TRANSIT, a Holder
  Handle is mandatory`. That last code is in the code list, but the TRANSIT request table does not
  list a Holder field **[UNVERIFIED whether Holder is required]**.

### 6.13 domain CHECK
Source: `D29:Auftrag domainCHECK`, `D29:Antworten domainCHECK und domainINFO`.

- K/V `Action: check` with `Domain:` and optional `Domain-Ace:`. XML `<domain:check>` with
  `handle, ace?`.
- No requirements; works on any domain.
- Response: `Domain`, `Domain-Ace`, `Status` (§5.3). XML in `domain:checkData` with `handle, ace,
  status`.
- An invalid name gives `63310062007 Inadmissible value for keyword "Domain" [Domain does not meet
  rules for domain name format]` (STD 3 rules), or `53300062003`.
- The K/V example prints `Status: exist` and `pendigCreate` **[DOC-INCONSISTENCY]**. Real values
  follow statusType.

### 6.14 domain INFO
Source: `D29:Auftrag domainINFO`, `D29:Antworten domainCHECK und domainINFO`, `D29:.de Registry Lock`.

- K/V `Action: info` with `Domain`, optional `Domain-Ace`, `AuthInfo` and `Recursive: true|false`.
  XML `<domain:info recursive="true|false">` with `handle, ace?, authInfo?`.
- **Recursive** controls whether contact data is embedded. Without it you get handles only, or
  empty headers.
- **AuthInfo** (AuthInfo1 or AuthInfo2 plaintext) lets **any** RegAcc see the holder data of a
  foreign domain. It works repeatedly until the AuthInfo expires or is consumed by CHPROV/CHHOLDER.
  A non-matching AuthInfo gives `63370088701` (C/I).
- **Visibility matrix** (from the examples):

| Case | What is returned |
|---|---|
| Own domain, recursive=true | Handles and full data for GR, Abuse and holders; full verification blocks; deadlines; full [RegAcc] (Id, Name, Email, Phone, Changed); `AuthInfo1`/`AuthInfo2` expiry dates when stored |
| Own domain, recursive=false | Domain data + deadlines; `[General Request]`/`[Abuse Contact]`/`[Holder]` with **Handle only**; [RegAcc] Id + Name |
| Foreign + valid AuthInfo, recursive=true | Contact data **without handles**; verification reduced to claims + result; deadlines; `AuthInfo: true`; full [RegAcc] |
| Foreign + valid AuthInfo, recursive=false | Empty section headers; deadlines; RegAcc Id + Name |
| Foreign, no AuthInfo, recursive=true | GR/Abuse URI templates; ORG holders with full data; PERSON holders with type only (XML example) |
| Foreign, no AuthInfo, recursive=false | Empty headers; no deadlines; RegAcc Id + Name |

  The K/V example for "foreign, no AuthInfo, recursive=true" shows full PERSON data, which
  conflicts with the XML example and with the NIS2 publication rule that PERSON data is not
  published **[DOC-INCONSISTENCY]**.

- **Response fields (K/V):**
  - Domain fields: `Domain`, `Domain-Ace`, `Nserver`/`Nsentry`/`Dnskey`, `Status`, `RegistryLock`
    (only when true), `RegistrationDate`, `VerificationDeadlineBeforeDedelegation`,
    `VerificationDeadlineBeforeDeletion`, `AuthInfo1`/`AuthInfo2`/`AuthInfo`, `Changed`.
  - Sections: `[General Request]`, `[Abuse Contact]`, `[Holder]` (one per holder, each followed by
    its own `[VerificationInformation]` blocks), `[Dispute]`, `[RegAcc]`.
  - Keywords use CamelCase.
  - XML order follows `domain:infoDataType` (§13).
  - Older layouts (RRI 3.0, Registry-Lock page) put `RegAccId:` and `RegAccName:` at top level.
    In 5.0 they sit in `[RegAcc]` / `domain:regAcc`.
- Deadlines are not returned when an invalid AuthInfo is given.
- GR and Abuse are shown only if they are set on the domain; there is no fallback to the RegAcc
  profile.

### 6.15 domain CREATE-AUTHINFO1
Source: `D29:Auftrag domainCREATE-AUTHINFO1`, `D29:Antworten CREATE-AUTHINFO1, CREATE-AUTHINFO2, CHPROV`.

- K/V `Action: create-authinfo1` with `Domain`, `AuthInfoHash` (1) and `AuthInfoExpire` (0–1,
  `YYYYMMDD`). XML `<domain:createAuthInfo1 hash="<64hex>" expire="YYYYMMDD">` with `handle, ace?`.
- **Who:** only the **administering (sponsoring) RegAcc**.
- **Rules:**
  - The password is 8–16 characters from the `authinfo-val` charset.
  - The hash is SHA-256 hex, no salt, 1 iteration.
  - Only one AuthInfo1 per domain (`63391068704 AuthInfo1 already exists`). It can coexist with an
    AuthInfo2.
  - Validity is at most 30 days; it is auto-deleted at expiry.
  - For a `failed` domain, the domain's expiry date is mentioned in the AuthInfo notification
    e-mail.
- **Response:** `Result`, `STID`, `CTID`, and status/deadline infos as in the examples. It may also
  carry `AuthInfoExpire`.
- **Errors:** `63391048502`/`63391068503` (hash), `63391048602`/`63391068603` (expire),
  `63300062009` (no such domain), `63300022003` (foreign domain).
- **Usage:** the registrar hands the plaintext to the holder, who gives it to the gaining registrar
  for CHPROV.

```
Version: 5.0
Action: create-authinfo1
Domain: de-example.de
Authinfohash: 4213d924230224fd719218b4acbd92f96ebe4344f3d5d1478dede1aa44e4cf4b
Authinfoexpire: 20100724
```

### 6.16 domain DELETE-AUTHINFO1
Source: `D29:Auftrag domainDELETE-AUTHINFO1`, `EX:Request/domainDELETE-AUTHINFO1`.

- K/V `Action: delete-authinfo1` with `Domain`. XML `<domain:deleteAuthInfo1>` with `handle,
  ace?`.
- Only the administering RegAcc may send it, and an AuthInfo1 must exist (`63392068709 AuthInfo1
  does not exist`).
- AuthInfo2 is unaffected.
- Response: `Result`, `STID`, `CTID`.
- The DENIC-29 page's examples are copies of CREATE-AUTHINFO2 **[DOC-INCONSISTENCY]**. Use
  `EX:Request/domainDELETE-AUTHINFO1`.

### 6.17 domain CREATE-AUTHINFO2
Source: `D29:Auftrag domainCREATE-AUTHINFO2`.

- K/V `Action: create-authinfo2` with `Domain`. XML `<domain:createAuthInfo2>` with `handle, ace?`.
- **Who:** **any member / RegAcc** (typically the gaining one).
- **Effects:**
  - DENIC generates the password and sends a **postal letter to every holder**, worldwide, all with
    the same AuthInfo2.
  - The **administering RegAcc gets an `authInfo2Notify`** queue message.
  - Validity is at most 30 days.
  - Only one AuthInfo2 per domain (`63393068704 AuthInfo2 already exists`). An existing AuthInfo1
    stays.
  - Allowed in statuses `connect`, `failed` and `redemptionPeriod`.
    - For `failed`, the letter states the domain's expiry.
    - For `redemptionPeriod`, the **RGP is reset to 30 days**. It can be requested only until
      midnight on the day of the purge release.
  - If the letter is undeliverable, DENIC deletes the AuthInfo2 and sends an `authInfo2Delete`
    message.
  - DELETE removes the AuthInfo2.
  - In the test environment the AuthInfo2 is always `secret`.
- The page also says "the AuthInfo2 has to be 8–16 characters / SHA-256 hash". That is apparently
  copied from AuthInfo1, since the client sends no hash or password **[DOC-INCONSISTENCY]**.

### 6.18 domain CHPROV (provider change / transfer)
Source: `D29:Auftrag domainCHPROV`, `D29:Fehlermeldungen bei Providerwechsel-Aufträgen`.

- K/V `Action: chprov`. XML `<domain:chprov>` with `handle, ace?, contact{1,7}, dnsentry{1,20},
  authInfo` (chprovType extends updateType, so per the XSD `authInfo` comes **after** all
  dnsentries). The doc example places `authInfo` between dnsentry elements, which would fail
  validation **[DOC-INCONSISTENCY]**.
- **Fields:** the complete domain data (Holder 1–5, GR, Abuse, Nserver/Nsentry, Dnskey) plus
  `AuthInfo` (plaintext AuthInfo1 or AuthInfo2). All mandatory data must be present
  (`53370080005`).
- **Who:** a RegAcc that does **not** administer the domain (`63380063209 Illegal operation on own
  domain`). The contact handles used must belong to the **requesting** RegAcc. The AuthInfo must
  match (`63370088701`, `56000088709 Specified AuthInfo2 does not exist`).
- **Semantics:**
  - **Immediate and synchronous.** There is no pending, approve or reject state.
  - It may be combined with a holder change, but not when a DISPUTE exists.
  - Using AuthInfo1 deletes it and keeps any AuthInfo2 if the holder is unchanged. Using AuthInfo2
    deletes both.
  - CHPROV with AuthInfo2 also **restores a domain in `redemptionPeriod`** to the requester.
  - The losing RegAcc receives a **`chprovAuthInfo`** message with `new` and `old` RegAccIds.
    The How-to says both providers are informed via the queue **[UNVERIFIED for the gaining
    side]**.
  - A risk assessment follows.
  - All holders need a phone number (`63300085940`).
  - Registry Lock must be removed first.
  - For DNSSEC operator changes see the separate document (not covered here).
- **Response:** as for CREATE-AUTHINFO1 (status and deadline infos).

```
Version: 5.0
Action: chprov
Domain: de-example.de
Holder: DENIC-1000002-HOLDER
Generalrequest: DENIC-1000002-GENERAL
Abusecontact: DENIC-1000002-ABUSE
Nserver: ns1.beispiel-eins.de
Nserver: ns2.beispiel-eins.de
Authinfo: secret
CTID: cba-987654321
```

### 6.19 regacc INFO
Source: `D29:Auftrag regaccINFO`, `D29:Antwort regaccINFO`.

- K/V `Action: info` with `RegAcc: DENIC-99995`. XML `<regacc:info><regacc:handle/></regacc:info>`.
- Works on **any** RegAcc, your own or others.
- Response: fields as in §5.6. XML in `regacc:infoData`. K/V uses `Regaccid`, `Memberaccid`,
  `[General Request]` and `[Abuse Contact]`.
- Errors: `63310062008` (invalid value), `63300062010 RegAcc doesn't exist`.

### 6.20 QUEUE-READ
Source: `D29:Auftrag QUEUE-READ`, `D29:Antworten QUEUE-READ`.

- K/V `Action: queue-read` with optional `MsgType: <type>` (case-insensitive, e.g.
  `authinfo2delete`). XML `<msg:queue-read msgType="authInfo2Delete"/>`; the attribute is optional
  and the element is empty.
- Returns **one** message: the **oldest** by MsgTime, or the oldest of the given type.
- **Response:**
  - K/V: `Result`, `STID`, `Msgcnt`, `Msgtime`, `Msgid`, `Msgtype`, then the type-specific fields.
  - XML: `tr:data/msg:message` with attributes `msgid` (required), `msgcnt` (optional) and `msgtime`
    (required), containing exactly one type element.
- `MsgCnt` is the total count, or the count for that type if a type was given.
- **Empty queue:** K/V returns `Msgcnt: 0`. XML omits msgcnt (and presumably the message element)
  **[UNVERIFIED exact XML]**.
- An invalid type gives `63600063502`.
- No quota cost.
- If messages are older than 3 days, a daily reminder e-mail goes to the RegAcc's `EMailTo`.
- RegAcc profile field `MsgFeed: "rri"` means messages are collected via RRI.

### 6.21 QUEUE-DELETE
Source: `D29:Auftrag QUEUE-DELETE`, `D29:Antwort QUEUE-DELETE`.

- K/V `Action: queue-delete` with `MsgId` (1, required), `MsgType` (0–1) and `CtId` (0–1).
  XML `<msg:delete msgid="…" msgType="…"/>`.
- Only the **oldest** message (overall, or of the given type) can be deleted:
  - `63650063607 This message is not the oldest`.
  - `63650063609 MsgId does not exist`.
  - `63650043610` MsgId keyword missing.
- Response: `Result`, `STID`, `CTID`. No quota cost.

---

## 7. AuthInfo mechanism (summary)
Sources: §6.15–6.18, `D29:Aufträge zum Providerwechsel`, `Howtos/Hash_erstellen.htm`.

| | AuthInfo1 | AuthInfo2 |
|---|---|---|
| Created by | Sponsoring RegAcc (CREATE-AUTHINFO1) | Any RegAcc (CREATE-AUTHINFO2) |
| Password origin | Chosen by the registrar; only the SHA-256 hex hash is sent | Generated by DENIC; mailed by post to the holder(s) |
| Length / charset | 8–16 characters, `authinfo-val` | Generated by DENIC (`secret` in test) |
| Validity | ≤ 30 days (client sets `YYYYMMDD`, default +30) | 30 days |
| Count | 1 per domain | 1 per domain |
| Notifications | `authInfoExpire` **[UNVERIFIED trigger timing]** | `authInfo2Notify` to the sponsor; `authInfo2Delete` if the letter is undeliverable; `authInfoExpire` |
| Deleted by | Its use in CHPROV; CHHOLDER (holder change); TRANSIT; DELETE; DELETE-AUTHINFO1; expiry | Its use in CHPROV; CHHOLDER (holder change); DELETE; expiry; undeliverable letter. Not by TRANSIT |
| Used in | CHPROV, INFO (holder data) | CHPROV (including restore from RGP), INFO |

Domain INFO shows `AuthInfo1:` and `AuthInfo2:` expiry dates to the sponsor and `AuthInfo: true`
to others.

---

## 8. Process semantics (NIS2 risk assessment, deadlines, RGP, dispute, lock)
Sources: `D29:Prozesse-Checks-und-Risikobewertung`, `D29:Risikostufen und Domain-Aufträge`, `D29:Risikostufen-Tabelle`,
`D29:Risikostufen und Kommunikation`, `D29:Verifizierung`, `D29:.de Registry Lock`, changelogs 019/023.

- **Risk assessment** runs asynchronously after domain CREATE, CHHOLDER, CHPROV, UPDATE and contact
  UPDATE. Traffic-light levels:

| Level | Domain state | Deadline | What happens |
|---|---|---|---|
| low (green) | Delegated | None | – |
| suspicious (yellow) | Delegated | **14 days** to verify | If no verification arrives, the level rises to high |
| high (red) | Not delegated: `serverHold` (quarantine) | **90 days** | If no verification arrives, DENIC deletes the domain with **no RGP** and it cannot be restored |

  A failed verification always means quarantine. Pre-verified handles (via contact CREATE/UPDATE
  with `success`) give a low risk level. Handles whose pre-verification failed give an immediately
  high level.
- **Deadline reporting:**
  - Response infos `16350000040` (…to avoid dedelegation by `<date>`) and `16350000041` (…deletion
    by `<date>`). Since 2025-04 their arguments are `Date: …` and `VerificationClaims: a;b`.
  - Domain INFO `VerificationDeadlineBefore*`.
  - Queue messages `domainStatusUpdate` and `contactVerificationRequired`.
  - E-mails to holders. The timing changed in 2026-08: the termination e-mail now comes 13 days
    before the end.
- **To resolve:** send contact UPDATE with verification info for the holder handle(s). All holders
  of a multi-holder domain must be verified.
- **Publication (NIS2):** ORG holder data (name, address, email, phone), the registration date and
  the administering member are published via the information services. For PERSON holders only the
  registration date and member are published.
- **Phone:** mandatory on contact CREATE/UPDATE since 2026-01-28. From April 2027 DENIC may request
  verification for domains whose holders lack a phone number.
- **Failed domains:** 30 days to connect. `expireWarning` is sent 1 week before and `expire` on
  deletion. `failed` domains cannot go to TRANSIT.
- **RGP:** 30 days after DELETE, then release in the purge window (02:00–04:00) on the following day
  with no pending-delete phase. Out-of-band deletion (holder waiver) can end the RGP early.
- **DISPUTE:**
  - Freezes the holder's address data.
  - Blocks CHHOLDER and CHPROV+holder change.
  - On DELETE the domain goes to the dispute holder.
  - Shown as `[Dispute]` / `domain:disputeData`, and as `DisputeReference` on the contact.
- **.de Registry Lock** is a paid product.
  - Every RRI write (UPDATE, CHHOLDER, CHPROV, TRANSIT, DELETE, and contact UPDATE of the locked
    domain's contacts) is rejected with `53000080009 Request rejected - this domain is locked!`.
  - Changes go by signed e-mail or form to DENIC and are confirmed by the lock contact via an OTP.
  - INFO shows `RegistryLock: true` (only when locked).
  - Queue messages `lockCreate` and `lockDelete` are sent when DENIC sets or removes the lock.

---

## 9. Message queue: message types
Sources: `D29:Aufträge zur Nachrichtenqueue`, `D29:Nachrichtentyp *`, `EX:Message/*`, `EX:XMLSchema/Message`.

The message XSD `msgTypeType` defines **15** types: `expireWarning, expire, authInfoExpire,
authInfo2Notify, chprovAuthInfo, domainDelete, authInfo2Delete, lockCreate, lockDelete,
domainUpdate, domainTransit, contactUpdate, contactDelete, domainStatusUpdate,
contactVerificationRequired`. The DENIC-29 chapter documents 10 of them in detail; the remaining 5
are only in `EX:Message/*`.

Every message has `msgid` (UUID, used for deletion), `msgtime` (creation time) and `msgcnt`. In
XML these are attributes of `msg:message`. In K/V they are `Msgid:`, `Msgtime:`, `Msgcnt:` and
`Msgtype:`. The domain block in XML is `<msg:domain><msg:handle/><msg:ace/></msg:domain>`; in K/V
it is `Domain:` and `Domain-ace:`.

| Type | Trigger / meaning | Content (XML / K/V) |
|---|---|---|
| `expireWarning` | 1 week before a domain expires (`failed` domain not connected within 30 days) | `msg:expireWarning/msg:domain{handle,ace,expire}`, 1..n domains per the XSD. K/V `Domain`, `Domain-ace`, `Expire` |
| `expire` | On the day a domain expired or was deleted | Same shape as expireWarning |
| `authInfoExpire` | Expiry date of an AuthInfo1/AuthInfo2 | `msg:domain`, `msg:authinfoexpire` (dateTime). K/V `Authinfoexpire` |
| `authInfo2Notify` | An AuthInfo2 was generated for one of your domains (sent to the sponsor) | `msg:domain` |
| `authInfo2Delete` | DENIC deleted the AuthInfo2 because the letter was undeliverable | `msg:domain` + `msg:message` codes `11300088725 AuthInfo deleted` and `11300088726 AuthInfo letter could not be delivered`. The K/V example shows 113000**77**725/726 **[DOC-INCONSISTENCY]** |
| `chprovAuthInfo` | Your domain was moved away by CHPROV (sent to the losing RegAcc) | `msg:domain`, `msg:new` (gaining RegAccId), `msg:old` (losing). K/V `Chprov-To`, `Chprov-From` |
| `domainDelete` | DENIC (legal department, or expiry of a verification deadline) deleted the domain | `msg:domain` + `msg:message code=16350000031 "Domain has been deleted"` with an argument such as `request-reference DENIC#:<ticket>`, `no verification information provided`, or empty. K/V `Message: 16350000031 Domain has been deleted [ … ]` |
| `contactDelete` | Contacts auto-deleted after their retention period | `msg:contactDelete/msg:handles/msg:handle` (1–100). K/V repeated `Handle:`. The XSD reasonType is `UNUSED_CONTACT` (unused in the examples) |
| `contactUpdate` | DENIC changed a contact (e.g. via a ticket) | `msg:contact/msg:handle` + messages "Contact has been updated - please check contact data with RRI-INFO command [request-reference DENIC#:…]" and "Contact update impacts all referenced domains". Codes are 16350000041/42 in XML but 13000000041/42 in K/V **[DOC-INCONSISTENCY]**; 16350000041 also clashes with the deadline code. K/V `contact:` |
| `domainUpdate` | DENIC changed domain data | `msg:domain` + `16350000030 Domain has been updated - please check domain data with RRI-INFO command [request-reference …]` |
| `domainTransit` | Domain placed in TRANSIT (by DENIC / ticket) **[UNVERIFIED trigger]** | `msg:domain` + `16350000032 Domain in Transit [request-reference …]` |
| `lockCreate` | Registry Lock set | `msg:domain` + `13000000040 Domain has been locked [request-reference …]` |
| `lockDelete` | Registry Lock removed | `msg:domain` + `13000000041 Domain has been unlocked [request-reference …]` |
| `domainStatusUpdate` | After a successful domain request (registered, changed, connected) once the risk assessment decided the status, or when verification is required | `msg:domain`, `msg:holders/msg:handle*` (holders for which **no** verification is required), `msg:status` (connect/serverHold/…), optional `msg:verificationDeadlineBeforeDedelegation`, `msg:verificationDeadlineBeforeDeletion`, `msg:message*` (16350000040/41 with `Date:` and `VerificationClaims:` arguments). K/V `Holder:`, `Status:`, `VerificationDeadline…:`, `Message:` |
| `contactVerificationRequired` | A contact (handle) must be verified | `msg:handle`, `msg:verificationClaims/msg:claim+`, `msg:numberOfReferencedDomainsTotal`, `msg:earliestDomainForDedelegation{domain,verificationDeadline}?`, `msg:earliestDomainForDeletion{domain,verificationDeadline}`, messages `16350000050 Verification information must be provided for the handle to avoid dedelegation and/or deletion` and `16350000051 Please provide the requested verification information by means of a Contact UPDATE`. K/V `Handle`, `VerificationClaim`, `NumberOfReferencedDomainsTotal`, `Message`, then sections `[earliest domain for dedelegation]` (Domain, Domain-ace, VerificationDeadlineBeforeDedelegation) and `[earliest domain for deletion]` (… VerificationDeadlineBeforeDeletion). Only the domain with the earliest deadlines is named |

Example (K/V `chprovAuthInfo`):
```
Result: success
STID: 253526e9-9f04-11df-a9e2-9519b5688882
Msgcnt: 2
Msgtime: 2010-07-11T10:09:24+01:00
Msgid: 02699380-9c7a-11de-8188-9ff72af94906
Msgtype: chprovauthinfo
Domain: de-example.de
Domain-ace: de-example.de
Chprov-to: DENIC-1000002
Chprov-from: DENIC-99999
```
Example (XML `domainStatusUpdate`, abridged):
```xml
<tr:data><msg:message xmlns:msg="http://registry.denic.de/msg/5.0" msgid="8960348c-…" msgcnt="1" msgtime="2024-06-01T15:51:08+02:00">
 <msg:domainStatusUpdate>
  <msg:domain><msg:handle>de-example.de</msg:handle><msg:ace>de-example.de</msg:ace></msg:domain>
  <msg:holders><msg:handle>DENIC-1000002-BadGuy</msg:handle><msg:handle>DENIC-1000002-GoodGuy</msg:handle></msg:holders>
  <msg:status>serverHold</msg:status>
  <msg:verificationDeadlineBeforeDeletion>2024-06-13T15:51:08+02:00</msg:verificationDeadlineBeforeDeletion>
  <msg:message level="info" code="16350000041"><tr:text>Verification information must be provided for the holder(s) to avoid deletion by</tr:text>
   <tr:argument>Date: 2024-06-13T15:51:08+02:00</tr:argument><tr:argument>VerificationClaims: address;name</tr:argument></msg:message>
 </msg:domainStatusUpdate></msg:message></tr:data>
```
One XML example repeats `verificationDeadlineBeforeDeletion` after the message, which is invalid
per the XSD order **[DOC-INCONSISTENCY]**.

---

## 10. Error code tables

### 10.1 General (any request)
Source: `D29:Fehlermeldungen des .de-Registrierungssystems`.

| Code | Message |
|---|---|
| 13000000011 | Request was processed in test environment |
| 13000000022 / 33000000022 | Used quota |
| 53000000008 | Daily quota exceeded |
| 53000000012 | Concurrent write access to the same business object is prohibited |
| 53000020002 | Unauthorized request |
| 60009500901 | PGP key does not comply |
| 63000000006 | Invalid key/value pair format |
| 63000000007 | Request shows semantics error |
| 63000000012 | Unknown Error |
| 63000040110 / 63000060102 | Action missing / not permitted |
| 63000040410 / 63000060402 | Version missing / not permitted |
| 63000060003 | An indicated Contact is invalid |
| 63000060008 | Invalid characters |
| 63000060015 | Value too long |
| 63000060504 | CTID used before |
| 63000060508 | Invalid Ctid |
| 63300080010 | Required domain data is missing |
| 83000000000 | Request message too long |
| 83000000002 | Encoding not supported |
| 83000000004 | XML schema validation failed |

Additional codes from the full list:

| Code | Message |
|---|---|
| 53000020013 / 53000020019 / 66000020020 | Signature verification (e-mail channel) |
| 56000000013 | Technical error |
| 56000020021 | Access control limit exceeded |
| 58000000002 / 58000000027 | Mail encoding / header |
| 63000080009 | Request type missing (Domain or Handle) |
| 63200040602 | Keyword "Handle" or "Domain" must appear once and just once |
| 63200080108 | Value of "Action" not permitted here |
| 76000000001 | Registry Service temporarily not available |
| 76000000002 | Timeout while processing request |

### 10.2 Domain requests
Source: `D29:Fehlermeldungen bei Domainaufträgen`. Each code is followed by the operations it
applies to: C = create, U = update, CH = chholder, R = restore, D = delete, T = transit,
DI = info, DC = check.

- 13350000001 dispute, no restore (D)
- 16000063119 DNS accepted (info)
- 16330088732 AuthInfo removed by action (CH, T)
- 33300102900 DNS not acceptable, status failed (warning)
- 33300102912 predelegation warning
- 46000108827 SEP flag should be set
- 53000060009 contact does not exist
- 53000080011 active DISPUTE (CH)
- 53000080012 status failed (C, T)
- 53300062003 invalid Domain format
- 53300081600 contact Email missing
- 53300100021 technical predelegation problem, retry
- 53300102902 glue missing
- 53300102912 nameserver error
- 53300102920 Nserver count out of range [2..13]
- 53300103022 MX preference missing
- 53380042010 Domain keyword missing
- 53380062206 Domain-ace mismatch
- 56300108812 DNS data not acceptable
- 56310082011 status redemptionPeriod (C)
- 63200020603 contact of another provider
- 63300022003 domain of another provider
- 63300042100 / 63300042102 Domain-ace keyword
- 63300043003 Nsentry count
- 63300043100 Nserver or Nsentry missing
- 63300060005 contact twice in same role
- 63300062009 domain doesn't exist
- 63300062905 duplicate Nserver
- 63300063002 MX pref range
- 63300063003 / 63300063005 / 63300063006 / 63300063011 / 63300083005 Nsentry or NS owner problems
- 63300063016 identical MX prefs
- 63300063102 unknown DNS type
- 63300063103 illegal DNS type
- 63300103005 Null MX combined with other MX
- 63300080013 too many contacts
- 63300080700 contact type wrong for role
- 63300085940 missing phone for holder (CH, CHPROV, RESTORE with AuthInfo2)
- 63300102913 incorrect Nserver
- 63310062004 domain already exists
- 63310062007 inadmissible Domain (incl. DI, DC)
- 63450043902 / 63450063902 Recursive keyword or value
- 66300063003 MX host missing
- 66300048905 invalid DNS data
- 66300063023 AAAA needs A
- 66300068803 / 66300068807 Dnskey format or invalid
- 66310082014 not in RGP (R)
- 53000080009 domain locked
- 63391082031 "Domain has Description" (legacy)
- 63900042502 Holder keyword once

Status info codes: 53000080013, 53000080014, 53000080015.

### 10.3 Contact requests
Source: `D29:Fehlermeldungen bei Contactaufträgen`, `D29:Liste-mit-Meldungscodes`.

- 53000080002 value cannot be deleted
- 63200020603 contact of another provider
- Keyword "must appear once and just once" / "cannot be recognized" errors:
  - Handle: 63200040610
  - Type: 63200040702 / 40710
  - Name: 63200040802 / 40810
  - Address: 63200041010
  - PostalCode: 63200041102 / 41110
  - City: 63200041202 / 41210
  - CountryCode: 63200041302 / 41310
  - Email: 63200041610
  - Phone: 63200042402
- 63200060702 invalid Type
- 63200061302 invalid CountryCode
- 63200061603 invalid Email
- 63200062603 invalid Phone (also reused for "Incomplete verification information"
  **[DOC-INCONSISTENCY]**)
- 63200080900 Organisation with ORG
- 63220080701 Type immutable (legacy)
- 63220080801 Name immutable
- 63400000001–63400000004 completeness check on Name, Address, PostalCode and City
- 83000000005 URI-Template validation (empty, too long, bad scheme, bad variable, bad characters)
- Legacy codes: 63200041802 / 63200061802 "Disclose", 63200061708 "Sip" (RRI 3/4 contact fields
  that no longer exist in 5.0)

### 10.4 Verification
Source: `D29:Liste-mit-Meldungscodes-zur-Verifikation`.

| Code | Meaning |
|---|---|
| 63450064002 | Verification block on a REQUEST contact |
| 63200041860 | Incomplete or missing header |
| 63200041861 | Inadmissible value |
| 63200041862 | More than 5 blocks |
| 63200041863 | Conflicting info for the same claim |
| 63200041864 | Duplicate block |
| 63200041865 | Duplicate value |
| 63200041866 | Duplicate key |
| 63200041867 | Invalid evidence/method combination |

### 10.5 Provider change and AuthInfo
Source: `D29:Fehlermeldungen bei Providerwechsel-Aufträgen`. Operations: C = CHPROV,
CA1 = CREATE-AUTHINFO1, CA2 = CREATE-AUTHINFO2, DA1 = DELETE-AUTHINFO1.

- The DNS, contact and domain errors from §10.2, plus:
- 53370080005 required chprov data missing
- 54300062506 Holder does not match
- 56000088709 AuthInfo2 does not exist
- 63370048700 AuthInfo keyword missing
- 63370088701 AuthInfo does not match
- 63380063209 illegal operation on own domain
- 63391048502 / 63391068503 AuthInfoHash
- 63391048602 / 63391068603 AuthInfoExpire
- 63391068704 AuthInfo1 exists
- 63392068709 AuthInfo1 does not exist
- 63393068704 AuthInfo2 exists
- 63300062009 domain doesn't exist (C, CA1, CA2, DA1)

### 10.6 Queue, RegAcc, LOGIN/LOGOUT
- **Queue:** 63600063502 bad MsgType, 63650063607 not oldest, 63650063609 MsgId does not exist,
  63650043610 MsgId missing.
- **RegAcc:** 63310062008, 63300062010.
- **LOGIN/LOGOUT:** see §6.1.
- **TRANSIT:** 63360043403, 63360063402, 63360082531.
- **Info codes in queue messages:** 11300088725/6, 16350000030/31/32, 16350000040/41/42,
  16350000050/51, 13000000040/41.

---

## 11. pyrri (RRI 4.0 Python client) compared with current RRI 5.0
Source: `https://raw.githubusercontent.com/DENICeG/pyrri/master/rri.py` (© 2019 DENIC, MIT, "Prototype").

| Aspect | pyrri | Current docs (5.0) |
|---|---|---|
| Framing | `struct.pack('!i', len(payload))` (signed 32-bit big-endian) + UTF-8 payload. Reads 4 bytes, unpacks `!i`, then loops `recv` until complete | Same 4-byte network-order length prefix (documented as unsigned / `htonl`); the difference is irrelevant below 2 GB. **Max 64 KB** PDU |
| Sending | `socket.send(size); socket.send(payload)` without a loop, so a partial send is possible (bug) | The examples loop or check the written length. Use `sendall` |
| TLS | `ssl.SSLContext(PROTOCOL_TLS)`, `check_hostname=False`, no verification unless `load_ssl_trustanchor()` is called; optional `check_ssl_cert()` with `match_hostname` (deprecated or removed in modern Python) | TLS 1.2/1.3 required; DENIC recommends validating the chain via the root CA and checking the name per RFC 6125 |
| Socket | IPv4 only (`AF_INET`) | IPv4 allowlisting only; IPv6 not supported for allowlisting **[UNVERIFIED whether the RRI endpoint has IPv6]** |
| Host and port | Default `rri.denic.de:51131` | Same; test is `rri.test.denic.de:51131` |
| LOGIN | `version: 4.0\naction: LOGIN\nuser: …\npassword: …\n` (lowercase keywords, plaintext password) | `Version: 5.0`. Keywords are case-insensitive, so the lowercase form still works syntactically. Version must be `5.0` **[UNVERIFIED whether 4.0 is still accepted; the docs only state 5.0 as valid]** |
| Success detection | Substring `"RESULT: success" in answer` (case-sensitive) | Examples show both `RESULT:` and `Result:`. Parse case-insensitively and use the codes |
| LOGOUT | `version: 4.0\naction: LOGOUT\n` | `Version: 5.0` / `Action: logout` |
| Formats | `talk()` sends any string (K/V or XML) | K/V 5.0 or XML 5.0 namespaces (`http://registry.denic.de/*/5.0`) |
| Features | Transport only: no object model, no queue handling, no keepalive | Session idle timeout 5 min, pre-login timeout 15 s, 7 sessions (4 in test), ACL, IP allowlisting |

Changes from 4.0-era RRI to 5.0 that are visible in the docs (only what the current pages show; no
4.0 spec was consulted):
- Version and namespaces bumped to 5.0.
- NIS2 additions: phone mandatory, verification blocks, `pendingCreate` / `serverHold`, risk
  deadlines, and the `domainStatusUpdate` / `contactVerificationRequired` / `contactDelete` messages.
- INFO output grouped into `[RegAcc]` with registration date.
- Legacy contact fields `Disclose` and `Sip` appear only in old error codes; the `ROLE` type
  survives only in the XSD.

---

## 12. Full message-code list
Source: `D29:Liste-mit-Meldungscodes`.

The page's own sorted list, with additions from other pages marked `*`.

| Code | Text |
|---|---|
| 11300088725 | AuthInfo deleted |
| 11300088726 | AuthInfo letter could not be delivered |
| 13000000011 | Request was processed in test environment – not valid in real world |
| 13000000022 | Used quota |
| 13000000040* | Domain has been locked (lockCreate) |
| 13000000041* | Domain has been unlocked (lockDelete) |
| 13350000001 | Domain bears a DISPUTE entry and can therefore not be restored |
| 16000063119 | DNS data was checked and accepted |
| 16330088732 | An action determines the removal of the AuthInfo |
| 16350000030* | Domain has been updated - please check domain data with RRI-INFO command |
| 16350000031 | Domain has been deleted [request-reference DENIC#:<Ticket-ID>] |
| 16350000032* | Domain in Transit |
| 16350000040* | Verification information must be provided for the holder(s) to avoid dedelegation by |
| 16350000041* | Verification information must be provided for the holder(s) to avoid deletion by |
| 16350000050* | Verification information must be provided for the handle to avoid dedelegation and/or deletion |
| 16350000051* | Please provide the requested verification information by means of a Contact UPDATE |
| 33000000022 | Used quota |
| 33300102900 | The provided DNS data are not acceptable. Domain "Status" is "failed". |
| 33300102912 | Predelegation Check warning |
| 46000108827 | Secure Entry Point flag should be set in DNSKEY |
| 53000000008 | Daily quota exceeded |
| 53000000012 | Concurrent write access to the same business object is prohibited |
| 53000020002 | Unauthorized request |
| 53000020013 | Verification of signature failed |
| 53000020019 | Signature of request is correct but too old |
| 53000060009 | At least one Contact does not exist |
| 53000080002 | This value cannot be deleted |
| 53000080009* | Request rejected - this domain is locked! |
| 53000080011 | The request cannot be carried out because of an active DISPUTE |
| 53000080012 | Domain "Status" is "failed" |
| 53000080013* | Domain "Status" is "connect" |
| 53000080014 | Domain "Status" is "pendingCreate" (listed as WARNING, returned as info) |
| 53000080015* | Domain "Status" is "serverHold" |
| 53300062003 | The value for keyword "Domain" has an invalid format |
| 53300081600 | Within a Contact "Email" is missing |
| 53300100021 | Technical Predelegation Check Problem – please try later |
| 53300102902 | Required glue record is missing |
| 53300102912 | Nameserver error |
| 53300102920 | Occurrences of keyword "Nserver" out of range [min: 2, max: 13] |
| 53300103022 | Missing mail exchange preference of DNS entry |
| 53370080005 | Required change provider request data is missing |
| 53380042010* | Keyword "Domain" cannot be recognized |
| 53380062206 | Mismatch between values for "Domain-ace" and "Domain" |
| 54300062506* | Holder does not match |
| 55000000002* | (ACL exceeded, per the ACL page) |
| 56000000013 | Technical error |
| 56000020021 | Access control limit exceeded |
| 56000088709 | Specified AuthInfo2 does not exist |
| 56300108812 | The provided DNS data are not acceptable |
| 56310082011 | Domain "Status" is "redemptionPeriod" |
| 58000000002 | Text part has not been encoded properly |
| 58000000027 | Mailheader is incomplete |
| 60009500901* | The PGP key does not comply with the requirements |
| 63000000006 | The request has an invalid key/value pair format |
| 63000000007 | Request shows semantics error |
| 63000000012 | Unknown Error |
| 63000040110 | Keyword "Action" cannot be recognized |
| 63000040410 | Keyword "Version" cannot be recognized |
| 63000060003 | An indicated Contact is invalid |
| 63000060008 | The value contains one or more invalid characters |
| 63000060015 | The value is too long |
| 63000060102 | Inadmissible value for keyword "Action" |
| 63000060402 | Inadmissible value for keyword "Version" |
| 63000060504 | "CTID" has been used before |
| 63000060508 | Inadmissible value for keyword "Ctid" |
| 63000080009 | Request type is missing, either keyword "Domain" or "Handle" |
| 63100020005 | Number of failed logins exceeds allowed maximum |
| 63100040202 | Keyword "User" must appear once and just once |
| 63100040302 | Keyword "Password" must appear once and just once |
| 63100064002 | Authorization failure |
| 63200020603 | This Contact is administered by another provider |
| 63200040602 | Keyword "Handle" or "Domain" must appear once and just once |
| 63200040610 … 63200041610 | Contact keyword errors (see §10.3) |
| 63200041802 | Keyword "Disclose" can appear once and just once (legacy) |
| 63200041860–63200041867* | Verification errors (§10.4) |
| 63200042402 | Keyword "Phone" must appear once and just once |
| 63200060702 | Inadmissible value for keyword "Type" |
| 63200061302 | The value for "CountryCode" is not a valid ISO code |
| 63200061603 | The value for keyword "Email" has an invalid format |
| 63200061708 | Invalid character(s) in "Sip" value (legacy) |
| 63200061802 | Inadmissible value for keyword "Disclose" (legacy) |
| 63200062603 | The value for keyword "Phone" has an invalid format |
| 63200080108 | This value of "Action" is not permitted here |
| 63200080900 | Keyword "Organisation" invalid with "Type" "ORG" |
| 63220080701 | The value of "Type" cannot be changed with an UPDATE |
| 63220080801 | The value of "Name" cannot be changed with an UPDATE |
| 63300022003 | This domain is administered by another provider |
| 63300042100 / 63300042102 | Keyword "Domain-ace" cannot be recognized / can appear once and just once |
| 63300043003 | Occurrences of keyword "Nsentry" out of range |
| 63300043100 | Keyword "Nserver" or "Nsentry" cannot be recognized |
| 63300060005 | Contact occurs more than once in same role |
| 63300062009 | Domain doesn't exist |
| 63300062010 | RegAcc doesn't exist |
| 63300062905 | Duplicate value(s) for "Nserver" |
| 63300063002 | Preference values for MX-RR are out of range (0-999) |
| 63300063003 | Incorrect value(s) for "Nsentry" |
| 63300063005 | Duplicate value for "Nsentry" record is present |
| 63300063006 | "Nsentry" has invalid owner |
| 63300063011 | Nserver has invalid owner |
| 63300063016 | At least 2 MX entries have the identical preference |
| 63300063102 | Unknown type of DNS data |
| 63300063103 | Illegal type of DNS data |
| 63300080010 | Required domain data is missing |
| 63300080013 | Too many Contacts are indicated |
| 63300080700 | Contact with wrong value for "Type" |
| 63300083005 | Value for "Nsentry" contains unknown host |
| 63300085940* | Missing phone for holder |
| 63300102913 | Incorrect value(s) for "Nserver" |
| 63300103005 | No other MX resource record is allowed in combination with "Null MX" |
| 63310062004 | Domain already exists |
| 63310062007 | Inadmissible value for keyword "Domain" |
| 63310062008 | Inadmissible value for keyword "RegAcc" |
| 63360043403 | Keyword "Disconnect" can appear once and just once |
| 63360063402 | Inadmissible value for keyword "Disconnect" |
| 63360082531 | For TRANSIT, a Holder Handle is mandatory |
| 63370048700 | Keyword "AuthInfo" cannot be recognized |
| 63370088701 | AuthInfo does not match |
| 63380063209 | Illegal operation on own domain |
| 63391048502 | Keyword "AuthInfoHash" must appear once and just once |
| 63391048602 | Keyword "AuthInfoExpire" can appear once and just once |
| 63391068503 | The value for keyword "AuthInfoHash" has an invalid format |
| 63391068603 | The value for keyword "AuthInfoExpire" has an invalid format |
| 63391068704 | AuthInfo1 already exists |
| 63391082031 | Domain has Description |
| 63392068709 | AuthInfo1 does not exist |
| 63393068704 | AuthInfo2 already exists |
| 63400000001–63400000004* | Completeness check: Name / Address / PostalCode / City invalid format |
| 63450043902 | Keyword "Recursive" can appear once and just once |
| 63450063902 | Inadmissible value for keyword "Recursive" |
| 63450064002* | Value not valid for this contact type [VerificationInformation] |
| 63600063502 | Inadmissible value for keyword "MsgType" |
| 63650043610* | Keyword "MsgId" cannot be recognized |
| 63650063607 | This message is not the oldest |
| 63650063609 | MsgId does not exist |
| 63900042502 | Keyword "Holder" must appear once and just once |
| 66000020020 | Invalid Signature Algorithm |
| 66300048905 | Invalid DNS Data (Nsentry, Dnskey) |
| 66300063003 | Missing mail exchange host |
| 66300063006 | "Nsentry" has invalid owner |
| 66300063023 | AAAA resource record requires corresponding A resource record |
| 66300068803 | The value for keyword "Dnskey" has an invalid format |
| 66300068807 | "Dnskey" invalid |
| 66310082014 | Domain is not in Redemption Grace Period |
| 73100000005 | The maximum number of permitted login is reached |
| 76000000001 | Registry Service temporarily not available |
| 76000000002 | Timeout while processing request |
| 83000000000 | Request message too long |
| 83000000002 | The encoding specified is not supported |
| 83000000004 | Validation of XML request against Schema failed |
| 83000000005 | Validation of URI-Template failed [...] |
| 83000000010 | Login failed |

---

## 13. XSD digest (5.0)
Source: `EX:XMLSchema/Global|Transaction|Domain|Dnsentry|Contact|Message|RegAcc|Verification`.
`monitoring-5.0.xsd` is not published there.

**global-5.0.xsd**
- `registry-request` is `requestType`: a choice of the command (see §3.2) followed by an optional
  `ctid` (`tr:idType`).
- `loginType` is `user` (NMTOKEN) + `password` (string). `logoutType` is the empty string.
- `registry-response` is `responseType`, which contains `tr:transaction`.

**transaction-5.0.xsd**
- `idType`: token of 3–64 characters.
- `resultType`: success | failed | exception.
- `levelType`: info | warning | error.
- `codeType`: unsignedLong.
- `messageType`: `text` (normalizedString) + `argument*` (token), with attributes `level` and `code`
  (both required).
- `dataType`: `any ##other` (1..n).
- `transactionType`: `stid? ctid? result message* data?`.

**domain-5.0.xsd**
- `handleType`: latinToken of 4–66 characters.
- `aceType`: `[0-9a-zA-Z][0-9a-zA-Z\-]{0,62}\.[dD][eE]`.
- `handleGroup`: `handle, ace?`.
- `statusType`: free, connect, failed, invalid, redemptionPeriod, pendingCreate, serverHold.
- `contactType` (in requests): a contact handle with required attribute `role` (holder |
  generalrequest | abusecontact).
- `createType` = `updateType` = `handleGroup, contact{1,7}, dnsentry{1,20}`. `chholder` uses
  `updateType`.
- `chprovType` = `updateType` + `authInfo` (latinToken, 1).
- `deleteType`: `handleGroup, contact{0,5}`.
- `restoreType`, `checkType`, `transitType` (+ optional `@disconnect` boolean), `deleteAuthInfo1Type`
  and `createAuthInfo2Type` are all just `handleGroup`.
- `createAuthInfo1Type`: `handleGroup`, `@hash` (hex), `@expire` (`[0-9]{8}`, optional).
  `createAuthInfo1Data`: `expire?` (dateTime).
- `infoType`: `handleGroup, authInfo?`, `@recursive` (boolean, optional).
- `checkData`: `handle, ace, status`.
- `infoDataType`, in this order:
  - `handle, ace, status`
  - `expire?`
  - `registryLock?`
  - either `authInfo` (boolean) or `authInfo1?` + `authInfo2?` (dateTime)
  - `contact{0,16}` (`contactInfoDataType`: optional `contact:handle` + `contact:coreDataGroup` +
    `verification:verificationInformation{0,5}`, with attribute `role`)
  - `dnsentry{0,20}`
  - `disputeData?`
  - `registrationDate?` (string)
  - `verificationDeadlineBeforeDedelegation?`, `verificationDeadlineBeforeDeletion?`
  - `changed`
  - `regAcc?` (`regAccId` (pattern `DENIC-[1-9][0-9]*`), `name`, `email?`, `phone*`, `changed?`)

**dnsentry-5.0.xsd**
- Abstract `dnsentryBaseType` has `owner` (`hostnameType`: ASCII, pattern
  `([*a-zA-Z0-9\-]+\.)+[*a-zA-Z0-9\-]*|(\.)`, 1–254 characters).
- Concrete types selected by `xsi:type`:
  - `A` and `AAAA`: `rdata/address` (3–39 characters).
  - `NS`: `rdata/nameserver, address*, addressV6*`.
  - `MX`: `rdata/preference` (0–999), `exchange`.
  - `DNSKEY`: `rdata/flags` (unsignedShort), `protocol` (unsignedByte), `algorithm` (unsignedByte),
    `publicKey` (base64Binary).

**contact-5.0.xsd**
- `handleType`: `[dD][eE][nN][iI][cC]\-[1-9][0-9]*\-[\-\.a-zA-Z0-9]+`, maxLength 32.
- `statusType`: free | exist | invalid.
- `roleType`: holder | generalrequest | abusecontact.
- `typeType`: PERSON | ROLE | ORG | REQUEST.
- Field types:
  - name, organisation, address: 1–255 characters.
  - postalCode: `[ a-zA-Z0-9\-]{1,20}`.
  - city: 1–80 characters.
  - countryCode: length 2.
  - email: `\S+@\S+`, 1–255 characters.
  - phone: 7–255 characters.
  - uri-template: normalizedString.
- `create` / `update`: `handle, type, name?, organisation*, postal?, email*, phone?, uri-template?,
  verificationInformation{0,5}`. The XSD is permissive; the business rules from §5.1 add the
  mandatory fields.
- `check` / `info`: `handle`.
- `checkData`: `handle, status`.
- `infoData`: `handle` + `coreDataGroup` (`type, name?, organisation*, postal?, email*, phone?,
  disputeReference?, uri-template?, changed?`) + `verificationInformation{0,5}`.

**message-5.0.xsd**
- `msgTypeType`: the 15 types listed in §9.
- `msg:queue-read`: empty, with optional `@msgType`.
- `msg:delete`: empty, with required `@msgid` (3–64 characters) and optional `@msgType`.
- `msg:message`: `@msgid` (required), `@msgcnt` (optional), `@msgtime` (required), holding exactly
  one of the type elements (shapes in §9).
- `msg:domain` is `handle, ace`. `domainWithExpireType` is `handle, ace, expire`.
  `contactsType` is `handle{1,100}`.
- Type-specific `message` children are `tr:messageType`.

**regacc-5.0.xsd**
- `info`: `handle` (`DENIC-[1-9][0-9]*`).
- `infoData`: `handle, name, postal(address+, postalCode, city, countryCode), phone*, fax*, email,
  url*, memberacc, contact{0,2} (@role; contact:infoDataGroup), changed`.
- phone and fax pattern: `\+[/\-\.\s0-9x]{1,254}`.

**verification-5.0.xsd**
- `verificationInformation` (abstract base `verifiedClaims/claim+`, `verificationResult` success |
  failed).
- `verificationInformationType` (requests): `verificationReference`, `verificationTimestamp`
  (dateTime), `verificationEvidence`, `verificationMethod` and `trustFramework`, all required.
- `domainVerificationInformationType` (INFO output): the same five elements, all optional.
- The value enumerations for claim, evidence and method are enforced by business logic, not by
  the XSD (the XSD uses plain string types).

---

## 14. Open points and items not verified
1. **Login password form.** Read here as plaintext in LOGIN with the MD5 hash stored in the RAI.
   The docs say both "clear text" and "transmitted … as an MD5 hash". The hash tool and pyrri
   support the plaintext reading.
2. Exact K/V syntax for Nsentry MX and AAAA entries, and whether one `Nserver:` line may carry
   several IP addresses.
3. XML form of an empty QUEUE-READ response.
4. When `authInfoExpire` is sent (at creation or at expiry), and who receives `domainTransit` and
   `chprovAuthInfo` beyond the losing RegAcc.
5. Whether TRANSIT really needs a Holder (error 63360082531 exists but is not in the field table).
6. Whether CREATE-AUTHINFO1/2 and CHPROV responses actually return `AuthInfoExpire`.
7. Whether contact type `ROLE` (in the XSD) is still accepted, and whether `Version: 4.0` is still
   accepted.
8. ACL-exceeded code: `55000000002` (ACL page) or `56000020021` (code list).
9. `monitoring-5.0.xsd` is not published on dedocs. It is presumably a health or keepalive request.
   No monitoring request is documented in the request lists.
10. The separate DENIC manuals were not crawled: "Nameserver Predelegation Check", "Operator Change
    for DNSSEC Domains", "Information Services" and "RAI".
