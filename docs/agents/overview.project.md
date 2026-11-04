# Project overview

An RPP (Registration Protocol Proxy) server that exposes a REST/JSON API (the IETF
RPP draft) and translates each request into classic EPP (RFC 5730/5731 etc.)
commands sent over TCP to a backend EPP registry server. It is a stateless-by-default
protocol bridge: RPP JSON in → EPP XML out → EPP XML back → RPP JSON out.

The stack is Connexion 3 (ASGI) on Flask and Starlette middleware, served by
uvicorn.

Protocol notes and open design questions are in
[RPP_IMPLEMENTATION_NOTES.md](../../RPP_IMPLEMENTATION_NOTES.md).
