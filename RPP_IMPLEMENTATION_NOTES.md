## Special handling behavior

- server changing caps of the domain name/host name -> make comparisons case-insensitive
- server changing order of entries in lists (contacts, IPs) -> list shall be treated unordered
- servers actually enforce unique clTRID
- test EPP server is hanging if clTRID is duplicated (TODO: implement timeout?)

## RPP design notes
- client/server transaction ids with incomplete/invalid requests? yes/no?

### Status codes
[x] domain not free (EPP 2302): 409
[x] domain not existing (EPP 2303): 404
[x] all other client-side errors: 400
[x] all server side errors: 500