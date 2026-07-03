from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from yaml import YAMLError

from .models import ArchitectureModel, AssetMapping, DigitalTwinAlert


def load_alert(path: Path) -> DigitalTwinAlert:
    """Load and validate a Digital Twin alert JSON file"""

    data = _load_json_object(path, "alert")
    try:
        return DigitalTwinAlert.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid alert file {path}: {exc}") from exc


def load_mapping(path: Path) -> dict[str, AssetMapping]:
    """Load and validate an asset-to-architecture mapping YAML file"""

    data = _load_yaml_object(path, "mapping")
    assets = data.get("assets")
    if not isinstance(assets, list):
        raise ValueError(f"Invalid mapping file {path}: expected top-level 'assets' list")

    mappings: dict[str, AssetMapping] = {}
    for index, item in enumerate(assets, start=1):
        try:
            mapping = AssetMapping.model_validate(item)
        except ValidationError as exc:
            raise ValueError(f"Invalid mapping entry #{index} in {path}: {exc}") from exc

        if mapping.asset_id in mappings:
            raise ValueError(f"Invalid mapping file {path}: duplicate asset_id '{mapping.asset_id}'")
        mappings[mapping.asset_id] = mapping

    return mappings


def load_architecture_model(path: Path) -> ArchitectureModel:
    """Load and validate an EA model YAML file"""

    data = _load_yaml_object(path, "architecture model")
    try:
        return ArchitectureModel.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid architecture model file {path}: {exc}") from exc


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    _ensure_readable_file(path, label)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {label} JSON file {path}: {exc.msg} at line {exc.lineno}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Invalid {label} JSON file {path}: expected a JSON object")
    return data


def _load_yaml_object(path: Path, label: str) -> dict[str, Any]:
    _ensure_readable_file(path, label)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        raise ValueError(f"Invalid {label} YAML file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Invalid {label} YAML file {path}: expected a YAML object")
    return data


def _ensure_readable_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label.capitalize()} file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label.capitalize()} path is not a file: {path}")
