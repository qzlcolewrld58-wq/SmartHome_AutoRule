from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Device(BaseModel):
    """Single device definition loaded from the device knowledge base."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    entity_id: str = Field(
        ...,
        min_length=3,
        pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$",
        description="Home Assistant entity id",
    )
    type: Literal[
        "light",
        "climate",
        "switch",
        "sensor",
        "cover",
        "fan",
        "media_player",
        "lock",
        "vacuum",
        "humidifier",
        "dehumidifier",
        "camera",
        "siren",
        "scene",
        "script",
    ] = Field(
        ...,
        description="Device domain or type",
    )
    room: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Room where the device is located",
    )
    supported_services: list[str] = Field(
        default_factory=list,
        description="Services supported by the device",
    )


class DeviceRegistry(BaseModel):
    """Device knowledge base wrapper with common query methods."""

    model_config = ConfigDict(extra="forbid")

    devices: list[Device] = Field(default_factory=list)

    @classmethod
    def from_json(cls, file_path: str | Path) -> "DeviceRegistry":
        path = Path(file_path)
        raw_data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, list):
            raise ValueError("devices.json must contain a JSON array.")
        devices = [Device.model_validate(item) for item in raw_data]
        return cls(devices=devices)

    def entity_exists(self, entity_id: str) -> bool:
        return any(device.entity_id == entity_id for device in self.devices)

    def get_supported_services(self, entity_id: str) -> list[str]:
        device = self.get_device(entity_id)
        if device is None:
            return []
        return device.supported_services

    def get_all_entity_ids(self) -> list[str]:
        return [device.entity_id for device in self.devices]

    def get_device(self, entity_id: str) -> Device | None:
        for device in self.devices:
            if device.entity_id == entity_id:
                return device
        return None


def load_default_registry(base_dir: str | Path | None = None) -> DeviceRegistry:
    """Load devices from data/devices.json under the project root."""

    if base_dir is None:
        base_path = Path(__file__).resolve().parents[1]
    else:
        base_path = Path(base_dir)
    return DeviceRegistry.from_json(base_path / "data" / "devices.json")


if __name__ == "__main__":
    registry = load_default_registry()
    query_entity = "light.living_room"

    print("entity exists:", registry.entity_exists(query_entity))
    print("supported services:", registry.get_supported_services(query_entity))
    print("all entity ids:", registry.get_all_entity_ids())
