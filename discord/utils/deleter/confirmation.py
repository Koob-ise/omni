import disnake
from disnake.ui import Button, View

deletion_data = {}

async def create_confirmation_view(inter, content, data_type, **data):
    await inter.response.defer(ephemeral=True)
    deletion_data[inter.id] = {
        "type": data_type,
        "author_id": inter.author.id,
        **data
    }
    view = View(timeout=60)
    confirm_button = Button(style=disnake.ButtonStyle.danger, label="Confirm", custom_id=f"confirm_{inter.id}")
    cancel_button = Button(style=disnake.ButtonStyle.secondary, label="Cancel", custom_id=f"cancel_{inter.id}")
    view.add_item(confirm_button)
    view.add_item(cancel_button)
    await inter.followup.send(content, ephemeral=True, view=view)