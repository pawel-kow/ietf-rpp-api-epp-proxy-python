# Specification writing: project specifics

Generic rules are in [specification.md](specification.md).

## Source of the rules

The generic rules and the RPP notation below are imported from the agent guide of the data objects draft,
<https://github.com/ietf-wg-rpp/draft-ietf-rpp-data-objects/blob/main/Agents.md>, at commit `2438b83`. Rules of that
repository about its own files are not imported: the single source file, its build, the document index script, the
IANA consistency script and the pre-release review. When the upstream guide changes, compare it with this file and
[specification.md](specification.md) and update both.

## The drafts

The RPP drafts define the shapes every specification here follows:

| Draft | Upstream source | Local copy | Defines the shape of |
|---|---|---|---|
| draft-ietf-rpp-data-objects | <https://github.com/ietf-wg-rpp/draft-ietf-rpp-data-objects/blob/main/src/draft-ietf-rpp-data-objects.md> | [.spec/draft-ietf-rpp-data-objects.clean.txt](../../.spec/draft-ietf-rpp-data-objects.clean.txt) | Data, Component and Process Objects: Object Description, Data Elements, Operations, Processes, status values, IANA registry tables |
| draft-ietf-rpp-json | <https://github.com/ietf-wg-rpp/draft-ietf-rpp-json/blob/main/src/draft-ietf-rpp-json.md> | [.spec/draft-ietf-rpp-json.clean.txt](../../.spec/draft-ietf-rpp-json.clean.txt) | JSON representation rules, JSON Schema definitions per object and operation, examples per object and operation |
| draft-ietf-rpp-core | <https://github.com/ietf-wg-rpp/draft-ietf-rpp-core/blob/main/src/draft-ietf-rpp-core.md> | [.spec/draft-ietf-rpp-core.clean.txt](../../.spec/draft-ietf-rpp-core.clean.txt) | HTTP: header fields, media types, signalling, endpoints and their mapping rules, problem details, result codes |

The extension guidelines, [.spec/draft-wullink-rpp-extension-guidelines.clean.txt](../../.spec/draft-wullink-rpp-extension-guidelines.clean.txt),
define the section list of an extension specification (§9).

Read the section of the draft whose shape you follow before writing, and copy its layout: heading levels, the order of
subsections, attribute bullets, table captions and the form of examples. Where the local copy and the upstream source
differ, ask which revision applies.

## Kinds of specification

