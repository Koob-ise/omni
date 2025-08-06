import disnake
from disnake.ext import commands
from disnake.ui import View, Button
from database.db import add_ban, add_mute, add_kick
import logging
import re
import asyncio
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

ACTION_PERM_MAP = {
    "kick": "kick",
    "mute": "mute",
    "ban": "ban"
}


class ConfirmPunishmentView(View):
    def __init__(self, offender, action, duration_str, reason, delete_days):
        super().__init__(timeout=60)
        self.offender = offender
        self.action = action
        self.duration_str = duration_str
        self.reason = reason
        self.delete_days = delete_days
        self.confirmed = False

    @disnake.ui.button(label="Confirm", style=disnake.ButtonStyle.green)
    async def confirm(self, button: Button, inter: disnake.MessageInteraction):
        if not self.check_control_permission(inter):
            await inter.response.send_message("❌ You don't have permission to confirm!", ephemeral=True)
            return

        self.confirmed = True
        await inter.response.edit_message(content="✅ Punishment confirmed", view=None)
        self.stop()

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.red)
    async def cancel(self, button: Button, inter: disnake.MessageInteraction):
        if not self.check_control_permission(inter):
            await inter.response.send_message("❌ You don't have permission to cancel!", ephemeral=True)
            return

        await inter.response.edit_message(content="❌ Punishment canceled", view=None)
        self.stop()

    def check_control_permission(self, inter):
        action_perm = ACTION_PERM_MAP.get(self.action.lower())
        if not action_perm:
            return False

        ctrl_perm = f"discord-{action_perm}-ctrl"

        for role in inter.author.roles:
            role_id = role.id
            for role_data in inter.bot.roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    permissions = [p.strip() for p in role_data["permissions"].split(",")]
                    if ctrl_perm in permissions:
                        return True
        return False


def parse_duration(duration_str: str) -> timedelta:
    total_seconds = 0
    pattern = r'(\d+)\s*([dhm])'
    matches = re.findall(pattern, duration_str.lower())

    if not matches:
        raise ValueError("Invalid duration format")

    for value, unit in matches:
        value = int(value)
        if unit == 'd':
            total_seconds += value * 86400
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60

    return timedelta(seconds=total_seconds)


async def find_offender_in_ticket(channel):
    async for message in channel.history(limit=1, oldest_first=True):
        if not message.embeds:
            return None

        embed = message.embeds[0]

        offender_field = None
        for field in embed.fields:
            field_name = field.name.lower()
            if any(keyword in field_name for keyword in ["offender"]):
                offender_field = field.value
                break

        return offender_field
    return None


def has_permission(member, action, roles_config):
    action_perm = ACTION_PERM_MAP.get(action.lower())
    if not action_perm:
        return False

    base_perm = f"discord-{action_perm}"
    ctrl_perm = f"{base_perm}-ctrl"

    for role in member.roles:
        role_id = role.id
        for role_data in roles_config["staff_roles"].values():
            if role_data["id"] == role_id and role_data.get("permissions"):
                permissions = [p.strip() for p in role_data["permissions"].split(",")]
                if base_perm in permissions or ctrl_perm in permissions:
                    return True
    return False


async def apply_punishment(inter, offender, action, duration_delta, reason, delete_days):
    try:
        if action == "ban":
            await inter.guild.ban(offender, reason=reason, delete_message_days=delete_days)
            add_ban("discord", offender.id, inter.author.id, reason, duration_delta.days if duration_delta else None)
        elif action == "mute":
            add_mute("discord", offender.id, inter.author.id, reason, duration_delta.days)
        elif action == "kick":
            await offender.kick(reason=reason)
            add_kick("discord", offender.id, inter.author.id, reason)

        return True
    except Exception as e:
        log.error(f"Error applying punishment: {e}")
        return False


