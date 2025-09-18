import disnake
from disnake.ui import Button, View

deletion_data = {}

async def create_confirmation_view(inter: disnake.ApplicationCommandInteraction, content: str, action_type: str, **data):
    await inter.response.defer(ephemeral=True)

    unique_id = inter.id
    deletion_data[unique_id] = {
        "type": action_type,
        "author_id": inter.author.id,
        **data
    }

    view = View(timeout=60)
    view.add_item(Button(style=disnake.ButtonStyle.danger, label="Confirm", custom_id=f"confirm_{unique_id}"))
    view.add_item(Button(style=disnake.ButtonStyle.secondary, label="Cancel", custom_id=f"cancel_{unique_id}"))

    async def on_timeout():
        if unique_id in deletion_data:
            del deletion_data[unique_id]

    view.on_timeout = on_timeout
    await inter.followup.send(content, view=view, ephemeral=True)