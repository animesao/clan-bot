import disnake
from disnake.ext import commands
import asyncio
from datetime import datetime, timedelta
import json
import os
from typing import Optional, Dict, List
from main import clan_data, save_clan_data

class TempChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}  # {channel_id: {"owner": member_id, "created_at": timestamp}}
        self.voice_states = {}  # {member_id: {"channel": channel_id, "joined_at": timestamp}}
        
        # Загружаем настройки временных каналов
        if 'temp_channels' not in clan_data:
            clan_data['temp_channels'] = {
                'enabled': False,
                'category_id': None,
                'name_template': "🎮 {username}",
                'user_limit': 0,
                'bitrate': 128000,
                'auto_delete': True,
                'delete_after': 300,  # 5 минут
                'allowed_roles': [],
                'prefix': "🎮",
                'suffix': "",
                'default_name': "Временный канал"
            }
            save_clan_data()

    @commands.slash_command(
        name="temp",
        description="Управление временными каналами"
    )
    @commands.has_permissions(administrator=True)
    async def temp(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @temp.sub_command(
        name="setup",
        description="Настроить систему временных каналов"
    )
    async def setup_temp(
        self,
        inter: disnake.ApplicationCommandInteraction,
        category: disnake.CategoryChannel = commands.Param(description="Категория для временных каналов"),
        name_template: str = commands.Param(
            description="Шаблон названия канала (используйте {username} для имени пользователя)",
            default="🎮 {username}"
        ),
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
        ),
        auto_delete: bool = commands.Param(
            description="Автоматически удалять пустые каналы",
            default=True
        ),
        delete_after: int = commands.Param(
            description="Удалять канал через X секунд после опустения",
            default=300,
            min_value=60,
            max_value=3600
        ),
        prefix: str = commands.Param(
            description="Префикс для названия канала",
            default="🎮"
        ),
        suffix: str = commands.Param(
            description="Суффикс для названия канала",
            default=""
        )
    ):
        try:
            clan_data['temp_channels'].update({
                'enabled': True,
                'category_id': category.id,
                'name_template': name_template,
                'user_limit': user_limit,
                'bitrate': bitrate * 1000,  # Конвертируем в биты
                'auto_delete': auto_delete,
                'delete_after': delete_after,
                'prefix': prefix,
                'suffix': suffix
            })
            save_clan_data()

            embed = disnake.Embed(
                title="✅ Настройки временных каналов обновлены",
                color=disnake.Color.green()
            )
            embed.add_field(name="Категория", value=category.mention, inline=True)
            embed.add_field(name="Шаблон названия", value=name_template, inline=True)
            embed.add_field(name="Лимит пользователей", value=str(user_limit) if user_limit > 0 else "Без лимита", inline=True)
            embed.add_field(name="Битрейт", value=f"{bitrate} кбит/с", inline=True)
            embed.add_field(name="Автоудаление", value="Включено" if auto_delete else "Выключено", inline=True)
            if auto_delete:
                embed.add_field(name="Удаление через", value=f"{delete_after} секунд", inline=True)
            embed.add_field(name="Префикс", value=prefix, inline=True)
            embed.add_field(name="Суффикс", value=suffix or "Нет", inline=True)

            await inter.response.send_message(embed=embed)
        except Exception as e:
            await inter.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    @temp.sub_command(
        name="toggle",
        description="Включить/выключить систему временных каналов"
    )
    async def toggle_temp(self, inter: disnake.ApplicationCommandInteraction):
        try:
            clan_data['temp_channels']['enabled'] = not clan_data['temp_channels']['enabled']
            save_clan_data()

            status = "включена" if clan_data['temp_channels']['enabled'] else "выключена"
            await inter.response.send_message(f"✅ Система временных каналов {status}!")
        except Exception as e:
            await inter.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    @temp.sub_command(
        name="settings",
        description="Показать текущие настройки временных каналов"
    )
    async def show_settings(self, inter: disnake.ApplicationCommandInteraction):
        try:
            settings = clan_data['temp_channels']
            category = self.bot.get_channel(settings['category_id']) if settings['category_id'] else None

            embed = disnake.Embed(
                title="⚙️ Настройки временных каналов",
                color=disnake.Color.blue()
            )
            embed.add_field(name="Статус", value="Включена" if settings['enabled'] else "Выключена", inline=True)
            embed.add_field(name="Категория", value=category.mention if category else "Не выбрана", inline=True)
            embed.add_field(name="Шаблон названия", value=settings['name_template'], inline=True)
            embed.add_field(name="Лимит пользователей", value=str(settings['user_limit']) if settings['user_limit'] > 0 else "Без лимита", inline=True)
            embed.add_field(name="Битрейт", value=f"{settings['bitrate'] // 1000} кбит/с", inline=True)
            embed.add_field(name="Автоудаление", value="Включено" if settings['auto_delete'] else "Выключено", inline=True)
            if settings['auto_delete']:
                embed.add_field(name="Удаление через", value=f"{settings['delete_after']} секунд", inline=True)
            embed.add_field(name="Префикс", value=settings['prefix'], inline=True)
            embed.add_field(name="Суффикс", value=settings['suffix'] or "Нет", inline=True)

            await inter.response.send_message(embed=embed)
        except Exception as e:
            await inter.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if not clan_data['temp_channels']['enabled']:
            return

        # Пользователь присоединился к голосовому каналу
        if after.channel and not before.channel:
            self.voice_states[member.id] = {
                "channel": after.channel.id,
                "joined_at": datetime.now()
            }

        # Пользователь покинул голосовой канал
        elif before.channel and not after.channel:
            if member.id in self.voice_states:
                del self.voice_states[member.id]

            # Проверяем, нужно ли удалить канал
            if before.channel.id in self.active_channels:
                if not before.channel.members and clan_data['temp_channels']['auto_delete']:
                    # Запускаем таймер на удаление
                    await asyncio.sleep(clan_data['temp_channels']['delete_after'])
                    # Проверяем, все еще пуст ли канал
                    if not before.channel.members:
                        await before.channel.delete()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if not clan_data['temp_channels']['enabled']:
            return

        settings = clan_data['temp_channels']
        category = self.bot.get_channel(settings['category_id'])

        # Пользователь присоединился к голосовому каналу
        if after.channel and not before.channel:
            # Если это канал создания временных каналов
            if after.channel.id == settings.get('create_channel_id'):
                # Создаем новый временный канал
                channel_name = settings['name_template'].format(username=member.display_name)
                if settings['prefix']:
                    channel_name = f"{settings['prefix']} {channel_name}"
                if settings['suffix']:
                    channel_name = f"{channel_name} {settings['suffix']}"

                new_channel = await category.create_voice_channel(
                    name=channel_name,
                    user_limit=settings['user_limit'],
                    bitrate=settings['bitrate']
                )

                # Перемещаем пользователя в новый канал
                await member.move_to(new_channel)

                # Сохраняем информацию о канале
                self.active_channels[new_channel.id] = {
                    "owner": member.id,
                    "created_at": datetime.now()
                }

        # Пользователь покинул голосовой канал
        elif before.channel and not after.channel:
            if before.channel.id in self.active_channels:
                if not before.channel.members and settings['auto_delete']:
                    # Запускаем таймер на удаление
                    await asyncio.sleep(settings['delete_after'])
                    # Проверяем, все еще пуст ли канал
                    if not before.channel.members:
                        await before.channel.delete()
                        del self.active_channels[before.channel.id]

def setup(bot):
    bot.add_cog(TempChannels(bot)) 