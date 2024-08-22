"""Base Relayer application."""
from dataclasses import dataclass
from enum import Enum


@dataclass
class BaseApp:
    """Base application."""

    class Emoji(Enum):
        """Emoji enum."""

        none = ""
        main = "💠 "
        receive = "📩 "
        success = "🟢 "
        info = "🔵 "
        alert = "🟠 "
        fail = "🔴 "
        wait = "⏳ "
        emark = "❕ "
        sendTx = "🟣 "
        receiveEvent = "🔵 "
        blockFinality = "🟡 "
        green = "🟢 "
        blue = "🔵 "
        yellow = "🟡 "
        orange = "🟠 "
        violet = "🟣 "
        red = "🔴 "


    def print_log(self, status: str, message: str):
        """Print log.

        Args:
            status (str): The status
            message (str): The message
        """
        print(f"{self.Emoji[status].value}{message}")

