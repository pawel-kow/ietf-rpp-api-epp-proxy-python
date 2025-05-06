## Special handling behavior

- server changing caps of the domain name/host name -> make comparisons case-insensitive
- server changing order of entries in lists (contacts, IPs) -> list shall be treated unordered
- servers actually enforce unique clTRID
- test EPP server is hanging if clTRID is duplicated (TODO: implement timeout?)

## RPP design notes
- client/server transaction ids with incomplete/invalid requests? yes/no?
- take a look into Retry-After header (to indicate temp errors)
- BODY missing on GET/DELETE"
    - https://github.com/swagger-api/swagger-ui/issues/2136#issuecomment-1055839700
    - https://github.com/spec-first/connexion/issues/1689

### Status codes
[x] domain not free (EPP 2302): 409
[x] domain not existing (EPP 2303): 404
[x] all other client-side errors: 400
[x] all server side errors: 500