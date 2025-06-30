import disnake
from disnake import ui
import time
import logging
from .config import user_states, last_cleanup, TYPE_OPTIONS, TYPE_OPTIONS_RU, PLATFORM_OPTIONS, PLATFORM_OPTIONS_RU, MODAL_CONFIGS, MODAL_CONFIGS_RU
from .utils import create_ticket_channel

log = logging.getLogger(__name__)

class FeedbackView(ui.View):
    def __init__(self, bot, channels_config, roles_config, lang="en", is_russian=False):
        super().__init__(timeout=None)
        self.bot = bot
        self.channels_config = channels_config
        self.roles_config = roles_config
        self.lang = lang
        self.is_russian = is_russian

        type_options = TYPE_OPTIONS_RU if is_russian else TYPE_OPTIONS
        type_placeholder = "Выберите тип обращения" if is_russian else "Select request type"
        self.type_select = ui.StringSelect(
            placeholder=type_placeholder,
            min_values=1,
            max_values=1,
            options=[disnake.SelectOption(**opt) for opt in type_options],
            custom_id=f"type_select_{lang}"
        )
        self.type_select.callback = self.type_callback
        self.add_item(self.type_select)

        platform_options = PLATFORM_OPTIONS_RU if is_russian else PLATFORM_OPTIONS
        platform_placeholder = "Выберите платформу" if is_russian else "Select platform"
        self.platform_select = ui.StringSelect(
            placeholder=platform_placeholder,
            min_values=1,
            max_values=1,
            options=[disnake.SelectOption(**opt) for opt in platform_options],
            custom_id=f"platform_select_{lang}"
        )
        self.platform_select.callback = self.platform_callback
        self.add_item(self.platform_select)

        submit_label = "Заполнить форму" if is_russian else "Fill Form"
        self.submit_button = ui.Button(
            label=submit_label,
            style=disnake.ButtonStyle.green,
            custom_id=f"submit_{lang}"
        )
        self.submit_button.callback = self.submit_callback
        self.add_item(self.submit_button)

    async def type_callback(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer(ephemeral=True, with_message=False)
        state_key = (interaction.message.id, interaction.user.id)
        selected_value = interaction.data["values"][0]

        if state_key not in user_states:
            user_states[state_key] = {}
        user_states[state_key]["selected_type"] = selected_value
        user_states[state_key]["timestamp"] = time.time()

    async def platform_callback(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer(ephemeral=True, with_message=False)
        state_key = (interaction.message.id, interaction.user.id)
        selected_value = interaction.data["values"][0]

        if state_key not in user_states:
            user_states[state_key] = {}
        user_states[state_key]["selected_platform"] = selected_value
        user_states[state_key]["timestamp"] = time.time()

    async def submit_callback(self, interaction: disnake.MessageInteraction):
        state_key = (interaction.message.id, interaction.user.id)
        state = user_states.get(state_key, {})

        if not (state.get("selected_type") and state.get("selected_platform")):
            error_msg = "❗ Сначала выберите тип и платформу." if self.is_russian else "❗ Please select both type and platform first."
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        if time.time() - state.get("timestamp", 0) > 1800:
            error_msg = "❗ Ваш выбор устарел, начните заново." if self.is_russian else "❗ Your selection has expired, please start over."
            await interaction.response.send_message(error_msg, ephemeral=True)
            if state_key in user_states:
                del user_states[state_key]
            return

        if self.is_russian:
            modal_config = MODAL_CONFIGS_RU[state["selected_type"]]
            title_for_ticket = MODAL_CONFIGS[state["selected_type"]]["title"]
        else:
            modal_config = MODAL_CONFIGS[state["selected_type"]]
            title_for_ticket = modal_config["title"]

        inputs = []
        for input_config in modal_config["inputs"]:
            if "condition" in input_config and not input_config["condition"](state["selected_platform"]):
                continue
            inputs.append(ui.TextInput(
                label=input_config["label"],
                custom_id=input_config["custom_id"],
                style=input_config["style"],
                max_length=input_config.get("max_length", 4000)
            ))

        class FeedbackModal(ui.Modal):
            def __init__(self, is_russian, channels_config, roles_config):
                super().__init__(
                    title=modal_config["title"],
                    custom_id=f"modal_{state['selected_type']}_{state['selected_platform']}",
                    components=inputs
                )
                self.is_russian = is_russian
                self.channels_config = channels_config
                self.roles_config = roles_config

            async def callback(self, modal_interaction: disnake.ModalInteraction):
                await modal_interaction.response.defer(ephemeral=True)
                try:
                    channel = await create_ticket_channel(
                        modal_interaction,
                        title_for_ticket,
                        state["selected_platform"],
                        modal_interaction.text_values,
                        "ru" if self.is_russian else "en",
                        self.channels_config,
                        self.roles_config
                    )
                    success_msg = f"✅ Канал создан: {channel.mention}" if self.is_russian else f"✅ Channel created: {channel.mention}"
                    await modal_interaction.followup.send(success_msg, ephemeral=True)
                except Exception as e:
                    log.error(f"Ticket creation error: {e}")
                    error_msg = "❌ Ошибка при создании тикета" if self.is_russian else "❌ Error creating ticket"
                    await modal_interaction.followup.send(error_msg, ephemeral=True)
                finally:
                    if state_key in user_states:
                        del user_states[state_key]

        await interaction.response.send_modal(FeedbackModal(
            is_russian=self.is_russian,
            channels_config=self.channels_config,
            roles_config=self.roles_config
        ))