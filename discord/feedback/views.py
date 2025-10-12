import disnake
from disnake import ui
import time
import logging
from configs.feedback_config import TYPE_OPTIONS_RU, TYPE_OPTIONS, PLATFORM_OPTIONS_RU, PLATFORM_OPTIONS, \
    MODAL_CONFIGS_RU, MODAL_CONFIGS, TEXTS, TICKET_COLORS
from .ticket_utils import create_ticket_channel
import os
import re

log = logging.getLogger(__name__)


class CloseTicketView(ui.View):
    def __init__(self, lang="en"):
        super().__init__(timeout=None)
        self.lang = lang
        texts = TEXTS[lang]["views"]

        self.add_item(ui.Button(
            label=texts["close_ticket"],
            style=disnake.ButtonStyle.red,
            custom_id="persistent_close_ticket"
        ))


class FeedbackView(ui.View):
    def __init__(self, lang="en", is_russian=False, user_states=None, webhook_name=None, channel_id=None,
                 banner_path=None):
        super().__init__(timeout=None)
        self.lang = lang
        self.is_russian = is_russian
        self.user_states = user_states if user_states is not None else {}
        self.webhook_name = webhook_name
        self.channel_id = channel_id
        self.banner_path = banner_path
        self.message = None
        self._rebuild_components()

    def _rebuild_components(self):
        self.clear_items()
        texts = TEXTS[self.lang]["views"]

        type_options = TYPE_OPTIONS_RU if self.is_russian else TYPE_OPTIONS
        self.type_select = ui.StringSelect(
            placeholder=texts["type_placeholder"],
            min_values=1,
            max_values=1,
            options=[disnake.SelectOption(**opt) for opt in type_options],
            custom_id=f"type_select_{self.lang}"
        )
        self.type_select.callback = self.type_callback
        self.add_item(self.type_select)

        platform_options = PLATFORM_OPTIONS_RU if self.is_russian else PLATFORM_OPTIONS
        self.platform_select = ui.StringSelect(
            placeholder=texts["platform_placeholder"],
            min_values=1,
            max_values=1,
            options=[disnake.SelectOption(**opt) for opt in platform_options],
            custom_id=f"platform_select_{self.lang}"
        )
        self.platform_select.callback = self.platform_callback
        self.add_item(self.platform_select)

        self.submit_button = ui.Button(
            label=texts["submit_button"],
            style=disnake.ButtonStyle.green,
            custom_id=f"submit_{self.lang}"
        )
        self.submit_button.callback = self.submit_callback
        self.add_item(self.submit_button)

    async def type_callback(self, interaction: disnake.MessageInteraction):
        try:
            await interaction.response.defer(ephemeral=True, with_message=False)
        except disnake.NotFound:
            return

        state_key = (interaction.message.id, interaction.user.id)
        selected_value = interaction.data["values"][0]
        if state_key not in self.user_states:
            self.user_states[state_key] = {}
        self.user_states[state_key]["selected_type"] = selected_value
        self.user_states[state_key]["timestamp"] = time.time()

    async def platform_callback(self, interaction: disnake.MessageInteraction):
        try:
            await interaction.response.defer(ephemeral=True, with_message=False)
        except disnake.NotFound:
            return

        state_key = (interaction.message.id, interaction.user.id)
        selected_value = interaction.data["values"][0]
        if state_key not in self.user_states:
            self.user_states[state_key] = {}
        self.user_states[state_key]["selected_platform"] = selected_value
        self.user_states[state_key]["timestamp"] = time.time()

    async def submit_callback(self, interaction: disnake.MessageInteraction):
        state_key = (interaction.message.id, interaction.user.id)
        state = self.user_states.get(state_key, {})
        texts = TEXTS[self.lang]["views"]

        if not (state.get("selected_type") and state.get("selected_platform")):
            await interaction.response.send_message(texts["errors"]["select_both"], ephemeral=True)
            return

        if time.time() - state.get("timestamp", 0) > 1800:
            await interaction.response.send_message(texts["errors"]["expired"], ephemeral=True)
            if state_key in self.user_states:
                del self.user_states[state_key]
            return

        selected_type = state["selected_type"]
        selected_platform = state["selected_platform"]

        if state_key in self.user_states:
            del self.user_states[state_key]

        if self.is_russian:
            modal_config = MODAL_CONFIGS_RU[selected_type]
            title_for_ticket = MODAL_CONFIGS[selected_type]["title"]
        else:
            modal_config = MODAL_CONFIGS[selected_type]
            title_for_ticket = modal_config["title"]

        inputs = []
        for input_config in modal_config["inputs"]:
            if "condition" in input_config and not input_config["condition"](selected_platform):
                continue
            inputs.append(disnake.ui.TextInput(
                label=input_config["label"],
                custom_id=input_config["custom_id"],
                style=input_config["style"],
                max_length=input_config.get("max_length", 4000)
            ))

        class FeedbackModal(disnake.ui.Modal):
            def __init__(self, is_russian, ticket_type, platform):
                super().__init__(
                    title=modal_config["title"],
                    custom_id=f"modal_{selected_type}_{selected_platform}",
                    components=inputs
                )
                self.is_russian = is_russian
                self.ticket_type = ticket_type
                self.platform = platform

            async def callback(self, modal_interaction: disnake.ModalInteraction):
                await modal_interaction.response.defer(ephemeral=True)
                try:
                    lang = "ru" if self.is_russian else "en"
                    texts_utils = TEXTS[lang]["ticket_utils"]

                    if self.ticket_type == "complaint" and self.platform == "discord":
                        offender_tag = modal_interaction.text_values.get("offender")
                        if not offender_tag or not offender_tag.strip():
                            await modal_interaction.followup.send(texts_utils["errors"]["missing_tag"], ephemeral=True)
                            return
                        if str(modal_interaction.author.id) in offender_tag:
                            error_msg = "Вы не можете пожаловаться на самого себя." if lang == "ru" else "You cannot report yourself."
                            await modal_interaction.followup.send(error_msg, ephemeral=True)
                            return

                        # --- НОВЫЙ БЛОК ПРОВЕРКИ ---
                        clean_tag = offender_tag.strip()
                        guild = modal_interaction.guild
                        offender = None

                        match = re.search(r'\d{17,}', clean_tag)
                        if match:
                            try:
                                offender_id = int(match.group(0))
                                offender = guild.get_member(offender_id) or await guild.fetch_member(offender_id)
                            except (ValueError, disnake.NotFound):
                                pass

                        if not offender:
                            offender = guild.get_member_named(clean_tag)

                        if not offender:
                            await modal_interaction.followup.send(
                                texts_utils["errors"]["member_not_found"].format(tag=clean_tag),
                                ephemeral=True
                            )
                            return
                        # --- КОНЕЦ НОВОГО БЛОКА ---

                    channel = await create_ticket_channel(
                        modal_interaction, title_for_ticket, selected_platform,
                        modal_interaction.text_values, lang=lang
                    )
                    await modal_interaction.followup.send(texts_utils["success"].format(channel=channel.mention),
                                                          ephemeral=True)
                except Exception as e:
                    log.error(f"Error creating ticket: {e}", exc_info=True)
                    await modal_interaction.followup.send(texts_utils["error"], ephemeral=True)

        modal = FeedbackModal(
            is_russian=self.is_russian,
            ticket_type=selected_type,
            platform=selected_platform
        )
        await interaction.response.send_modal(modal)

        try:
            channel = interaction.guild.get_channel(self.channel_id)
            if not channel:
                log.error(f"Channel not found: ID {self.channel_id}")
                return

            webhook = await self.find_webhook(channel, self.webhook_name)
            if not webhook:
                log.error(f"Webhook '{self.webhook_name}' not found in channel {channel.id}")
                return

            self._rebuild_components()

            feedback_texts = TEXTS[self.lang]["setup"]["feedback"]
            color_name = TICKET_COLORS.get("feedback", "orange")
            color = getattr(disnake.Color, color_name, disnake.Color.orange)()

            new_embed = disnake.Embed(
                title=feedback_texts["title"],
                description=feedback_texts["description"],
                color=color,
            )

            files_to_send = []
            if self.banner_path:
                try:
                    filename = os.path.basename(self.banner_path)
                    banner_file = disnake.File(self.banner_path, filename=filename)
                    files_to_send.append(banner_file)
                    new_embed.set_image(url=f"attachment://{filename}")
                except FileNotFoundError:
                    log.warning(f"Banner file not found at {self.banner_path} during message edit.")

            await webhook.edit_message(
                interaction.message.id,
                content=interaction.message.content,
                embeds=[new_embed],
                view=self,
                files=files_to_send
            )
        except Exception as e:
            log.error(f"Error updating message via webhook: {e}")

    async def find_webhook(self, channel, webhook_name):
        try:
            webhooks = await channel.webhooks()
            for wh in webhooks:
                if wh.name == webhook_name:
                    return wh
            return None
        except Exception as e:
            log.error(f"Error fetching webhooks: {e}")
            return None