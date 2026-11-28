%%%
title = "DENIC RRI Preset for the RESTful Provisioning Protocol (RPP)"
abbrev = "RPP DENIC RRI Preset"
area = "Applications and Real-Time"
workgroup = "Network Working Group"
submissiontype = "IETF"
keyword = ["RPP", "provisioning", "registry", "preset", "RRI"]
TocDepth = 4
date = 2026-11-27

[seriesInfo]
name = "Internet-Draft"
value = "draft-kowalik-rpp-denic-rri-preset-00"
stream = "IETF"
status = "informational"

[[author]]
initials="P."
surname="Kowalik"
fullname="Pawel Kowalik"
organization = "DENIC"

%%%

.# Abstract

This document defines a private preset of the RESTful Provisioning Protocol (RPP) for a server whose registry operates the DENIC Registry Robot Interface (RRI) version 5.0: the base preset with the DENIC RRI extension and the generic extensions for the messages of the registry, and no profile.

{mainmatter}

# Introduction {#introduction}

This section states the purpose of the preset and the clients and servers it is intended for.

The preset is for clients that provision domain names in a registry that operates the DENIC Registry Robot Interface (RRI) version 5.0, and for servers that offer such a registry. It is the preset of the DENIC RRI extension ([rri-extension](rri-extension.md)), the message components extension ([messages](../extensions/messages-extension.md)), the domain lock messages extension ([domain-lock](../extensions/domain-lock-extension.md)), and the registry change messages extension ([registry-changes](../extensions/registry-changes-extension.md)) on top of the base preset. The DENIC RRI extension and the two extensions of messages refer to the Component Objects of the message components extension. The preset [DENIC RRI strict](rri-strict-preset.md) applies the profile [DENIC RRI](rri-profile.md) to it.

The preset follows the Preset Specification Format of [@!I-D.wullink-rpp-extension-guidelines].

## Conventions and Terminology {#terminology}

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [@!RFC2119] [@!RFC8174] when, and only when, they appear in all capitals, as shown here.

The terms Profile, Preset, Applicable Profiles, and Profile Binding are used as defined in [@!I-D.ietf-rpp-data-objects]. The DENIC RRI extension is `de.denic.rpp.rri`. The message components, domain lock messages, and registry change messages extensions are `io.github.pawel-kow.rpp.messages`, `io.github.pawel-kow.rpp.domain-lock`, and `io.github.pawel-kow.rpp.registry-changes`.

# Preset Overview {#overview}

| Field | Value |
| ----- | ----- |
| Name | DENIC RRI preset |
| Identifier | `de.denic.rpp.preset.rri` |
| Version | 1.0 |
| RPP version | 1.0 |
| Extensions | `de.denic.rpp.rri` 0.4.0, `io.github.pawel-kow.rpp.messages` 0.1.0, `io.github.pawel-kow.rpp.domain-lock` 0.1.0, `io.github.pawel-kow.rpp.registry-changes` 0.1.0 |
| Profiles | None |
| Base presets | `urn:ietf:params:rpp:preset:base` 1.0 |
| Specification | <https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/docs/rri/rri-preset.md> |
Table: Preset Overview

A client signals the preset with each request, as defined in [@!I-D.ietf-rpp-core]:

```http-message
RPP-Preset: preset=de.denic.rpp.preset.rri;version=1.0
```

# IANA Considerations {#iana}

This document has no IANA actions. The preset is a private preset, and its identifier is formed by reverse domain name notation under the domain `denic.de` [@!I-D.wullink-rpp-extension-guidelines]. It is not registered in the RPP Presets registry.

# Security Considerations {#security}

The preset adds no functionality and no constraints of its own. The security considerations of its extensions apply.

{removeInRFC="true"}
{toc="exclude"}
# Changes History

{toc="exclude"}
{numbered="false"}
## 1.0

* initial version #183
* require the extension de.denic.rpp.rri 0.3.0 #248
* require the extension de.denic.rpp.rri 0.4.0 and the extensions io.github.pawel-kow.rpp.messages, io.github.pawel-kow.rpp.domain-lock and io.github.pawel-kow.rpp.registry-changes 0.1.0 #261
