import disnake
from disnake import ui

class CloseTicketView(ui.View):
    def __init__(self, lang="en"):
        super().__init__(timeout=None)
        self.lang = lang
        self.add_item(ui.Button(
            label="Закрыть тикет" if lang == "ru" else "Close Ticket",
            style=disnake.ButtonStyle.red,
            custom_id="persistent_close_ticket"
        ))