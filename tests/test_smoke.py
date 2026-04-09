from pathlib import Path

from core.pipeline import AutomationPipeline


def test_pipeline_smoke() -> None:
    pipeline = AutomationPipeline(project_root=Path(__file__).resolve().parents[1])
    result = pipeline.run("如果客厅温度高于30度，就打开客厅空调")
    assert result.validation.is_valid is True
    assert "automation" in result.yaml_text
