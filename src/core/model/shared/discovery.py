from dataclasses import dataclass


@dataclass(kw_only=True)
class Discovery:
    version: str
    base_url: str
    tlds: list[str]
    environment_name: str
    environment_status: str
    objects: list[str]
    profiles: list[str]
    datetime: str
