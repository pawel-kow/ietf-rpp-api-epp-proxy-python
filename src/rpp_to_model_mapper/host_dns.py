from .dns_records import ADDRESS_RECORDS, ORIGIN, check_record_class, record_address, record_rdata, record_type
from .rpp_models import RPPDnsRecord
from .unsupported_rpp_feature import UnsupportedRppFeature


def _is_host(host_name: str, name: str) -> bool:
    return name.removesuffix(".").lower() == host_name.lower()


def rpp_to_model(host_name: str, record: RPPDnsRecord) -> tuple[str, str] | None:
    """The address family and address of a record. EPP holds only the glue of the host itself.

    The self-referencing `ns` record carries nothing EPP has to hold, so it gives None.
    """
    check_record_class(record)
    if record.name != ORIGIN and not _is_host(host_name, record.name):
        raise UnsupportedRppFeature(f"A DNS record for '{record.name}' is not supported")
    kind = record_type(record)
    if kind == "ns":
        if not _is_host(host_name, record_rdata(record, "nsdname")[0]):
            raise UnsupportedRppFeature("An 'ns' record for another host is not supported")
        return None
    if kind not in ADDRESS_RECORDS:
        raise UnsupportedRppFeature(f"DNS record type '{record.type}' is not supported")
    return record_address(record)
