%%%
title = "DENIC RRI Strict Preset for the RESTful Provisioning Protocol (RPP)"
abbrev = "RPP DENIC RRI Strict Preset"
area = "Applications and Real-Time"
workgroup = "Network Working Group"
submissiontype = "IETF"
keyword = ["RPP", "provisioning", "registry", "preset", "RRI"]
TocDepth = 4
date = 2026-11-27

[seriesInfo]
name = "Internet-Draft"
value = "draft-kowalik-rpp-denic-rri-strict-preset-00"
stream = "IETF"
status = "informational"

[[author]]
initials="P."
surname="Kowalik"
fullname="Pawel Kowalik"
organization = "DENIC"

%%%

.# Abstract

This document defines a private preset of the RESTful Provisioning Protocol (RPP) for a server whose registry operates the DENIC Registry Robot Interface (RRI) version 5.0: the DENIC RRI preset, constrained by the DENIC RRI profile.

{mainmatter}

# Introduction {#introduction}

This section states the purpose of the preset and the clients and servers it is intended for.

The preset is for clients that provision domain names in a registry that operates the DENIC Registry Robot Interface (RRI) version 5.0 and want every request that the registry cannot hold refused as a broken profile constraint. It applies the profile [DENIC RRI](rri-profile.md) to the DENIC RRI preset, which contains the DENIC RRI extension ([rri-extension](rri-extension.md)) and the extensions it builds on. The DENIC RRI preset stays available without the profile.

The preset follows the Preset Specification Format of [@!I-D.wullink-rpp-extension-guidelines].

## Conventions and Terminology {#terminology}

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [@!RFC2119] [@!RFC8174] when, and only when, they appear in all capitals, as shown here.

The terms Profile, Preset, Applicable Profiles, and Profile Binding are used as defined in [@!I-D.ietf-rpp-data-objects]. The terms Profile Schema, Constraints Mapper (`rpp:constraints`), Preset Schema, and Effective Schema are used as defined in [@!I-D.ietf-rpp-json]. The DENIC RRI extension is `de.denic.rpp.rri`.

# Preset Overview {#overview}

| Field | Value |
| ----- | ----- |
| Name | DENIC RRI strict preset |
| Identifier | `de.denic.rpp.preset.rri-strict` |
| Version | 1.0 |
| RPP version | 1.0 |
| Extensions | None |
| Profiles | `de.denic.rpp.profile.rri` 1.0 |
| Base presets | `de.denic.rpp.preset.rri` 1.0 |
| Specification | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/docs/rri/rri-strict-preset.md> |
Table: Preset Overview

The preset has no extension of its own. It contains the extensions of its base preset, of which the profile requires the DENIC RRI extension.

A client signals the preset with each request, as defined in [@!I-D.ietf-rpp-core]:

```http-message
RPP-Preset: preset=de.denic.rpp.preset.rri-strict;version=1.0
```

# IANA Considerations {#iana}

This document has no IANA actions. The preset is a private preset, and its identifier is formed by reverse domain name notation under the domain `denic.de` [@!I-D.wullink-rpp-extension-guidelines]. It is not registered in the RPP Presets registry.

# Security Considerations {#security}

The preset adds no functionality and no constraints of its own. The security considerations of its extensions and its profile apply.

{removeInRFC="true"}
{toc="exclude"}
# Changes History

{toc="exclude"}
{numbered="false"}
## 1.0

* initial version #183
* contain the extensions of the preset de.denic.rpp.preset.rri, which builds on the extensions io.github.pawel-kow.rpp.messages, io.github.pawel-kow.rpp.domain-lock and io.github.pawel-kow.rpp.registry-changes #261
* contain the extension io.github.pawel-kow.rpp.authinfo through the preset de.denic.rpp.preset.rri #262
