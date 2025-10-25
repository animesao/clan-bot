import disnake
from disnake.ext import commands
import re
import json
import os
from pathlib import Path

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discordapp\.com/invite)/[a-zA-Z0-9]+')
        self.url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
        
        # Создаем директорию data если её нет
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Путь к файлу настроек
        self.settings_file = self.data_dir / "automod.json"
        
        # Загружаем настройки
        self.settings = self.load_settings()

    def load_settings(self):
        """Загрузка настроек из файла"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.get_default_settings()
        else:
            settings = self.get_default_settings()
            self.save_settings(settings)
            return settings

    def get_default_settings(self):
        """Получение настроек по умолчанию"""
        return {
            'enabled': True,
            'block_invites': True,
            'block_urls': False,
            'allowed_channels': [],
            'ignored_roles': []
        }

    def save_settings(self, settings=None):
        """Сохранение настроек в файл"""
        if settings is None:
            settings = self.settings
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        # Игнорируем сообщения от ботов
        if message.author.bot:
            return

        # Проверяем, включен ли автомод
        if not self.settings['enabled']:
            return

        # Проверяем, является ли канал разрешенным
        if message.channel.id in self.settings['allowed_channels']:
            return

        # Проверяем, есть ли у пользователя игнорируемая роль
        for role in message.author.roles:
            if role.id in self.settings['ignored_roles']:
                return

        # Проверка на приглашения Discord
        if self.settings['block_invites']:
            if self.invite_pattern.search(message.content):
                await message.delete()
                try:
                    await message.author.send(
                        f"Пожалуйста, не отправляйте приглашения Discord в каналы клана. "
                        f"Ваше сообщение было удалено."
                    )
                except:
                    pass
                return

        # Проверка на URL
        if self.settings['block_urls']:
            if self.url_pattern.search(message.content):
                await message.delete()
                try:
                    await message.author.send(
                        f"Пожалуйста, не отправляйте ссылки в каналы клана. "
                        f"Ваше сообщение было удалено."
                    )
                except:
                    pass
                return

    @commands.slash_command(
        name="automod",
        description="Настройки автомодерации"
    )
    @commands.has_permissions(administrator=True)
    async def automod_settings(
        self,
        inter: disnake.ApplicationCommandInteraction,
        action: str = commands.Param(
            description="Действие",
            choices=["status", "toggle", "add_channel", "remove_channel", "add_role", "remove_role"]
        ),
        value: str = commands.Param(description="Значение (для toggle: on/off, для каналов и ролей: ID)", default=None)
    ):
        await inter.response.defer(ephemeral=True)

        if action == "status":
            embed = disnake.Embed(
                title="Статус автомодерации",
                color=disnake.Color.blue()
            )
            embed.add_field(
                name="Статус",
                value="Включен" if self.settings['enabled'] else "Выключен",
                inline=False
            )
            embed.add_field(
                name="Блокировка приглашений",
                value="Включена" if self.settings['block_invites'] else "Выключена",
                inline=False
            )
            embed.add_field(
                name="Блокировка URL",
                value="Включена" if self.settings['block_urls'] else "Выключена",
                inline=False
            )
            
            allowed_channels = [f"<#{channel_id}>" for channel_id in self.settings['allowed_channels']]
            embed.add_field(
                name="Разрешенные каналы",
                value=", ".join(allowed_channels) if allowed_channels else "Нет",
                inline=False
            )
            
            ignored_roles = [f"<@&{role_id}>" for role_id in self.settings['ignored_roles']]
            embed.add_field(
                name="Игнорируемые роли",
                value=", ".join(ignored_roles) if ignored_roles else "Нет",
                inline=False
            )
            
            await inter.edit_original_response(embed=embed)
            return

        if action == "toggle":
            if value not in ["on", "off"]:
                await inter.edit_original_response(content="Значение должно быть 'on' или 'off'")
                return
            
            self.settings['enabled'] = (value == "on")
            self.save_settings()
            await inter.edit_original_response(content=f"Автомодерация {'включена' if value == 'on' else 'выключена'}")
            return

        if action in ["add_channel", "remove_channel"]:
            try:
                channel_id = int(value)
                channel = inter.guild.get_channel(channel_id)
                if not channel:
                    await inter.edit_original_response(content="Канал не найден")
                    return

                if action == "add_channel":
                    if channel_id not in self.settings['allowed_channels']:
                        self.settings['allowed_channels'].append(channel_id)
                        self.save_settings()
                        await inter.edit_original_response(content=f"Канал {channel.mention} добавлен в список разрешенных")
                    else:
                        await inter.edit_original_response(content="Этот канал уже в списке разрешенных")
                else:
                    if channel_id in self.settings['allowed_channels']:
                        self.settings['allowed_channels'].remove(channel_id)
                        self.save_settings()
                        await inter.edit_original_response(content=f"Канал {channel.mention} удален из списка разрешенных")
                    else:
                        await inter.edit_original_response(content="Этот канал не был в списке разрешенных")
            except ValueError:
                await inter.edit_original_response(content="Неверный ID канала")
            return

        if action in ["add_role", "remove_role"]:
            try:
                role_id = int(value)
                role = inter.guild.get_role(role_id)
                if not role:
                    await inter.edit_original_response(content="Роль не найдена")
                    return

                if action == "add_role":
                    if role_id not in self.settings['ignored_roles']:
                        self.settings['ignored_roles'].append(role_id)
                        self.save_settings()
                        await inter.edit_original_response(content=f"Роль {role.mention} добавлена в список игнорируемых")
                    else:
                        await inter.edit_original_response(content="Эта роль уже в списке игнорируемых")
                else:
                    if role_id in self.settings['ignored_roles']:
                        self.settings['ignored_roles'].remove(role_id)
                        self.save_settings()
                        await inter.edit_original_response(content=f"Роль {role.mention} удалена из списка игнорируемых")
                    else:
                        await inter.edit_original_response(content="Эта роль не была в списке игнорируемых")
            except ValueError:
                await inter.edit_original_response(content="Неверный ID роли")
            return

    @commands.slash_command(
        name="automod_toggle",
        description="Включить/выключить блокировку приглашений или URL"
    )
    @commands.has_permissions(administrator=True)
    async def automod_toggle(
        self,
        inter: disnake.ApplicationCommandInteraction,
        feature: str = commands.Param(
            description="Функция",
            choices=["invites", "urls"]
        ),
        status: str = commands.Param(
            description="Статус",
            choices=["on", "off"]
        )
    ):
        await inter.response.defer(ephemeral=True)
        
        if feature == "invites":
            self.settings['block_invites'] = (status == "on")
            self.save_settings()
            await inter.edit_original_response(
                content=f"Блокировка приглашений {'включена' if status == 'on' else 'выключена'}"
            )
        else:
            self.settings['block_urls'] = (status == "on")
            self.save_settings()
            await inter.edit_original_response(
                content=f"Блокировка URL {'включена' if status == 'on' else 'выключена'}"
            )

def setup(bot):
    bot.add_cog(AutoMod(bot)) 