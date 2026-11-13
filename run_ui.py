from ui.chat_window import start_ui
from utils.tracing_setup import setup_tracing
if __name__ == "__main__":
    setup_tracing()
    start_ui()