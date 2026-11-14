# The `rri` extension

An RPP extension (json §7) for a proxy whose registry speaks DENIC RRI 5.0. It carries what RRI needs and the RPP
drafts have no place for. The schema is [rri-extension.schema.json](rri-extension.schema.json); the RRI facts behind
it are in [docs/rri/](../docs/rri/).

| Extension object (json §6.2.12) | |
|---|---|
| `name` | `DENIC RRI` |
| `id` | `rri` |
| `version` | `0.1.0` |
| `url` | the `$id` of the schema |

A server that offers it lists it in the `extensions` of its discovery document (core §12.3). The proxy offers it
when `rpp_backend` is `rri` (the `extensions` of the backend profile).

## Schema

The schema follows json §7: `rpp:extends` maps each base definition to the extension's definition, which is composed
with it by `allOf` into the effective schema (json §7.2). Two points where it departs from the draft's example:

- `rpp:extends` and the `$ref`s name the base definitions by their local names (`#/$defs/contact.reference`), because
  the bundle of the drafts has no `$id` to refer to. The proxy adds the extension's definitions, prefixed `ext.rri.`,
  to the bundle.
- `rpp:extension` holds the members of the Extension Object besides `url`, which is the schema's `$id`. Json §7 does
  not say where an extension states its name and version.

## Domain transfer (CHPROV)

RRI has one transfer, CHPROV (docs/rri/rri-5.0-reference.md §6.18). It is requested by the gaining registrar with the
domain's AuthInfo (AuthInfo1 or AuthInfo2), and it moves the domain at once. It states the complete domain data:
1–5 holders and the General Request and Abuse contacts, all of them **the gainer's own** contacts, and all DNS data.
RPP's transfer request has none of it (gap Q3, option B).

The extension adds to `domainTransferProcess.create`:

| Member | As in `domainName.create` | Required |
|---|---|---|
| `registrant` | the first holder | yes |
| `contacts` | further holders (`registrant`), `generalRequest`, `abuse` | no |
| `dns` | `ns` records with glue, `a`, `aaaa`, `mx`, `dnskey` | yes |

They are converted as those of a domain create, with the same refusals: no `nameservers` (RRI has no host objects),
no `ds` records, no other contact labels. The AuthInfo travels in `RPP-Authorization` (core §6.1), as for any
transfer.

```
POST /domainNames/example.de/processes/transferProcesses
RPP-Authorization: authinfo value=QWJjMjM0NTY3OA==

{
  "@type": "domainTransferProcess",
  "registrant": {"@type": "contact", "id": "DENIC-1000002-HOLDER"},
  "contacts": [
    {"label": "generalRequest", "object": {"@type": "contact", "id": "DENIC-1000002-GENERAL"}},
    {"label": "abuse", "object": {"@type": "contact", "id": "DENIC-1000002-ABUSE"}}
  ],
  "dns": {"@type": "dnsData", "records": [
    {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": "ns1.example.com."}},
    {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": "ns2.example.com."}}
  ]}
}
```

### Response

CHPROV is immediate, so the answer is the "completed at once" one of core §16.1.4: **200** without `Location`. The
RRI reply has no transfer state, so the process is stated as the registry completed it:

| Member | Value |
|---|---|
| `transferDir` | `pull` |
| `trStatus` | `serverApproved` |
| `reqClientId`, `actClientId` | the gainer's RegAccId |
| `requestDate`, `actionDate` | the time of the reply |
| `expiryDate` | absent: an RRI domain has no expiry |

The losing registrar learns of it from a `chprovAuthInfo` queue message, which the proxy shows as a service notice.

### Refusals

| Case | Answer |
|---|---|
| `registrant` or `dns` missing | 400 (`02001`), no command sent |
| no `RPP-Authorization` | 400 (`02003`), no command sent |
| the AuthInfo does not match (`63370088701`), or no AuthInfo2 exists (`56000088709`) | 401 (`02202`) |
| a contact of another registrar (`63200020603`) | 403 (`02201`) |
| the gainer already sponsors the domain (`63380063209`) | 409 (`02002`) |
| required CHPROV data missing (`53370080005`) | 400 (`02003`) |

### Not covered

- Query, cancel, approve and reject: RRI has none, so they answer 501 (`02101`). A push transfer is 501 (`02102`),
  TRANSIT is not mapped (gap Q8).
- A transfer of a domain in its redemption period with an AuthInfo2, which RRI allows, works as any other but is not
  tested: RPP has no way to request an AuthInfo2 (gap Q9).
- The operator change of a DNSSEC domain (DENIC's separate document) is not described here.
