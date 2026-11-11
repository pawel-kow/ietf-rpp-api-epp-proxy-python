from core.model.shared.common import ProvisioningObject
from rpp.dto.rpp_prov_metadata import RPPProvMetadata


def model_to_rpp(obj: ProvisioningObject) -> RPPProvMetadata:
    return RPPProvMetadata(
        repositoryId=obj.roid,
        spClientId=obj.clID,
        crClientId=obj.crID,
        crDate=obj.crDate,
        upClientId=obj.upID,
        upDate=obj.upDate,
        trDate=obj.trDate,
    )
