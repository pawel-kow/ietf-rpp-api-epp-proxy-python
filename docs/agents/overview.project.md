# Project overview

An RPP (Registration Protocol Proxy) server that exposes a REST/JSON API (the IETF
RPP draft) and translates each request into classic EPP (RFC 5730/5731 etc.)
commands sent over TCP to a backend EPP registry server. It is a stateless-by-default
protocol bridge: RPP JSON in → EPP XML out → EPP XML back → RPP JSON out.

A deployment can speak DENIC RRI 5.0 (XML over TCP) to the registry instead of EPP (`rpp_backend: rri`). The RPP
API is the same; what RRI lacks answers 501. The design and the RRI facts are in [docs/rri/](../rri/).

The stack is Connexion 3 (ASGI) on Flask and Starlette middleware, served by
uvicorn.

Protocol notes and open design questions are in
[RPP_IMPLEMENTATION_NOTES.md](../../RPP_IMPLEMENTATION_NOTES.md).
