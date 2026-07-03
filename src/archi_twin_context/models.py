from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AlertValue = float | int | str | None


class StrictModel(BaseModel):
    """Base model with strict unknown-field handling"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DigitalTwinAlert(StrictModel):
    alert_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    alert_type: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    value: AlertValue = None
    unit: str | None = None
    timestamp: str = Field(min_length=1)
    message: str | None = None

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        return value.lower()

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp must be ISO-8601 compatible") from exc
        return value

    @field_validator("unit", "message", mode="before")
    @classmethod
    def empty_optional_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class AssetMapping(StrictModel):
    asset_id: str = Field(min_length=1)
    ea_element_id: str = Field(min_length=1)
    default_bpmn_process: str | None = None
    owner: str | None = None

    @field_validator("default_bpmn_process", "owner", mode="before")
    @classmethod
    def empty_optional_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class EAElement(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    layer: str = Field(min_length=1)
    description: str | None = None
    criticality: str = Field(min_length=1)
    owner: str | None = None
    related_elements: list[str] = Field(default_factory=list)
    supported_capabilities: list[str] = Field(default_factory=list)
    supported_processes: list[str] = Field(default_factory=list)
    supported_applications: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("criticality")
    @classmethod
    def normalize_criticality(cls, value: str) -> str:
        return value.lower()

    @field_validator("description", "owner", mode="before")
    @classmethod
    def empty_optional_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "related_elements",
        "supported_capabilities",
        "supported_processes",
        "supported_applications",
        "tags",
    )
    @classmethod
    def validate_string_list(cls, values: list[str]) -> list[str]:
        cleaned_values: list[str] = []
        for item in values:
            cleaned_item = item.strip()
            if not cleaned_item:
                raise ValueError("list items must not be empty")
            cleaned_values.append(cleaned_item)
        return cleaned_values


class ArchitectureModel(StrictModel):
    elements: list[EAElement] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_element_references(self) -> ArchitectureModel:
        element_ids = [element.id for element in self.elements]
        duplicate_ids = sorted({element_id for element_id in element_ids if element_ids.count(element_id) > 1})
        if duplicate_ids:
            raise ValueError(f"architecture model contains duplicate element ids: {', '.join(duplicate_ids)}")

        known_ids = set(element_ids)
        reference_fields = (
            "related_elements",
            "supported_capabilities",
            "supported_processes",
            "supported_applications",
        )
        missing_references: list[str] = []
        for element in self.elements:
            for field_name in reference_fields:
                for reference_id in getattr(element, field_name):
                    if reference_id not in known_ids:
                        missing_references.append(f"{element.id}.{field_name}: {reference_id}")

        if missing_references:
            raise ValueError(
                "architecture model contains unknown element references: "
                + ", ".join(missing_references)
            )

        return self


class EnrichedAlert(StrictModel):
    alert: DigitalTwinAlert
    mapped_element: EAElement
    business_impact: dict[str, list[str]]
    recommended_bpmn_process: str | None
    recommended_owner: str
    risk_level: str
    trace: list[str] = Field(default_factory=list)