def setup_moderation_commands(bot, channels_config, roles_config):
    bot.roles_config = roles_config  # Save roles config in bot

    @bot.slash_command(name="punishment")
    async def punishment(
            inter: disnake.ApplicationCommandInteraction,
            action: str = commands.Param(choices=["ban", "mute", "kick"]),
            duration: str = commands.Param(
                None,
                description="Duration (e.g.: 7d 3h 30m). Not required for kick"
            ),
            delete_days: int = commands.Param(
                0,
                ge=0,
                le=7,
                description="Delete messages from last N days (ban only)",
            ),
            reason: str = commands.Param("No comment", description="Punishment reason")
    ):
        ticket_category_id = channels_config["categories"]["❓│Помощь / Support"]["id"]
        if inter.channel.category_id != ticket_category_id:
            return await inter.response.send_message("❌ Command only available in report channels!", ephemeral=True)

        if not has_permission(inter.author, action, roles_config):
            return await inter.response.send_message("❌ Insufficient permissions for this action!", ephemeral=True)

        offender_tag = await find_offender_in_ticket(inter.channel)
        if not offender_tag:
            return await inter.response.send_message(
                "❌ Could not automatically find offender in ticket! "
                "Please specify tag manually: @username",
                ephemeral=True
            )

        clean_tag = re.sub(r'[<@>]', '', offender_tag).strip()

        offender = None
        try:
            offender_id = int(clean_tag)
            offender = await inter.guild.fetch_member(offender_id)
        except (ValueError, disnake.NotFound):
            offender = inter.guild.get_member_named(clean_tag)

        if not offender:
            return await inter.response.send_message(
                f"❌ User {offender_tag} not found on server!",
                ephemeral=True
            )

        duration_delta = None
        if action in ["ban", "mute"]:
            if not duration:
                return await inter.response.send_message(
                    f"❌ Duration required for {action}!",
                    ephemeral=True
                )

            try:
                duration_delta = parse_duration(duration)

                if action == "mute":
                    if duration_delta > timedelta(days=28):
                        return await inter.response.send_message(
                            "❌ Maximum mute duration is 28 days!",
                            ephemeral=True
                        )
                    if duration_delta < timedelta(minutes=1):
                        return await inter.response.send_message(
                            "❌ Minimum mute duration is 1 minute!",
                            ephemeral=True
                        )
            except ValueError as e:
                return await inter.response.send_message(
                    f"❌ Duration format error: {e}\n"
                    "Correct format: `7d 3h 30m` (days, hours, minutes)\n"
                    "Examples: `3d`, `2h 30m`, `7d 12h`",
                    ephemeral=True
                )

        embed = disnake.Embed(
            title="🛑 Punishment Confirmation",
            color=disnake.Color.orange()
        )
        embed.add_field(name="👤 Offender", value=offender.mention, inline=True)
        embed.add_field(name="⚖️ Action", value=action, inline=True)

        if duration_delta:
            days = duration_delta.days
            hours = duration_delta.seconds // 3600
            minutes = (duration_delta.seconds % 3600) // 60

            duration_parts = []
            if days: duration_parts.append(f"{days} days")
            if hours: duration_parts.append(f"{hours} hrs")
            if minutes: duration_parts.append(f"{minutes} min")

            duration_text = " ".join(duration_parts)
            embed.add_field(name="⏱ Duration", value=duration_text, inline=True)

        if action == "ban" and delete_days > 0:
            embed.add_field(
                name="🗑 Delete messages",
                value=f"Last {delete_days} days",
                inline=True
            )

        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Confirm or cancel punishment")

        view = ConfirmPunishmentView(
            offender=offender,
            action=action,
            duration_str=duration,
            reason=reason,
            delete_days=delete_days
        )

        confirmation_msg = await inter.channel.send(embed=embed, view=view)

        await inter.response.send_message(
            "⏳ Waiting for punishment confirmation...",
            ephemeral=True
        )

        try:
            await view.wait()
            if view.confirmed:
                success = await apply_punishment(
                    inter, offender, action, duration_delta, reason, delete_days
                )

                if success:
                    punishments_channel_id = channels_config["channels"]["📌│punishments"]["id"]
                    channel = inter.guild.get_channel(punishments_channel_id)
                    if channel:
                        log_embed = disnake.Embed(
                            title="🚨 Punishment Applied",
                            color=disnake.Color.red(),
                            timestamp=disnake.utils.utcnow()
                        )
                        log_embed.add_field(name="👤 Offender", value=f"{offender.mention} ({offender.id})", inline=True)
                        log_embed.add_field(name="🛡 Moderator", value=inter.author.mention, inline=True)
                        log_embed.add_field(name="⚖️ Action", value=action, inline=True)

                        if duration_delta:
                            end_time = disnake.utils.utcnow() + duration_delta
                            log_embed.add_field(name="🕒 Ends at", value=f"<t:{int(end_time.timestamp())}:f>",
                                                inline=True)

                        if action == "ban" and delete_days > 0:
                            log_embed.add_field(
                                name="🗑 Messages deleted",
                                value=f"Last {delete_days} days",
                                inline=True
                            )

                        log_embed.add_field(name="📝 Reason", value=reason, inline=False)

                        try:
                            await channel.send(embed=log_embed)
                        except Exception as e:
                            log.error(f"Error sending log: {e}")

                    await inter.edit_original_message(
                        content=f"✅ {action.capitalize()} applied to {offender.mention}!"
                    )
                else:
                    await inter.edit_original_message(
                        content=f"❌ Failed to apply punishment to {offender.mention}!"
                    )
        except Exception as e:
            log.error(f"Error confirming punishment: {e}")
            await inter.edit_original_message(
                content="❌ An error occurred while processing punishment"
            )
        finally:
            try:
                await confirmation_msg.delete()
            except:
                pass