import json

import pytest

from speedtest.data import results


@pytest.fixture
def sample_result():
    return {
        "download": 125000000,
        "upload": 25000000,
        "ping": 15,
        "timestamp": "2025-01-15T10:30:00.000000Z",
        "server": {},
        "client": {},
        "bytes_sent": 0,
        "bytes_received": 0,
        "share": None,
    }


class TestReadArray:
    def test_returns_empty_list_for_nonexistent_file(self, tmp_path):
        source = tmp_path / "nonexistent.json"
        result = results.read_array(source)
        assert result == []

    def test_reads_existing_array(self, tmp_path):
        source = tmp_path / "data.json"
        expected_data = [{"key": "value1"}, {"key": "value2"}]
        source.write_text(json.dumps(expected_data))

        result = results.read_array(source)
        assert result == expected_data

    def test_raises_type_exception_for_non_list(self, tmp_path):
        source = tmp_path / "data.json"
        source.write_text(json.dumps({"not": "a list"}))

        with pytest.raises(results.TypeException, match="Expected list type"):
            results.read_array(source)

    def test_reads_empty_array(self, tmp_path):
        source = tmp_path / "data.json"
        source.write_text(json.dumps([]))

        result = results.read_array(source)
        assert result == []


class TestUpdateArray:
    def test_creates_new_file_with_result(self, tmp_path, sample_result):
        source = tmp_path / "data.json"

        results.update_array(source, sample_result)

        assert source.exists()
        data = json.loads(source.read_text())
        assert data == [sample_result]

    def test_appends_to_existing_array(self, tmp_path, sample_result):
        source = tmp_path / "data.json"
        existing_data = [{"existing": "data"}]
        source.write_text(json.dumps(existing_data))

        results.update_array(source, sample_result)

        data = json.loads(source.read_text())
        assert len(data) == 2
        assert data[0] == {"existing": "data"}
        assert data[1] == sample_result

    def test_creates_parent_directories(self, tmp_path, sample_result):
        source = tmp_path / "nested" / "path" / "data.json"

        results.update_array(source, sample_result)

        assert source.exists()
        assert source.parent.exists()

    def test_formats_json_with_indent(self, tmp_path, sample_result):
        source = tmp_path / "data.json"

        results.update_array(source, sample_result)

        content = source.read_text()
        assert "    " in content  # Check for indentation

    def test_multiple_updates_accumulate(self, tmp_path, sample_result):
        source = tmp_path / "data.json"

        results.update_array(source, sample_result)
        results.update_array(source, sample_result)
        results.update_array(source, sample_result)

        data = json.loads(source.read_text())
        assert len(data) == 3


class TestTypeException:
    def test_type_exception_is_exception(self):
        assert issubclass(results.TypeException, Exception)

    def test_type_exception_message(self):
        exc = results.TypeException("Custom message")
        assert str(exc) == "Custom message"
