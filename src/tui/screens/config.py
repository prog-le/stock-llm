"""src/tui/screens/config.py"""
import os
from textual.containers import Vertical
from textual.widgets import Static, Input, Button, RichLog
from dotenv import load_dotenv, set_key

ENV_PATH = ".env"


class ConfigScreen(Vertical):
    TITLE = "⚙️ 配置"

    def compose(self):
        yield Static("API 配置", classes="section-title")
        yield Input(
            value=os.getenv("DEEPSEEK_API_KEY", ""),
            placeholder="DeepSeek API Key",
            id="deepseek-key", password=True
        )
        yield Input(
            value=os.getenv("TUSHARE_TOKEN", ""),
            placeholder="Tushare Token",
            id="tushare-token", password=True
        )
        yield Input(
            value=os.getenv("MAIRUI_LICENSE", ""),
            placeholder="麦蕊 License",
            id="mairui-license", password=True
        )
        yield Button("💾 保存", id="save-btn")
        yield Button("🔌 测试连接", id="test-btn")
        yield RichLog(id="config-log", max_lines=10)

    def on_mount(self) -> None:
        load_dotenv()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save_config()
        elif event.button.id == "test-btn":
            self._test_connection()

    def _save_config(self) -> None:
        pairs = [
            ("DEEPSEEK_API_KEY", "deepseek-key"),
            ("TUSHARE_TOKEN", "tushare-token"),
            ("MAIRUI_LICENSE", "mairui-license"),
        ]
        for env_key, input_id in pairs:
            val = self.query_one(f"#{input_id}", Input).value
            set_key(ENV_PATH, env_key, val)
        log = self.query_one("#config-log", RichLog)
        log.write("✅ 配置已保存到 .env")

    def _test_connection(self) -> None:
        log = self.query_one("#config-log", RichLog)
        load_dotenv()
        # Test DeepSeek
        key = os.getenv("DEEPSEEK_API_KEY")
        if key:
            log.write("🔑 DeepSeek: API Key 已设置")
        else:
            log.write("⚠️ DeepSeek: API Key 未设置")

        # Test Tushare
        token = os.getenv("TUSHARE_TOKEN")
        if token:
            log.write("🔑 Tushare: Token 已设置")
        else:
            log.write("⚠️ Tushare: Token 未设置")

        # Test 麦蕊
        lic = os.getenv("MAIRUI_LICENSE")
        if lic:
            log.write("🔑 麦蕊: License 已设置")
        else:
            log.write("⚠️ 麦蕊: License 未设置")
