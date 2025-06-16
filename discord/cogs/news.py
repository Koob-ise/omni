import disnake
from disnake import Embed, Webhook
from disnake.ext import commands
from disnake.ui import Modal, TextInput
import json
import os

def load_config(file_path="configs/channels_config.json"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠ Ошибка загрузки конфигурации: {e}")
        return None

async def post_news_to_channel(bot: disnake.Client, channel_id: int, webhook_config: dict, title: str, description: str, image_url: str, footer: str, author: disnake.User):
    channel = bot.get_channel(channel_id)
    if not channel:
        print(f"❌ Канал {channel_id} не найден!")
        return False

    author_avatar = str(author.avatar.url) if author.avatar else webhook_config["avatar"]

    embed = Embed(
        title=title,
        description=description,
        color=disnake.Color.blue(),
        timestamp=disnake.utils.utcnow()
    )
    embed.set_footer(text=footer, icon_url=author_avatar)
    if image_url:
        embed.set_image(url=image_url)

    try:
        webhook = await channel.create_webhook(
            name=webhook_config.get("name", "Omnicorp Bot"),
            reason=webhook_config.get("reason", "News message")
        )

        await webhook.send(
            embed=embed,
            username=webhook_config.get("name", "Omnicorp Bot"),
            avatar_url=webhook_config.get("avatar")
        )
        await webhook.delete()
        print(f"✅ Новость отправлена в канал {channel_id}")
        return True

    except Exception as e:
        print(f"⚠ Ошибка при работе с вебхуком в канале {channel_id}: {e}")
        return False

class NewsModal(Modal):
    def __init__(self, bot, channel_id, webhook_config, author):
        self.bot = bot
        self.channel_id = channel_id
        self.webhook_config = webhook_config
        self.author = author

        components = [
            TextInput(
                label="Заголовок / Title",
                custom_id="news_title",
                style=disnake.TextInputStyle.short,
                max_length=100,
                required=True
            ),
            TextInput(
                label="Описание / Description",
                custom_id="news_description",
                style=disnake.TextInputStyle.paragraph,
                max_length=2000,
                required=True
            ),
            TextInput(
                label="Картинка / Image URL (optional)",
                custom_id="news_image_url",
                style=disnake.TextInputStyle.short,
                required=False
            ),
            TextInput(
                label="Подпись / Footer (optional)",
                custom_id="news_footer",
                style=disnake.TextInputStyle.short,
                required=False
            )
        ]

        super().__init__(title="Создать новость / Create News", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        title = inter.text_values["news_title"]
        description = inter.text_values["news_description"]
        image_url = inter.text_values["news_image_url"]
        footer = inter.text_values["news_footer"] or f"Опубликовал: {self.author.display_name} | OmniCorp © 2025"

        success = await post_news_to_channel(
            self.bot, self.channel_id, self.webhook_config,
            title, description, image_url, footer, self.author
        )

        if success:
            await inter.response.send_message("✅ Новость опубликована!", ephemeral=True)
        else:
            await inter.response.send_message("❌ Ошибка при публикации!", ephemeral=True)

class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        if not self.config:
            print("❌ Конфигурация не загружена!")

    @commands.slash_command(name="postnews", description="Опубликовать новость / Post a news")
    async def post_news(
        self,
        inter: disnake.AppCmdInter,
        language: str = commands.Param(
            choices=["Русский / Russian", "Английский / English"],
            description="Выберите язык / Choose language"
        )
    ):
        if not self.config:
            await inter.response.send_message("❌ Конфигурация не загружена!", ephemeral=True)
            return

        channels = self.config.get("channels", {})
        channel_key = "📢│новости" if language == "Русский / Russian" else "📢│announcements"
        channel_config = channels.get(channel_key)

        if not channel_config:
            await inter.response.send_message("❌ Канал не найден в конфиге!", ephemeral=True)
            return

        modal = NewsModal(
            bot=self.bot,
            channel_id=channel_config["id"],
            webhook_config=channel_config["webhook"],
            author=inter.author
        )
        await inter.response.send_modal(modal)

def setup(bot):
    bot.add_cog(News(bot))
