from dataclasses import dataclass
from enum import Enum


@dataclass
class BaseApp:
    """"""

    class Emoji(Enum):
        """"""
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


    def print_log(self, status, message):
        """Print a log."""

        if self.verbose:
            print(f"{self.Emoji[status].value}{message}")

