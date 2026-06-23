"""src/tui/widgets/status_bar.py"""
from textual.widgets import Static
from textual.reactive import reactive


class StatusBar(Static):
    """全局状态栏 — 显示数据源 / LLM / 运行时间状态。"""

    data_source = reactive("检查中...")
    llm_status = reactive("就绪")
    last_run = reactive("从未")

    def render(self) -> str:
        return (
            f" 🔵 数据: {self.data_source}  "
            f" 🤖 LLM: {self.llm_status}  "
            f" ⏱ 上次运行: {self.last_run}"
        )
