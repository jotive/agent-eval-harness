import pytest
import yaml
from pydantic import ValidationError

from app.core.dataset import load_dataset


def _write(tmp_path, text, name="dataset.yaml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_list_format(tmp_path):
    path = _write(tmp_path, "- id: a\n  input: hello\n- id: b\n  input: world\n")
    assert [c.id for c in load_dataset(path)] == ["a", "b"]


def test_loads_mapping_format(tmp_path):
    path = _write(tmp_path, "cases:\n  - id: a\n    input: hello\n")
    [case] = load_dataset(path)
    assert case.expect.contains == []


def test_mapping_without_cases_is_empty(tmp_path):
    assert load_dataset(_write(tmp_path, "other: 1\n")) == []


def test_accepts_string_path(tmp_path):
    path = _write(tmp_path, "cases:\n  - id: a\n    input: hello\n")
    assert len(load_dataset(str(path))) == 1


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "absent.yaml")


def test_invalid_yaml_raises(tmp_path):
    with pytest.raises(yaml.YAMLError):
        load_dataset(_write(tmp_path, "cases: [unclosed\n"))


def test_empty_file_raises(tmp_path):
    with pytest.raises(TypeError):
        load_dataset(_write(tmp_path, ""))


def test_missing_required_field_raises(tmp_path):
    with pytest.raises(ValidationError):
        load_dataset(_write(tmp_path, "cases:\n  - id: a\n"))


def test_wrong_field_type_raises(tmp_path):
    with pytest.raises(ValidationError):
        load_dataset(_write(tmp_path, "cases:\n  - id: a\n    input: x\n    expect:\n      max_steps: many\n"))


def test_duplicate_ids_raise(tmp_path):
    path = _write(tmp_path, "cases:\n  - id: a\n    input: x\n  - id: a\n    input: y\n")
    with pytest.raises(ValueError, match="duplicate case id"):
        load_dataset(path)


def test_shipped_datasets_are_valid():
    from pathlib import Path

    for path in sorted(Path(__file__).parent.parent.joinpath("datasets").glob("*.yaml")):
        assert load_dataset(path)
