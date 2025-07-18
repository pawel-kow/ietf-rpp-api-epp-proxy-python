from models import *
from .rpp_models import *
from rpp_schema_validator import validate_schema


def provisioning_object_to_rpp(obj: ProvisioningObject, target_dict: dict) -> str:
    """Converts a Contact object to a JSON string according to the provided schema."""

    if obj.status:
        target_dict["status"] = [x for x in obj.status]
    if obj.crDate:
        target_dict["crDate"] = obj.crDate
    if obj.exDate:
        target_dict["exDate"] = obj.exDate
    if obj.upDate:
        target_dict["upDate"] = obj.upDate
    if obj.trDate:
        target_dict["trDate"] = obj.trDate
    if obj.clID:
        target_dict["clID"] = obj.clID
    if obj.crID:
        target_dict["crID"] = obj.crID
    if obj.authInfo:
        target_dict["authInfo"] = {}
        if obj.authInfo.pw:
            target_dict["authInfo"]["pw"] = obj.authInfo.pw
        if obj.authInfo.hash:
            target_dict["authInfo"]["hash"] = obj.authInfo.hash

