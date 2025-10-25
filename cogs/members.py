import disnake
from disnake.ext import commands
from datetime import datetime
from main import clan_data, save_clan_data

class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="profile",
        description="Просмотр профиля участника"
    )
    async def profile_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, чей профиль нужно просмотреть", default=None)
    ):
        if member is None:
            member = inter.author

        embed = disnake.Embed(
            title=f"Профиль {member.name}",
            color=member.color if member.color != disnake.Color.default() else disnake.Color.blue()
        )

        # Основная информация
        embed.add_field(
            name="ID",
            value=str(member.id),
            inline=True
        )
        embed.add_field(
            name="Присоединился",
            value=member.joined_at.strftime("%d.%m.%Y %H:%M") if member.joined_at else "Неизвестно",
            inline=True
        )
        embed.add_field(
            name="Аккаунт создан",
            value=member.created_at.strftime("%d.%m.%Y %H:%M"),
            inline=True
        )

        # Роли пользователя
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        if roles:
            embed.add_field(
                name="Роли",
                value=", ".join(roles) if len(", ".join(roles)) < 1024 else "Слишком много ролей для отображения",
                inline=False
            )

        # Информация о клане
        if str(member.id) in clan_data['members']:
            member_data = clan_data['members'][str(member.id)]
            joined_at = datetime.fromisoformat(member_data['joined_at'])
            embed.add_field(
                name="Дата вступления в клан",
                value=joined_at.strftime("%d.%m.%Y %H:%M"),
                inline=False
            )

        # Предупреждения
        warnings = [w for w in clan_data['warnings'].values() if w['user_id'] == str(member.id)]
        if warnings:
            warnings_text = "\n".join([
                f"• {w['reason']} ({datetime.fromisoformat(w['timestamp']).strftime('%d.%m.%Y')}) [ID: {warning_id}]"
                for warning_id, w in clan_data['warnings'].items() if w['user_id'] == str(member.id)
            ])
            embed.add_field(
                name="Предупреждения",
                value=warnings_text,
                inline=False
            )

        # Статус
        status_emoji = {
            "online": "🟢",
            "idle": "🟡",
            "dnd": "🔴",
            "offline": "⚫"
        }
        embed.add_field(
            name="Статус",
            value=f"{status_emoji.get(str(member.status), '⚫')} {str(member.status).title()}",
            inline=True
        )

        # Аватар
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Футер
        embed.set_footer(text=f"Запросил: {inter.author.name}", icon_url=inter.author.display_avatar.url)

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="warn",
        description="Выдать предупреждение участнику"
    )
    @commands.has_permissions(administrator=True)
    async def warn_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, которому нужно выдать предупреждение"),
        reason: str = commands.Param(description="Причина предупреждения")
    ):
        if str(member.id) not in clan_data['members']:
            await inter.response.send_message('Этот пользователь не является участником клана!', ephemeral=True)
            return

        warning_id = str(len(clan_data['warnings']) + 1)
        clan_data['warnings'][warning_id] = {
            'user_id': str(member.id),
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'issued_by': str(inter.author.id)
        }
        save_clan_data()

        # Отправка уведомления в ЛС
        try:
            embed = disnake.Embed(
                title="Вы получили предупреждение",
                description=f"**Причина:** {reason}",
                color=disnake.Color.red()
            )
            await member.send(embed=embed)
        except:
            pass

        await inter.response.send_message(f'Предупреждение выдано {member.mention}!', ephemeral=True)

    @commands.slash_command(
        name="warnings",
        description="Просмотр предупреждений участника"
    )
    @commands.has_permissions(administrator=True)
    async def warnings_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, чьи предупреждения нужно просмотреть")
    ):
        warnings = [w for w in clan_data['warnings'].values() if w['user_id'] == str(member.id)]
        
        if not warnings:
            await inter.response.send_message(f'У {member.mention} нет предупреждений.', ephemeral=True)
            return

        embed = disnake.Embed(
            title=f"Предупреждения {member.name}",
            color=disnake.Color.orange()
        )
        
        for warning_id, warning in clan_data['warnings'].items():
            if warning['user_id'] == str(member.id):
                issued_by = await self.bot.fetch_user(int(warning['issued_by']))
                embed.add_field(
                    name=f"Предупреждение от {datetime.fromisoformat(warning['timestamp']).strftime('%d.%m.%Y %H:%M')} [ID: {warning_id}]",
                    value=f"**Причина:** {warning['reason']}\n"
                          f"**Выдал:** {issued_by.name}",
                    inline=False
                )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="kick",
        description="Исключить участника из клана и с сервера"
    )
    @commands.has_permissions(administrator=True)
    async def kick_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, которого нужно исключить"),
        reason: str = commands.Param(description="Причина исключения")
    ):
        if str(member.id) not in clan_data['members']:
            await inter.response.send_message('Этот пользователь не является участником клана!', ephemeral=True)
            return

        # Проверяем, не пытаемся ли мы кикнуть администратора
        if member.guild_permissions.administrator:
            await inter.response.send_message('Нельзя исключить администратора сервера!', ephemeral=True)
            return

        # Удаление всех ролей группировок
        for faction in clan_data['factions']['factions'].values():
            if faction['role_id']:
                role = inter.guild.get_role(faction['role_id'])
                if role and role in member.roles:
                    await member.remove_roles(role)

        # Удаление роли участника
        member_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['member'])
        if member_role and member_role in member.roles:
            await member.remove_roles(member_role)

        # Удаление из списка участников
        del clan_data['members'][str(member.id)]
        save_clan_data()

        # Отправка уведомления в ЛС
        try:
            embed = disnake.Embed(
                title="Вы были исключены из клана и с сервера",
                description=f"**Причина:** {reason}\n**Выдал:** {inter.author.name}",
                color=disnake.Color.red()
            )
            await member.send(embed=embed)
        except:
            pass

        # Кик с сервера
        await member.kick(reason=f"{reason} | Выдал: {inter.author.name}")

        # Отправка уведомления в канал объявлений
        if clan_data['settings']['announcement_channel']:
            channel = self.bot.get_channel(clan_data['settings']['announcement_channel'])
            if channel:
                embed = disnake.Embed(
                    title="Участник исключен из клана и с сервера",
                    description=f"{member.mention} был исключен из клана и с сервера.\n**Причина:** {reason}\n**Выдал:** {inter.author.mention}",
                    color=disnake.Color.red()
                )
                await channel.send(embed=embed)

        await inter.response.send_message(f'{member.mention} исключен из клана и с сервера!', ephemeral=True)

    @commands.slash_command(
        name="ban",
        description="Забанить участника"
    )
    @commands.has_permissions(administrator=True)
    async def ban_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, которого нужно забанить"),
        reason: str = commands.Param(description="Причина бана"),
        delete_messages: int = commands.Param(
            description="Количество дней сообщений для удаления (0-7)",
            default=0,
            min_value=0,
            max_value=30
        )
    ):
        if str(member.id) not in clan_data['members']:
            await inter.response.send_message('Этот пользователь не является участником клана!', ephemeral=True)
            return

        # Проверяем, не пытаемся ли мы забанить администратора
        if member.guild_permissions.administrator:
            await inter.response.send_message('Нельзя забанить администратора сервера!', ephemeral=True)
            return

        # Удаление всех ролей группировок
        for faction in clan_data['factions']['factions'].values():
            if faction['role_id']:
                role = inter.guild.get_role(faction['role_id'])
                if role and role in member.roles:
                    await member.remove_roles(role)

        # Удаление роли участника
        member_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['member'])
        if member_role and member_role in member.roles:
            await member.remove_roles(member_role)

        # Удаление из списка участников
        del clan_data['members'][str(member.id)]
        save_clan_data()

        # Отправка уведомления в ЛС перед баном
        try:
            embed = disnake.Embed(
                title="Вы были забанены",
                description=f"**Причина:** {reason}\n**Выдал:** {inter.author.name}",
                color=disnake.Color.dark_red()
            )
            await member.send(embed=embed)
        except:
            pass

        # Бан участника
        await member.ban(reason=f"{reason} | Выдал: {inter.author.name}", delete_message_days=delete_messages)

        # Отправка уведомления в канал объявлений
        if clan_data['settings']['announcement_channel']:
            channel = self.bot.get_channel(clan_data['settings']['announcement_channel'])
            if channel:
                embed = disnake.Embed(
                    title="Участник забанен",
                    description=f"{member.mention} был забанен.\n**Причина:** {reason}\n**Выдал:** {inter.author.mention}",
                    color=disnake.Color.dark_red()
                )
                await channel.send(embed=embed)

        await inter.response.send_message(f'{member.mention} забанен!', ephemeral=True)

    @commands.slash_command(
        name="deletewarn",
        description="Удалить предупреждение у участника"
    )
    async def delete_warn_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник, у которого нужно удалить предупреждение"),
        warning_id: str = commands.Param(description="ID предупреждения для удаления")
    ):
        # Проверяем, является ли пользователь лидером
        leader_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['leader'])
        if not leader_role or leader_role not in inter.author.roles:
            await inter.response.send_message('Только лидер может удалять предупреждения!', ephemeral=True)
            return

        if warning_id not in clan_data['warnings']:
            await inter.response.send_message('Предупреждение не найдено!', ephemeral=True)
            return

        warning = clan_data['warnings'][warning_id]
        if warning['user_id'] != str(member.id):
            await inter.response.send_message('Это предупреждение не принадлежит указанному участнику!', ephemeral=True)
            return

        # Удаляем предупреждение
        del clan_data['warnings'][warning_id]
        save_clan_data()

        # Отправляем уведомление в ЛС
        try:
            embed = disnake.Embed(
                title="Предупреждение удалено",
                description=f"Ваше предупреждение было удалено лидером клана.",
                color=disnake.Color.green()
            )
            await member.send(embed=embed)
        except:
            pass

        await inter.response.send_message(f'Предупреждение успешно удалено у {member.mention}!', ephemeral=True)

def setup(bot):
    bot.add_cog(Members(bot))