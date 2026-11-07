# Contact availability (#30)

`GET`/`HEAD /contacts/{id}/availability` answer 501. No EPP contact check exists. Mirror host availability (`hosts_availability*`, `epp_hosts_Check`).

## Tasks

- [x] Plan approved by orchestrator
- [x] Tests first (unit): `contact_check_xml`, `parse_contact_check_response`, `contact_availability.model_to_rpp`
- [x] Integration cases `tests/integration/test_case_data/contact_availability/` (free, taken, HEAD free, HEAD taken, unknown user, repeated clTRID), unskip `draft_contact/test1-availability.json`
- [x] `models/contact_check_response.py` (`ContactCheckResponse`, own file)
- [x] `commands/contacts.py::contact_check`, `contacts.py::contact_check_xml` / `parse_contact_check_response`
- [x] `eppclient/epp_contacts.py::epp_contacts_Check`
- [x] `rpp_models/rpp_contact_availability.py`, `rpp_to_model_mapper/contact_availability.py`
- [x] `controller/contacts.py::contacts_availability` and `contacts_availabilityHead` (as hosts: 200 available, 404 not, HEAD without Content-Type)
- [x] Docs: architecture.project.md / testing.project.md mentions if needed
- [~] Full `pytest` on the reported commit

## Findings

- `contactAvailability.read` (json §6.2.15.3, §8.2.1) exists in the schema; openapi has both operations (`contacts_availability`, `contacts_availabilityHead`).
- contact-1.0 `ChkData.cd[].id` has `avail` and `value`, `reason` optional; generated model exists.
- Contact create uppercases the id in EPP; Info/Delete pass the id as given; Check does the same.

## Decisions

- `draft_contact/test1-availability.json`: unskipped, create step with an `FO-` id then check it, draft response shape kept (orchestrator).
- Probe: lowercase id on a created contact is taken (404), so the backend matches ids case-insensitively. Ids of 2 and 31 chars answer available (200) on the backend, though EPP checkIDType is 3 to 16: backend defect, reported not filed.

## Open questions