**Extension specification.** An RPP extension the proxy implements is specified in a Markdown file under `docs/`
(`de.denic.rpp.rri`: [rri-extension.md](../rri/rri-extension.md), `org.example.rpp.extension.planets`:
[planets-extension.md](../demo/planets-extension.md)), and the generic extensions of the tree `io.github.pawel-kow.rpp.<name>` in
`docs/extensions/<name>-extension.md` (`io.github.pawel-kow.rpp.messages`: [messages-extension.md](../extensions/messages-extension.md)). It has the section list of guidelines §9, in that
order, with "None" in a section that does not apply. Each section takes the shape of the draft that defines the base
concept: object sections that of data-objects, the JSON Schema and Examples sections that of json, and Result Codes,
Problem Details, HTTP Headers and Endpoints that of core. How the extension is implemented is in
[architecture.project.md](architecture.project.md#rpp-extensions).

**Proposal for a change to a draft.** A concept the proxy implements experimentally ahead of the drafts is written as a
proposal per affected draft: the draft, its revision, and for each change the section (title and anchor), whether
text is added, replaced or removed, and the exact text in that draft's shape and notation, including its IANA
Considerations and Changes History entries. Each proposal is a file per draft under `.spec/proposals/<issue>-<topic>/`
(`data-objects.md`, `core.md`, `json.md`, `extension-guidelines.md`). A proposal for a new draft is a file named
after its topic, with the whole draft text in the shape of the profile, extension or base draft it is. Both are written on the branch of the issue for the
experimental implementation (see [requirements.md](requirements.md)) and linked from that issue. A problem with the drafts that is not a proposal goes to
[.spec/spec-issues.md](../../.spec/spec-issues.md).

## Authoring syntax

Specifications are Markdown for [mmark](https://mmark.miek.nl/):

- A TOML title block between `%%%` fences (`title`, `abbrev`, `area`, `workgroup`, `keyword`, `[seriesInfo]`,
  `[[author]]`), then `.# Abstract` (note the dot), `{mainmatter}` and `{backmatter}`.
- Anchors `{#anchor}` on a heading or block, referenced as `(#anchor)` or `[](#anchor)`.
- Citations `[@!RFCxxxx]` and `[@!I-D.name]` for normative references, `[@RFCxxxx]` for informative ones, and a
  section as `[@!I-D.ietf-rpp-data-objects, section 12]`. Other references are defined in the back matter with
  `<reference>` XML.
- `A>` for an editorial aside, fenced `ascii` blocks for diagrams of object structures.
- Section attributes `{removeInRFC="true"}`, `{toc="exclude"}` and `{numbered="false"}`.

## Spelling

British English in prose ("behaviour", "authorisation", "organisation"). Identifiers, status values, URNs, anything
in backticks or code blocks, and titles of external documents ("Internationalized Domain Names") keep their spelling.

## RPP data model notation

Terms of the data model (Data Object, Component Object, Process Object, data element, cardinality, mutability, and the
others) are used as data-objects defines them and are not redefined. Load its Conventions and Terminology and its
Common Data Types when writing definitions.

**Data element.** Every data element has all of these attributes:

```
* Element Name
  * Identifier: elementId
  * Cardinality: 1
  * Mutability: read-write
  * Data Type: String
  * Description: Description of the element.
  * Constraints: Any specific constraints.
```

- Identifier: camelCase.
- Cardinality: `1`, `0-1`, `0+` or `1+`.
- Mutability: `create-only`, `read-only` or `read-write`.
- Data Type: a primitive type (`String`, `Integer`, `Boolean`, `Decimal`, `Date`, `Timestamp`, `URL`, `Binary`,
  `Dictionary`, `Object`), a Common Data Type (`Identifier`, `Client Identifier`, `Phone Number`), or an object
  through an association.
- Other attributes only as data-objects defines them (Data Element Semantics), such as Direct Access and Visibility.

**Object.** Name, Identifier (camelCase), Description, the complete list of Data Elements, and for a resource object
its Operations. Each operation has an `* Identifier:` and its input under `* Input:`, with `* Input Data Elements:`
and `* Parameters:` laid out like Data Elements (data-objects, Operation Input and Output).

**Associations.** `Aggregation[Type]` for independent objects, `Type` for composition, `LabelledAggregation[Type]`,
`DictionaryAggregation[Type]`, `LabelledComposition[Type]` and `DictionaryComposition[Type]`. Refer to an object by
name in brackets, `[Object Name]`, and only to an object that is defined.

**EPP Compatibility Profile.** A constraint for EPP compatibility starts with "In EPP Compatibility Profile" and cites
the EPP RFC it comes from (RFC 5730 to 5734, RFC 3915).

**Structured, not prose.** Put a fact a consumer needs (which table a value comes from, which process an operation
starts) in an attribute bullet or a captioned table, in the same form the drafts use, never only in prose.

**Consistency.** After a structural change, the definitions, the IANA registry tables, the JSON Schema and the examples
agree as [specification.md](specification.md#consistency-checks) describes.

## Checked examples

In an extension specification, an example marked `<!-- example valid <definition> -->` or
`<!-- example invalid <definition> -->` is validated against the extension's schema, and a definition shown after
`<!-- definition <name> -->` must equal the schema's. `tests/unit/test_extension_docs.py` checks this for
[rri-extension.md](../rri/rri-extension.md) and the three documents of [docs/extensions/](../extensions/) (it also checks that the
schema copy in `src/extensions/<name>/rpp/schema/` is the one of `.spec/`). Run it after editing one of them.

## Changes History

An extension specification keeps its history in a `# Changes History` section before `{backmatter}`, marked
`{removeInRFC="true"}` and `{toc="exclude"}`, with one `{numbered="false"}` subsection per version
(`## 0.1.0 - 0.2.0`). The entries follow [specification.md](specification.md#changes-history).
