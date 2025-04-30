## Special handling behavior

- server changing caps of the domain name/host name -> make comparisons case-insensitive
- server changing order of entries in lists (contacts, IPs) -> list shall be treated unordered
- servers actually enforce unique clTRID

## RPP design notes

### Status codes
[x] domain not free (EPP 2302): 409
[x] domain not existing (EPP 2303): 404
