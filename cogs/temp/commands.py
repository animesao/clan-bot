import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
from typing import Optional
from main import clan_data, save_clan_data

class TempCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="tempchannel",
        description="Управление временным каналом"
    )
    async def tempchannel(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @tempchannel.sub_command(
        name="create",
        description="Создать временный голосовой канал"
    )
    async def create_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(description="Название канала"),
        user_limit: int = commands.Param(
            description="Лимит пользователей (0 - без лимита)",
            default=0,
            min_value=0,
            max_value=99
        ),
        bitrate: int = commands.Param(
            description="Битрейт канала (в кбит/с)",
            default=128,
            min_value=8,
            max_value=384
        )
    ):
        try:
            if not clan_data['temp_channels']['enabled']:
                await inter.response.send_message("❌ Система временных каналов отключена!", ephemeral=True)
                return

            category = self.bot.get_channel(clan_data['temp_channels']['category_id'])
            if not category:
                await inter.response.send_message("❌ Категория для временных каналов не найдена!", ephemeral=True)
                return

            # Создаем канал
            channel = await category.create_voice_channel(
                name=name,
                user_limit=user_limit,
                bitrate=bitrate * 1000
            )

            # Перемещаем пользователя в новый канал
            if inter.author.voice:
                await inter.author.move_to(channel)

            await inter.response.send_message(
                f"✅ Временный канал {channel.mention} создан!",
                ephemeral=True
            )
        except Exception as e:
            await inter.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    @tempchannel.sub_command(
        name="limit",
        description="Установить лимит пользователей для временного канала"
    )
    async def set_limit(
        self,
        inter: disnake.ApplicationCommandInteraction,
        limit: int = commands.Param(
            description="Лимит пользователей (0 - без лимита)",
            min_value=0,
            max_value=99
        )
    ):
        try:
            if not inter.author.voice:
                await inter.response.send_message("❌ Вы должны быть в голосовом канале!", ephemeral=True)
                return

            channel = inter.author.voice.channel
            if not channel.category or channel.category.id != clan_data['temp_channels']['category_id']:
                await inter.response.send_message("❌ Эта команда работает только в временных каналах!", ephemeral=True)
                return

            await channel.edit(user_limit=limit)
            await inter.response.send_message(
                f"✅ Лимит пользователей установлен на {limit if limit > 0 else 'без лимита'}!",
                ephemeral=True
            )
        except Exception as e:
            await inter.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    @tempchannel.sub_command(
        name="name",
        description="Изменить название временного канала"
    )
    async def rename_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(description="Новое название канала")
    ):
        try:
            if not inter.author.voice:
                await inter.response.send_message("❌ Вы должны быть в голосовом канале!", ephemeral=True)
                return

            channel = inter.author.voice.channel
            if not channel.category or channel.category.id != clan_data['temp_channels']['category_id']:
                await inter.response.send_message("❌ Эта команда работает только в временных каналах!", ephemeral=True)
                return

            await channel.edit(name=name)
            await inter.response.send_message(
                f"✅ Название канала изменено на {name}!",
                ephemeral=True
            )
        except Exception as e:
            await inter.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    @tempchannel.sub_command(
        name="bitrate",
        description="Изменить битрейт временного канала"
    )
    async def set_bitrate(
        self,
        inter: disnake.ApplicationCommandInteraction,
        bitrate: int = commands.Param(
            description="Битрейт канала (в кбит/с)",
            min_value=8,
            max_value=384
        )
    ):
        try:
            if not inter.author.voice:
                await inter.response.send_message("❌ Вы должны быть в голосовом канале!", ephemeral=True)
                return

            channel = inter.author.voice.channel
            if not channel.category or channel.category.id != clan_data['temp_channels']['category_id']:
                await inter.response.send_message("❌ Эта команда работает только в временных каналах!", ephemeral=True)
                return

            await channel.edit(bitrate=bitrate * 1000)
            await inter.response.send_message(
                f"✅ Битрейт канала установлен на {bitrate} кбит/с!",
                ephemeral=True
            )
        except Exception as e:
            await inter.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    @tempchannel.sub_command(
        name="delete",
        description="Удалить временный канал"
    )
    async def delete_channel(self, inter: disnake.ApplicationCommandInteraction):
        try:
            if not inter.author.voice:
                await inter.response.send_message("❌ Вы должны быть в голосовом канале!", ephemeral=True)
                return

            channel = inter.author.voice.channel
            if not channel.category or channel.category.id != clan_data['temp_channels']['category_id']:
                await inter.response.send_message("❌ Эта команда работает только в временных каналах!", ephemeral=True)
                return

            await channel.delete()
            await inter.response.send_message(
                "✅ Временный канал удален!",
                ephemeral=True
            )
        except Exception as e:
            await inter.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(TempCommands(bot)) 