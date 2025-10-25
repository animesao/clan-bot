import disnake
from disnake.ext import commands
from main import clan_data, save_clan_data

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="announce",
        description="Создать объявление"
    )
    @commands.has_permissions(administrator=True)
    async def announce_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        title: str = commands.Param(description="Заголовок объявления"),
        content: str = commands.Param(description="Содержание объявления")
    ):
        if not clan_data['settings']['announcement_channel']:
            await inter.response.send_message('Канал для объявлений не настроен! Используйте команду `/setchannel`', ephemeral=True)
            return

        channel = self.bot.get_channel(clan_data['settings']['announcement_channel'])
        if not channel:
            await inter.response.send_message('Канал для объявлений не найден!', ephemeral=True)
            return

        embed = disnake.Embed(
            title=title,
            description=content,
            color=disnake.Color.blue()
        )
        embed.set_footer(text=f"Объявление от {inter.author.name}")
        
        await channel.send(embed=embed)
        await inter.response.send_message('Объявление отправлено!', ephemeral=True)

    @commands.slash_command(
        name="setchannel",
        description="Настроить канал"
    )
    @commands.has_permissions(administrator=True)
    async def setchannel_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel_type: str = commands.Param(
            description="Тип канала",
            choices=["welcome", "announcement", "log"]
        ),
        channel: disnake.TextChannel = commands.Param(description="Канал")
    ):
        if channel_type == "welcome":
            clan_data['settings']['welcome_channel'] = channel.id
        elif channel_type == "announcement":
            clan_data['settings']['announcement_channel'] = channel.id
        elif channel_type == "log":
            clan_data['settings']['log_channel'] = channel.id

        save_clan_data()
        await inter.response.send_message(f'Канал {channel.mention} установлен как {channel_type}!', ephemeral=True)

    @commands.slash_command(
        name="setrole",
        description="Настроить роль"
    )
    @commands.has_permissions(administrator=True)
    async def setrole_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        role_type: str = commands.Param(
            description="Тип роли",
            choices=["leader", "member", "applicant", "new_member", "officer"]
        ),
        role: disnake.Role = commands.Param(description="Роль")
    ):
        clan_data['roles'][role_type] = role.id
        save_clan_data()
        await inter.response.send_message(f'Роль {role.mention} установлена как {role_type}!', ephemeral=True)

    @commands.slash_command(
        name="settings",
        description="Просмотр текущих настроек"
    )
    @commands.has_permissions(administrator=True)
    async def settings_slash(self, inter: disnake.ApplicationCommandInteraction):
        embed = disnake.Embed(
            title="Настройки клана",
            color=disnake.Color.blue()
        )

        # Каналы
        channels = []
        if clan_data['settings']['welcome_channel']:
            channel = self.bot.get_channel(clan_data['settings']['welcome_channel'])
            channels.append(f"Приветственный: {channel.mention if channel else 'Не найден'}")
        if clan_data['settings']['announcement_channel']:
            channel = self.bot.get_channel(clan_data['settings']['announcement_channel'])
            channels.append(f"Объявлений: {channel.mention if channel else 'Не найден'}")
        if clan_data['settings']['log_channel']:
            channel = self.bot.get_channel(clan_data['settings']['log_channel'])
            channels.append(f"Логов: {channel.mention if channel else 'Не найден'}")

        embed.add_field(
            name="Каналы",
            value="\n".join(channels) if channels else "Не настроены",
            inline=False
        )

        # Роли
        roles = []
        for role_type, role_id in clan_data['roles'].items():
            role = inter.guild.get_role(role_id)
            roles.append(f"{role_type}: {role.mention if role else 'Не найдена'}")

        embed.add_field(
            name="Роли",
            value="\n".join(roles) if roles else "Не настроены",
            inline=False
        )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="clear",
        description="Очистить сообщения в канале"
    )
    @commands.has_permissions(administrator=True)
    async def clear_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        amount: int = commands.Param(description="Количество сообщений для удаления", min_value=1, max_value=100)
    ):
        await inter.response.defer(ephemeral=True)
        deleted = await inter.channel.purge(limit=amount)
        await inter.followup.send(f'Удалено {len(deleted)} сообщений!', ephemeral=True)

def setup(bot):
    bot.add_cog(Admin(bot)) 