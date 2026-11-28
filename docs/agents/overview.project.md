# Project overview

An RPP (Registration Protocol Proxy) server that exposes a REST/JSON API (the IETF
RPP draft) and translates each request into classic EPP (RFC 5730/5731 etc.)
commands sent over TCP to a backend EPP registry server. It is a stateless-by-default
protocol bridge: RPP JSON in → EPP XML out → EPP XML back → RPP JSON out.

A deployment can speak DENIC RRI 5.0 (XML over TCP) to the registry instead of EPP (`rpp_backend: rri`). The RPP
API is the same, with the `de.denic.rpp.rri` extension ([rri-extension.md](../rri/rri-extension.md), `src/extensions/rri/`, which `config/backends/rri.yaml` registers) for what RRI
holds and RPP has no place for; what RRI lacks answers 501. The design and the RRI facts are in [docs/rri/](../rri/).

A third backend, `rpp_backend: sqlite`, is a test bed for protocol features: bare RPP over a SQLite database, with no
registry behind it and none of the drafts' data objects. Its objects are the planets and satellites of a demo extension
(`org.example.rpp.extension.planets`, [docs/demo/planets-extension.md](../demo/planets-extension.md)), which a
deployment registers by its configuration (`rpp_extensions`); see
[architecture.project.md](architecture.project.md#registered-extensions).

The stack is Connexion 3 (ASGI) on Flask and Starlette middleware, served by
uvicorn.

Protocol notes and open design questions are in
[RPP_IMPLEMENTATION_NOTES.md](../../RPP_IMPLEMENTATION_NOTES.md).
