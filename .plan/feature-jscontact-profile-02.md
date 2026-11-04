# JSContact profile -02

Align the proxy, the schemas and the tests to draft-wullink-rpp-jscontact-profile-02.

## Decisions (accepted by the maintainer)

- One localization maps to EPP `postalInfo type="loc"`. `language` and the tag are accepted but EPP cannot store them, reads use `und` and return only members that differ from the internationalized form. A partial localization inherits from the internationalized form. Localized email and a second localization: 501 (`02102`).
- Schema edits go to `.spec/auto/`, then `copy_models.sh`. TypeSpec follow-up is an issue.
- Phone key and features that disagree: 400.
- The US-ASCII check runs in the mapper, on requests only.
- `tel:+CC.number;ext=N` only. Older forms are 400.
- Additional emails and phones, links, more than 3 street lines: 501 (`02102`).

## Findings

- Backend: keeps `int` and `loc`, accepts `loc` alone, rejects non-ASCII with 2005, echoing it as Latin-1 in a UTF-8 document, which breaks `TCPClient`.

## Tasks

- [x] Tests first (unit, integration data)
- [x] Schemas in `.spec/auto/`, copied to `src/`
- [x] Mapper, RPP models, phones
- [x] Model and EPP mapping of `loc`
- [x] TCPClient decode
- [x] Docs, spec-issues
- [x] Issues #55 and #56
- [~] Full pytest, draft PR, maintainer acceptance
