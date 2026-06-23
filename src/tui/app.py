"""src/tui/app.py"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane
from src.tui.screens.portfolio import PortfolioScreen
from src.tui.screens.market import MarketScreen
from src.tui.screens.config import ConfigScreen
from src.tui.screens.realtime import RealtimeScreen
from src.tui.widgets.status_bar import StatusBar


class AiTouGuApp(App):
    """AI 投顾 TUI 主应用。"""
    CSS = """
    Screen { layout: vertical; }
    TabbedContent { height: 1fr; }
    TabPane { height: 1fr; }
    PortfolioScreen, MarketScreen, ConfigScreen, RealtimeScreen {
        height: 1fr;
        overflow-y: auto;
        overflow-x: hidden;
    }
    StatusBar { dock: bottom; height: 1; background: $panel; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="tab-portfolio"):
            with TabPane("📊 投资组合", id="tab-portfolio"):
                yield PortfolioScreen()
            with TabPane("🎯 市场扫描", id="tab-market"):
                yield MarketScreen()
            with TabPane("⚙️ 配置", id="tab-config"):
                yield ConfigScreen()
            with TabPane("📈 行情", id="tab-realtime"):
                yield RealtimeScreen()
        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        self.title = "AI 投顾"
        self.sub_title = "私人 AI 投资助手"


if __name__ == "__main__":
    AiTouGuApp().run()
