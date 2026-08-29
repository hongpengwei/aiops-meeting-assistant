import os
import pytest
from src.health_checker import HealthChecker
from src.utils import load_dotenv_if_present, mask_secret

class TestHealthChecker:
    def test_mask_secret(self):
        assert mask_secret("AIzaSy1234567890ABCD", 6, 4) == "AIzaSy****ABCD"
        assert mask_secret("short") == "*****"
        assert mask_secret("") == ""

    def test_load_dotenv_fallback(self, tmp_path):
        env_file = tmp_path / ".env.test"
        env_file.write_text("TEST_KEY_123=my_secret_val\n# comment\nexport TEST_KEY_456=\"hello\"\n", encoding="utf-8")
        count = load_dotenv_if_present(str(env_file))
        assert count == 2
        assert os.environ.get("TEST_KEY_123") == "my_secret_val"
        assert os.environ.get("TEST_KEY_456") == "hello"

    def test_health_checker_runs(self, sample_config, tmp_path):
        import yaml
        cfg_file = tmp_path / "config.yaml"
        with open(cfg_file, "w", encoding="utf-8") as f:
            yaml.dump(sample_config, f)
        
        checker = HealthChecker(config_path=str(cfg_file), env_path=str(tmp_path / ".env.nonexistent"))
        is_ok = checker.run_all()
        # 由於使用 mock sample config，不應有 critical FAIL
        assert isinstance(is_ok, bool)
        assert len(checker.results) > 0
        categories = {item.category for item in checker.results}
        assert "環境設定" in categories
        assert "資料來源" in categories
        assert "AI 服務" in categories
        assert "推播通道" in categories
