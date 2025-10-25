import disnake
from disnake.ext import commands
import json
from main import clan_data, save_clan_data

class Factions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="faction", description="Управление группировками")
    @commands.has_permissions(administrator=True)
    async def faction(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @faction.sub_command(name="setup", description="Настроить систему группировок")
    async def setup_faction(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(description="Канал для выбора группировок")
    ):
        try:
            if not clan_data['factions']['factions']:
                await inter.response.send_message("Сначала добавьте хотя бы одну группировку через команду `/faction add`!", ephemeral=True)
                return

            # Создаем embed с описанием группировок
            embed = disnake.Embed(
                title="Выбор группировки",
                description="Выберите свою группировку, нажав на соответствующую кнопку ниже:",
                color=disnake.Color.blue()
            )

            # Добавляем информацию о каждой группировке
            for faction_id, faction in clan_data['factions']['factions'].items():
                embed.add_field(
                    name=f"{faction['emoji']} {faction['name']}",
                    value=faction['description'] or "",
                    inline=False
                )

            # Создаем кнопки для каждой группировки
            components = []
            for faction_id, faction in clan_data['factions']['factions'].items():
                components.append(
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.primary,
                        label=faction['name'],
                        emoji=faction['emoji'],
                        custom_id=f"faction_{faction_id}"
                    )
                )

            # Создаем view с кнопками
            view = disnake.ui.View()
            for button in components:
                view.add_item(button)

            # Отправляем сообщение с embed и кнопками
            message = await channel.send(embed=embed, view=view)

            # Сохраняем настройки
            clan_data['factions']['enabled'] = True
            clan_data['factions']['message_id'] = message.id
            clan_data['factions']['channel_id'] = channel.id

            # Сохраняем данные
            save_clan_data()

            await inter.response.send_message("Система группировок успешно настроена!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Произошла ошибка при настройке системы: {str(e)}", ephemeral=True)

    @faction.sub_command(name="add", description="Добавить новую группировку")
    async def add_faction(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(description="Название группировки"),
        description: str = commands.Param(description="Описание группировки", default=""),
        emoji: str = commands.Param(description="Эмодзи группировки"),
        role: disnake.Role = commands.Param(description="Роль группировки"),
        color: str = commands.Param(description="Цвет группировки (hex код, например #FF0000)", default="#000000")
    ):
        try:
            # Создаем уникальный ID для группировки
            faction_id = name.lower().replace(" ", "_")
            
            # Проверяем, не существует ли уже группировка с таким ID
            if faction_id in clan_data['factions']['factions']:
                await inter.response.send_message("Группировка с таким названием уже существует!", ephemeral=True)
                return

            # Проверяем валидность hex-кода цвета
            if not color.startswith('#'):
                color = f"#{color}"
            
            # Добавляем группировку
            clan_data['factions']['factions'][faction_id] = {
                'name': name,
                'description': description,
                'emoji': emoji,
                'role_id': role.id,
                'color': color
            }

            # Сохраняем данные
            save_clan_data()

            await inter.response.send_message(f"Группировка {name} успешно добавлена!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Произошла ошибка при добавлении группировки: {str(e)}", ephemeral=True)

    @faction.sub_command(name="edit", description="Изменить существующую группировку")
    async def edit_faction(
        self,
        inter: disnake.ApplicationCommandInteraction,
        faction: str = commands.Param(description="ID группировки"),
        name: str = commands.Param(description="Новое название группировки", default=None),
        description: str = commands.Param(description="Новое описание группировки", default=None),
        emoji: str = commands.Param(description="Новый эмодзи группировки", default=None),
        role: disnake.Role = commands.Param(description="Новая роль группировки", default=None),
        color: str = commands.Param(description="Новый цвет группировки (hex код)", default=None)
    ):
        try:
            # Проверяем существование группировки
            if faction not in clan_data['factions']['factions']:
                await inter.response.send_message("Такой группировки не существует!", ephemeral=True)
                return

            faction_data = clan_data['factions']['factions'][faction]
            
            if name:
                faction_data['name'] = name
            if description is not None:  # Позволяем установить пустое описание
                faction_data['description'] = description
            if emoji:
                faction_data['emoji'] = emoji
            if role:
                faction_data['role_id'] = role.id
            if color:
                if not color.startswith('#'):
                    color = f"#{color}"
                faction_data['color'] = color

            # Сохраняем данные
            save_clan_data()

            await inter.response.send_message(f"Группировка успешно обновлена!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Произошла ошибка при обновлении группировки: {str(e)}", ephemeral=True)

    @faction.sub_command(name="remove", description="Удалить группировку")
    async def remove_faction(
        self,
        inter: disnake.ApplicationCommandInteraction,
        faction: str = commands.Param(description="ID группировки")
    ):
        try:
            # Проверяем существование группировки
            if faction not in clan_data['factions']['factions']:
                await inter.response.send_message("Такой группировки не существует!", ephemeral=True)
                return

            # Удаляем группировку
            del clan_data['factions']['factions'][faction]

            # Сохраняем данные
            save_clan_data()

            await inter.response.send_message(f"Группировка успешно удалена!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Произошла ошибка при удалении группировки: {str(e)}", ephemeral=True)

    @faction.sub_command(name="list", description="Показать список всех группировок")
    async def list_factions(self, inter: disnake.ApplicationCommandInteraction):
        try:
            if not clan_data['factions']['factions']:
                await inter.response.send_message("Нет добавленных группировок!", ephemeral=True)
                return

            embed = disnake.Embed(
                title="Список группировок",
                color=disnake.Color.blue()
            )

            for faction_id, faction in clan_data['factions']['factions'].items():
                role = inter.guild.get_role(faction['role_id'])
                role_name = role.name if role else "Роль не найдена"
                
                embed.add_field(
                    name=f"{faction['emoji']} {faction['name']} (ID: {faction_id})",
                    value=f"Описание: {faction['description'] or 'Нет описания'}\nРоль: {role_name}",
                    inline=False
                )

            await inter.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Произошла ошибка при получении списка группировок: {str(e)}", ephemeral=True)

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        try:
            if not inter.component.custom_id.startswith("faction_"):
                return

            if not clan_data['factions']['enabled']:
                await inter.response.send_message("Система группировок отключена.", ephemeral=True)
                return

            faction_id = inter.component.custom_id.split("_")[1]
            if faction_id not in clan_data['factions']['factions']:
                await inter.response.send_message("Эта группировка больше не существует.", ephemeral=True)
                return

            faction = clan_data['factions']['factions'][faction_id]

            if not faction['role_id']:
                await inter.response.send_message("Роль для этой группировки не настроена.", ephemeral=True)
                return

            # Проверяем, есть ли уже у пользователя роль этой группировки
            role = inter.guild.get_role(faction['role_id'])
            if role and role in inter.author.roles:
                await inter.response.send_message("Вы уже состоите в этой группировке!", ephemeral=True)
                return

            # Удаляем все роли группировок
            for other_faction in clan_data['factions']['factions'].values():
                if other_faction['role_id']:
                    role = inter.guild.get_role(other_faction['role_id'])
                    if role and role in inter.author.roles:
                        await inter.author.remove_roles(role)

            # Выдаем новую роль
            role = inter.guild.get_role(faction['role_id'])
            if role:
                await inter.author.add_roles(role)
                await inter.response.send_message(f"Вы успешно присоединились к группировке {faction['name']}!", ephemeral=True)
            else:
                await inter.response.send_message("Произошла ошибка при выдаче роли.", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Произошла ошибка при выборе группировки: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(Factions(bot)) 