import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
from main import clan_data, save_clan_data

class Subclans(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="createsubclan",
        description="Создать подразделение клана"
    )
    async def create_subclan_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(description="Название подразделения"),
        description: str = commands.Param(description="Описание подразделения"),
        max_members: int = commands.Param(description="Максимальное количество участников", default=50)
    ):
        # Отправляем отложенный ответ
        await inter.response.defer(ephemeral=True)

        # Проверяем кулдаун
        can_create, remaining_time = self.check_cooldown(str(inter.author.id))
        if not can_create:
            await inter.edit_original_response(content=f'Вы не можете создать подразделение еще {remaining_time}!')
            return

        # Проверяем, не состоит ли пользователь в другом подразделении
        for subclan_name, subclan in clan_data.get('subclans', {}).items():
            if str(inter.author.id) in subclan['members']:
                await inter.edit_original_response(content=f'Вы уже состоите в подразделении {subclan_name}! Сначала выйдите из него.')
                return

        # Проверяем, не создал ли уже пользователь подразделение
        for subclan in clan_data.get('subclans', {}).values():
            if str(inter.author.id) == subclan['created_by']:
                await inter.edit_original_response(content='Вы уже создали подразделение! Один человек может создать только одно подразделение.')
                return

        # Проверяем наличие роли офицера
        if 'roles' not in clan_data:
            clan_data['roles'] = {}
            
        if 'officer' not in clan_data['roles']:
            await inter.edit_original_response(content='Роль офицера не настроена! Используйте команду /setrole для настройки роли офицера.')
            return

        officer_role = inter.guild.get_role(clan_data['roles']['officer'])
        
        if not officer_role:
            await inter.edit_original_response(content='Роль офицера не найдена на сервере! Используйте команду /setrole для настройки роли офицера.')
            return

        # Проверяем, есть ли у пользователя роль офицера
        if officer_role not in inter.author.roles:
            await inter.edit_original_response(content='У вас нет прав для создания подразделения! Требуется роль офицера.')
            return

        # Проверяем, не существует ли уже подразделение с таким названием
        if name in clan_data.get('subclans', {}):
            await inter.edit_original_response(content='Подразделение с таким названием уже существует!')
            return

        try:
            # Создаем категорию для подразделения
            category = await inter.guild.create_category(name=f"📌 {name}")
            
            # Создаем каналы в категории
            general_channel = await category.create_text_channel("общий")
            announcements_channel = await category.create_text_channel("объявления")
            voice_channel = await category.create_voice_channel("голосовой")

            # Создаем роли для подразделения
            leader_role = await inter.guild.create_role(
                name=f"{name} | Лидер",
                color=disnake.Color.gold(),
                reason=f"Создание подразделения {name}"
            )
            officer_role = await inter.guild.create_role(
                name=f"{name} | Офицер",
                color=disnake.Color.blue(),
                reason=f"Создание подразделения {name}"
            )
            member_role = await inter.guild.create_role(
                name=f"{name} | Участник",
                color=disnake.Color.green(),
                reason=f"Создание подразделения {name}"
            )

            # Выдаем роль лидера создателю
            await inter.author.add_roles(leader_role)

            # Настраиваем права доступа для каналов
            for channel in [general_channel, announcements_channel, voice_channel]:
                await channel.set_permissions(inter.guild.default_role, read_messages=False)
                await channel.set_permissions(member_role, read_messages=True, send_messages=True)
                await channel.set_permissions(officer_role, read_messages=True, send_messages=True, manage_messages=True)
                await channel.set_permissions(leader_role, read_messages=True, send_messages=True, manage_messages=True, manage_channels=True)

            # Сохраняем информацию о подразделении
            if 'subclans' not in clan_data:
                clan_data['subclans'] = {}

            clan_data['subclans'][name] = {
                'description': description,
                'created_at': datetime.now().isoformat(),
                'created_by': str(inter.author.id),
                'max_members': max_members,
                'members': [str(inter.author.id)],
                'channels': {
                    'category': category.id,
                    'general': general_channel.id,
                    'announcements': announcements_channel.id,
                    'voice': voice_channel.id
                },
                'roles': {
                    'leader': leader_role.id,
                    'officer': officer_role.id,
                    'member': member_role.id
                }
            }
            save_clan_data()

            # Отправляем сообщение об успешном создании
            embed = disnake.Embed(
                title="Подразделение создано!",
                description=f"**Название:** {name}\n"
                           f"**Описание:** {description}\n"
                           f"**Максимум участников:** {max_members}\n"
                           f"**Лидер:** {inter.author.mention}",
                color=disnake.Color.green()
            )
            await announcements_channel.send(embed=embed)
            await inter.edit_original_response(content=f'Подразделение "{name}" успешно создано!')

        except Exception as e:
            # В случае ошибки пытаемся удалить созданные объекты
            try:
                if 'category' in locals():
                    await category.delete()
                if 'leader_role' in locals():
                    await leader_role.delete()
                if 'officer_role' in locals():
                    await officer_role.delete()
                if 'member_role' in locals():
                    await member_role.delete()
            except:
                pass

            await inter.edit_original_response(content=f'Произошла ошибка при создании подразделения: {str(e)}')

    @commands.slash_command(
        name="subclaninvite",
        description="Пригласить участника в подразделение"
    )
    async def invite_to_subclan_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник для приглашения"),
        subclan_name: str = commands.Param(description="Название подразделения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем права
        leader_role = inter.guild.get_role(subclan['roles']['leader'])
        officer_role = inter.guild.get_role(subclan['roles']['officer'])
        
        if not (leader_role in inter.author.roles or officer_role in inter.author.roles):
            await inter.response.send_message('У вас нет прав для приглашения участников!', ephemeral=True)
            return

        # Проверяем количество участников
        if len(subclan['members']) >= subclan['max_members']:
            await inter.response.send_message('Достигнут лимит участников подразделения!', ephemeral=True)
            return

        # Проверяем, не состоит ли уже участник в подразделении
        if str(member.id) in subclan['members']:
            await inter.response.send_message('Этот участник уже состоит в подразделении!', ephemeral=True)
            return

        # Проверяем, не состоит ли участник в другом подразделении
        for other_subclan_name, other_subclan in clan_data.get('subclans', {}).items():
            if other_subclan_name != subclan_name and str(member.id) in other_subclan['members']:
                await inter.response.send_message(f'Этот участник уже состоит в подразделении {other_subclan_name}! Сначала он должен выйти из него.', ephemeral=True)
                return

        # Добавляем участника
        member_role = inter.guild.get_role(subclan['roles']['member'])
        await member.add_roles(member_role)
        subclan['members'].append(str(member.id))
        save_clan_data()

        # Отправляем уведомления
        announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
        if announcements_channel:
            embed = disnake.Embed(
                title="Новый участник подразделения!",
                description=f"{member.mention} присоединился к подразделению!",
                color=disnake.Color.green()
            )
            await announcements_channel.send(embed=embed)

        try:
            embed = disnake.Embed(
                title=f"Приглашение в подразделение {subclan_name}",
                description=f"Вы были приглашены в подразделение {subclan_name}!\n"
                           f"Описание: {subclan['description']}",
                color=disnake.Color.blue()
            )
            await member.send(embed=embed)
        except:
            pass

        await inter.response.send_message(f'{member.mention} приглашен в подразделение!', ephemeral=True)

    @commands.slash_command(
        name="subclankick",
        description="Исключить участника из подразделения"
    )
    async def kick_from_subclan_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник для исключения"),
        subclan_name: str = commands.Param(description="Название подразделения"),
        reason: str = commands.Param(description="Причина исключения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем права
        leader_role = inter.guild.get_role(subclan['roles']['leader'])
        officer_role = inter.guild.get_role(subclan['roles']['officer'])
        
        if not (leader_role in inter.author.roles or officer_role in inter.author.roles):
            await inter.response.send_message('У вас нет прав для исключения участников!', ephemeral=True)
            return

        # Проверяем, состоит ли участник в подразделении
        if str(member.id) not in subclan['members']:
            await inter.response.send_message('Этот участник не состоит в подразделении!', ephemeral=True)
            return

        # Удаляем роли
        for role_id in subclan['roles'].values():
            role = inter.guild.get_role(role_id)
            if role and role in member.roles:
                await member.remove_roles(role)

        # Удаляем из списка участников
        subclan['members'].remove(str(member.id))
        save_clan_data()

        # Отправляем уведомления
        announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
        if announcements_channel:
            embed = disnake.Embed(
                title="Участник исключен из подразделения",
                description=f"{member.mention} был исключен из подразделения.\nПричина: {reason}",
                color=disnake.Color.red()
            )
            await announcements_channel.send(embed=embed)

        try:
            embed = disnake.Embed(
                title=f"Исключение из подразделения {subclan_name}",
                description=f"Вы были исключены из подразделения {subclan_name}.\nПричина: {reason}",
                color=disnake.Color.red()
            )
            await member.send(embed=embed)
        except:
            pass

        await inter.response.send_message(f'{member.mention} исключен из подразделения!', ephemeral=True)

    @commands.slash_command(
        name="subclaninfo",
        description="Информация о подразделении"
    )
    async def subclan_info_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        created_at = datetime.fromisoformat(subclan['created_at'])
        leader = await self.bot.fetch_user(int(subclan['created_by']))

        embed = disnake.Embed(
            title=f"Информация о подразделении {subclan_name}",
            description=subclan['description'],
            color=disnake.Color.blue()
        )

        embed.add_field(
            name="Лидер",
            value=leader.mention,
            inline=True
        )
        embed.add_field(
            name="Создано",
            value=created_at.strftime("%d.%m.%Y %H:%M"),
            inline=True
        )
        embed.add_field(
            name="Участников",
            value=f"{len(subclan['members'])}/{subclan['max_members']}",
            inline=True
        )

        # Список участников
        members_list = []
        for member_id in subclan['members']:
            try:
                member = await self.bot.fetch_user(int(member_id))
                member_obj = inter.guild.get_member(int(member_id))
                if member_obj:
                    display_role_name = "Участник" # Default if no specific role found

                    # Collect all relevant subclan roles (by object, not just ID)
                    subclan_roles_objects = {}
                    # Add main roles
                    for role_type, role_id in subclan['roles'].items():
                        role = inter.guild.get_role(role_id)
                        if role:
                            subclan_roles_objects[role_type] = role

                    # Add custom roles
                    if 'custom_roles' in subclan:
                        for custom_role_name, custom_role_data in subclan['custom_roles'].items():
                             role = inter.guild.get_role(custom_role_data['id'])
                             if role:
                                subclan_roles_objects[custom_role_name] = role

                    # Find the highest role the member has from the subclan roles
                    highest_subclan_role = None
                    for role in member_obj.roles:
                         if role.id in [r.id for r in subclan_roles_objects.values()]:
                             # This role is one of the subclan's roles
                             if highest_subclan_role is None or role > highest_subclan_role:
                                 highest_subclan_role = role

                    if highest_subclan_role:
                         # Use the mention for the highest role found
                         display_role_name = highest_subclan_role.mention
                    elif str(member.id) == subclan['created_by']:
                        # Special case: Ensure leader is shown even if role object lookup fails (shouldn't happen)
                        leader_role = inter.guild.get_role(subclan['roles']['leader'])
                        if leader_role:
                             display_role_name = leader_role.mention
                        else:
                             display_role_name = "Лидер"

                    members_list.append(f"{member.name} ({display_role_name})")
            except Exception as e:
                print(f"Error fetching member or roles for {member_id}: {e}")
                # If an error occurs for a member, still try to list them without role
                try:
                    basic_member = await self.bot.fetch_user(int(member_id))
                    members_list.append(f"{basic_member.name} (Не удалось определить роль)")
                except:
                    members_list.append(f"Unknown User (Не удалось определить роль)")
                continue

        if members_list:
            embed.add_field(
                name="Участники",
                value="\n".join(members_list),
                inline=False
            )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="subclans",
        description="Список всех подразделений"
    )
    async def list_subclans_slash(self, inter: disnake.ApplicationCommandInteraction):
        if not clan_data.get('subclans'):
            await inter.response.send_message('Нет созданных подразделений!', ephemeral=True)
            return

        embed = disnake.Embed(
            title="Список подразделений",
            color=disnake.Color.blue()
        )

        for name, subclan in clan_data['subclans'].items():
            created_at = datetime.fromisoformat(subclan['created_at'])
            leader = await self.bot.fetch_user(int(subclan['created_by']))
            
            embed.add_field(
                name=name,
                value=f"**Описание:** {subclan['description']}\n"
                      f"**Лидер:** {leader.mention}\n"
                      f"**Участников:** {len(subclan['members'])}/{subclan['max_members']}\n"
                      f"**Создано:** {created_at.strftime('%d.%m.%Y')}",
                inline=False
            )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="subclanapply",
        description="Подать заявку на вступление в подразделение"
    )
    async def apply_to_subclan_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        reason: str = commands.Param(description="Причина вступления")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        # Проверяем кулдаун
        can_join, remaining_time = self.check_cooldown(str(inter.author.id))
        if not can_join:
            await inter.response.send_message(f'Вы не можете присоединиться к подразделению еще {remaining_time}!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, не состоит ли уже участник в подразделении
        if str(inter.author.id) in subclan['members']:
            await inter.response.send_message('Вы уже состоите в этом подразделении!', ephemeral=True)
            return

        # Проверяем, не состоит ли участник в другом подразделении
        for other_subclan_name, other_subclan in clan_data.get('subclans', {}).items():
            if other_subclan_name != subclan_name and str(inter.author.id) in other_subclan['members']:
                await inter.response.send_message(f'Вы уже состоите в подразделении {other_subclan_name}! Сначала выйдите из него.', ephemeral=True)
                return

        # Проверяем, не создал ли пользователь другое подразделение
        for other_subclan_name, other_subclan in clan_data.get('subclans', {}).items():
            if str(inter.author.id) == other_subclan['created_by']:
                await inter.response.send_message(f'Вы не можете вступить в подразделение, так как являетесь лидером подразделения {other_subclan_name}!', ephemeral=True)
                return

        # Проверяем количество участников
        if len(subclan['members']) >= subclan['max_members']:
            await inter.response.send_message('Достигнут лимит участников подразделения!', ephemeral=True)
            return

        # Создаем заявку
        if 'applications' not in subclan:
            subclan['applications'] = {}

        application_id = str(inter.author.id)
        subclan['applications'][application_id] = {
            'user_id': str(inter.author.id),
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        save_clan_data()

        # Отправляем уведомление лидеру и офицерам
        leader = await self.bot.fetch_user(int(subclan['created_by']))
        leader_role = inter.guild.get_role(subclan['roles']['leader'])
        officer_role = inter.guild.get_role(subclan['roles']['officer'])

        embed = disnake.Embed(
            title="Новая заявка на вступление",
            description=f"**Участник:** {inter.author.mention}\n"
                       f"**Причина:** {reason}",
            color=disnake.Color.blue()
        )
        embed.set_footer(text="Используйте /subclanaccept или /subclanreject для ответа на заявку")

        # Отправляем в канал объявлений
        announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
        if announcements_channel:
            await announcements_channel.send(
                content=f"{leader_role.mention} {officer_role.mention}",
                embed=embed
            )

        await inter.response.send_message('Ваша заявка отправлена! Ожидайте ответа от лидера или офицера.', ephemeral=True)

    @commands.slash_command(
        name="subclanaccept",
        description="Принять заявку на вступление в подразделение"
    )
    async def accept_subclan_application_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        user: disnake.Member = commands.Param(description="Участник, чью заявку принимаем")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем права
        leader_role = inter.guild.get_role(subclan['roles']['leader'])
        officer_role = inter.guild.get_role(subclan['roles']['officer'])
        
        if not (leader_role in inter.author.roles or officer_role in inter.author.roles):
            await inter.response.send_message('У вас нет прав для принятия заявок! Требуется роль лидера или офицера подразделения.', ephemeral=True)
            return

        # Проверяем наличие заявки
        if 'applications' not in subclan or str(user.id) not in subclan['applications']:
            await inter.response.send_message('Заявка от этого участника не найдена!', ephemeral=True)
            return

        # Проверяем количество участников
        if len(subclan['members']) >= subclan['max_members']:
            await inter.response.send_message('Достигнут лимит участников подразделения!', ephemeral=True)
            return

        # Проверяем, не состоит ли участник в другом подразделении
        for other_subclan_name, other_subclan in clan_data.get('subclans', {}).items():
            if other_subclan_name != subclan_name and str(user.id) in other_subclan['members']:
                await inter.response.send_message(f'Этот участник уже состоит в подразделении {other_subclan_name}! Сначала он должен выйти из него.', ephemeral=True)
                return

        # Добавляем участника
        member_role = inter.guild.get_role(subclan['roles']['member'])
        await user.add_roles(member_role)
        subclan['members'].append(str(user.id))
        
        # Удаляем заявку
        del subclan['applications'][str(user.id)]
        save_clan_data()

        # Отправляем уведомления
        announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
        if announcements_channel:
            embed = disnake.Embed(
                title="Заявка принята!",
                description=f"{user.mention} принят в подразделение!",
                color=disnake.Color.green()
            )
            await announcements_channel.send(embed=embed)

        try:
            embed = disnake.Embed(
                title=f"Заявка в подразделение {subclan_name} принята!",
                description=f"Ваша заявка на вступление в подразделение {subclan_name} была принята!",
                color=disnake.Color.green()
            )
            await user.send(embed=embed)
        except:
            pass

        await inter.response.send_message(f'Заявка от {user.mention} принята!', ephemeral=True)

    @commands.slash_command(
        name="subclanreject",
        description="Отклонить заявку на вступление в подразделение"
    )
    async def reject_subclan_application_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        user: disnake.Member = commands.Param(description="Участник, чью заявку отклоняем"),
        reason: str = commands.Param(description="Причина отклонения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем права
        leader_role = inter.guild.get_role(subclan['roles']['leader'])
        officer_role = inter.guild.get_role(subclan['roles']['officer'])
        
        if not (leader_role in inter.author.roles or officer_role in inter.author.roles):
            await inter.response.send_message('У вас нет прав для отклонения заявок!', ephemeral=True)
            return

        # Проверяем наличие заявки
        if 'applications' not in subclan or str(user.id) not in subclan['applications']:
            await inter.response.send_message('Заявка от этого участника не найдена!', ephemeral=True)
            return

        # Удаляем заявку
        del subclan['applications'][str(user.id)]
        save_clan_data()

        # Отправляем уведомления
        announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
        if announcements_channel:
            embed = disnake.Embed(
                title="Заявка отклонена",
                description=f"Заявка от {user.mention} отклонена.\nПричина: {reason}",
                color=disnake.Color.red()
            )
            await announcements_channel.send(embed=embed)

        try:
            embed = disnake.Embed(
                title=f"Заявка в подразделение {subclan_name} отклонена",
                description=f"Ваша заявка на вступление в подразделение {subclan_name} была отклонена.\nПричина: {reason}",
                color=disnake.Color.red()
            )
            await user.send(embed=embed)
        except:
            pass

        await inter.response.send_message(f'Заявка от {user.mention} отклонена!', ephemeral=True)

    @commands.slash_command(
        name="subclandelete",
        description="Удалить подразделение"
    )
    async def delete_subclan_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения")
    ):
        # Отправляем отложенный ответ
        await inter.response.defer(ephemeral=True)

        if subclan_name not in clan_data.get('subclans', {}):
            await inter.edit_original_response(content='Подразделение не найдено!')
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.edit_original_response(content='Вы можете удалить только своё подразделение!')
            return

        # Создаем кнопки подтверждения
        confirm_button = disnake.ui.Button(
            style=disnake.ButtonStyle.danger,
            label="Подтвердить",
            custom_id="confirm_delete"
        )
        cancel_button = disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label="Отмена",
            custom_id="cancel_delete"
        )

        # Создаем компонент с кнопками
        components = disnake.ui.ActionRow(confirm_button, cancel_button)

        # Отправляем сообщение с кнопками
        message = await inter.edit_original_response(
            content=f"Вы уверены, что хотите удалить подразделение '{subclan_name}'?\n"
                   "Это действие нельзя отменить!",
            components=[components]
        )

        # Ждем нажатия кнопки
        try:
            interaction = await self.bot.wait_for(
                "button_click",
                check=lambda i: i.author == inter.author and i.message.id == message.id,
                timeout=30.0
            )
        except:
            await inter.edit_original_response(
                content="Время ожидания истекло. Удаление отменено.",
                components=[]
            )
            return

        # Проверяем, какая кнопка была нажата
        if interaction.data.custom_id == "cancel_delete":
            await interaction.response.edit_message(
                content="Удаление подразделения отменено.",
                components=[]
            )
            return

        # Если подтверждено, удаляем подразделение
        await interaction.response.edit_message(
            content="Удаление подразделения...",
            components=[]
        )

        try:
            # Удаляем роли
            all_subclan_role_ids = list(subclan['roles'].values())
            if 'custom_roles' in subclan:
                for custom_role_data in subclan['custom_roles'].values():
                    all_subclan_role_ids.append(custom_role_data['id'])

            for role_id in all_subclan_role_ids:
                role = inter.guild.get_role(role_id)
                if role:
                    try:
                        await role.delete(reason=f"Удаление подразделения {subclan_name}")
                    except Exception as e:
                        print(f"Ошибка при удалении роли {role.name}: {str(e)}")

            # Удаляем все каналы подразделения
            channels_to_delete = []

            # Добавляем основные каналы
            for channel_id in subclan['channels'].values():
                channel = inter.guild.get_channel(channel_id)
                if channel:
                    channels_to_delete.append(channel)

            # Добавляем дополнительные каналы
            if 'additional_channels' in subclan:
                for channel_id in subclan['additional_channels'].keys():
                    channel = inter.guild.get_channel(int(channel_id))
                    if channel:
                        channels_to_delete.append(channel)

            # Удаляем все каналы
            for channel in channels_to_delete:
                try:
                    await channel.delete(reason=f"Удаление подразделения {subclan_name}")
                except Exception as e:
                    print(f"Ошибка при удалении канала {channel.name}: {str(e)}")

            # Удаляем категорию
            category = inter.guild.get_channel(subclan['channels']['category'])
            if category:
                try:
                    await category.delete(reason=f"Удаление подразделения {subclan_name}")
                except Exception as e:
                    print(f"Ошибка при удалении категории {category.name}: {str(e)}")

            # Удаляем из данных
            del clan_data['subclans'][subclan_name]
            save_clan_data()

            # Отправляем финальное сообщение через новый ответ
            await interaction.followup.send(
                content=f'Подразделение "{subclan_name}" успешно удалено!',
                ephemeral=True
            )

        except Exception as e:
            error_message = f'Произошла ошибка при удалении подразделения: {str(e)}'
            print(error_message)  # Логируем ошибку
            try:
                await interaction.followup.send(
                    content=error_message,
                    ephemeral=True
                )
            except:
                # Если не удалось отправить сообщение через followup, пробуем через edit
                try:
                    await interaction.edit_original_response(
                        content=error_message,
                        components=[]
                    )
                except:
                    # Если и это не удалось, отправляем новое сообщение
                    await inter.followup.send(
                        content=error_message,
                        ephemeral=True
                    )

    @commands.slash_command(
        name="subclanapplications",
        description="Просмотр заявок на вступление в подразделение"
    )
    async def view_subclan_applications_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем права
        leader_role = inter.guild.get_role(subclan['roles']['leader'])
        officer_role = inter.guild.get_role(subclan['roles']['officer'])
        
        if not (leader_role in inter.author.roles or officer_role in inter.author.roles):
            await inter.response.send_message('У вас нет прав для просмотра заявок! Требуется роль лидера или офицера подразделения.', ephemeral=True)
            return

        if 'applications' not in subclan or not subclan['applications']:
            await inter.response.send_message('Нет активных заявок!', ephemeral=True)
            return

        embed = disnake.Embed(
            title=f"Заявки на вступление в {subclan_name}",
            color=disnake.Color.blue()
        )

        for user_id, application in subclan['applications'].items():
            user = await self.bot.fetch_user(int(user_id))
            timestamp = datetime.fromisoformat(application['timestamp'])
            
            embed.add_field(
                name=f"Заявка от {user.name}",
                value=f"**Причина:** {application['reason']}\n"
                      f"**Подана:** {timestamp.strftime('%d.%m.%Y %H:%M')}\n"
                      f"**Статус:** {application['status']}",
                inline=False
            )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="subclanpromote",
        description="Повысить участника до офицера подразделения"
    )
    async def promote_to_officer_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        member: disnake.Member = commands.Param(description="Участник для повышения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может повышать участников!', ephemeral=True)
            return

        # Проверяем, состоит ли участник в подразделении
        if str(member.id) not in subclan['members']:
            await inter.response.send_message('Этот участник не состоит в подразделении!', ephemeral=True)
            return

        # Проверяем, не является ли участник уже офицером
        officer_role = inter.guild.get_role(subclan['roles']['officer'])
        if officer_role in member.roles:
            await inter.response.send_message('Этот участник уже является офицером!', ephemeral=True)
            return

        # Выдаем роль офицера
        await member.add_roles(officer_role)
        
        # Отправляем уведомления
        announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
        if announcements_channel:
            embed = disnake.Embed(
                title="Новый офицер подразделения!",
                description=f"{member.mention} повышен до офицера подразделения!",
                color=disnake.Color.blue()
            )
            await announcements_channel.send(embed=embed)

        try:
            embed = disnake.Embed(
                title=f"Повышение в подразделении {subclan_name}",
                description=f"Вы были повышены до офицера в подразделении {subclan_name}!",
                color=disnake.Color.blue()
            )
            await member.send(embed=embed)
        except:
            pass

        await inter.response.send_message(f'{member.mention} повышен до офицера!', ephemeral=True)

    @commands.slash_command(
        name="subclandemote",
        description="Понизить офицера до участника подразделения"
    )
    async def demote_officer_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        member: disnake.Member = commands.Param(description="Офицер для понижения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может понижать офицеров!', ephemeral=True)
            return

        # Проверяем, является ли участник офицером
        officer_role = inter.guild.get_role(subclan['roles']['officer'])
        if officer_role not in member.roles:
            await inter.response.send_message('Этот участник не является офицером!', ephemeral=True)
            return

        # Удаляем роль офицера
        await member.remove_roles(officer_role)
        
        # Отправляем уведомления
        announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
        if announcements_channel:
            embed = disnake.Embed(
                title="Офицер понижен",
                description=f"{member.mention} понижен до участника подразделения.",
                color=disnake.Color.orange()
            )
            await announcements_channel.send(embed=embed)

        try:
            embed = disnake.Embed(
                title=f"Понижение в подразделении {subclan_name}",
                description=f"Вы были понижены до участника в подразделении {subclan_name}.",
                color=disnake.Color.orange()
            )
            await member.send(embed=embed)
        except:
            pass

        await inter.response.send_message(f'{member.mention} понижен до участника!', ephemeral=True)

    @commands.slash_command(
        name="subclanofficers",
        description="Список офицеров подразделения"
    )
    async def list_officers_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        officer_role = inter.guild.get_role(subclan['roles']['officer'])
        
        if not officer_role:
            await inter.response.send_message('Роль офицера не найдена!', ephemeral=True)
            return

        # Получаем список офицеров
        officers = []
        for member in officer_role.members:
            officers.append(f"{member.mention}")

        if not officers:
            await inter.response.send_message('В подразделении нет офицеров!', ephemeral=True)
            return

        embed = disnake.Embed(
            title=f"Офицеры подразделения {subclan_name}",
            description="\n".join(officers),
            color=disnake.Color.blue()
        )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="subclanaddrole",
        description="Добавить новую роль в подразделение"
    )
    async def add_subclan_role_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        role_name: str = commands.Param(description="Название новой роли"),
        color: str = commands.Param(description="Цвет роли (hex код, например #FF0000)", default="#000000")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может добавлять роли в подразделение!', ephemeral=True)
            return

        try:
            # Создаем новую роль
            new_role = await inter.guild.create_role(
                name=f"{subclan_name} | {role_name}",
                color=disnake.Color(int(color.replace('#', ''), 16)),
                reason=f"Добавление роли в подразделение {subclan_name}"
            )

            # Добавляем роль в настройки подразделения
            if 'custom_roles' not in subclan:
                subclan['custom_roles'] = {}
            
            subclan['custom_roles'][role_name] = {
                'id': new_role.id,
                'name': role_name,
                'color': color
            }
            save_clan_data()

            # Настраиваем права доступа для каналов
            for channel_id in subclan['channels'].values():
                channel = inter.guild.get_channel(channel_id)
                if channel:
                    await channel.set_permissions(new_role, read_messages=True, send_messages=True)

            await inter.response.send_message(f'Роль {new_role.mention} успешно добавлена в подразделение!', ephemeral=True)

        except Exception as e:
            await inter.response.send_message(f'Произошла ошибка при создании роли: {str(e)}', ephemeral=True)

    @commands.slash_command(
        name="subclaneditrole",
        description="Изменить роль в подразделении"
    )
    async def edit_subclan_role_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        role_name: str = commands.Param(description="Название роли для изменения"),
        new_name: str = commands.Param(description="Новое название роли", default=None),
        new_color: str = commands.Param(description="Новый цвет роли (hex код)", default=None)
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может изменять роли в подразделении!', ephemeral=True)
            return

        # Проверяем существование роли
        if 'custom_roles' not in subclan or role_name not in subclan['custom_roles']:
            await inter.response.send_message('Роль не найдена в подразделении!', ephemeral=True)
            return

        try:
            role = inter.guild.get_role(subclan['custom_roles'][role_name]['id'])
            if not role:
                await inter.response.send_message('Роль не найдена на сервере!', ephemeral=True)
                return

            # Обновляем роль
            if new_name:
                await role.edit(name=f"{subclan_name} | {new_name}")
                subclan['custom_roles'][role_name]['name'] = new_name
            if new_color:
                await role.edit(color=disnake.Color.from_str(new_color))
                subclan['custom_roles'][role_name]['color'] = new_color

            save_clan_data()
            await inter.response.send_message(f'Роль {role.mention} успешно обновлена!', ephemeral=True)

        except Exception as e:
            await inter.response.send_message(f'Произошла ошибка при изменении роли: {str(e)}', ephemeral=True)

    @commands.slash_command(
        name="subclanremoverole",
        description="Убрать роль у участника подразделения"
    )
    async def remove_role_from_member_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        member: disnake.Member = commands.Param(description="Участник, у которого нужно убрать роль"),
        role: disnake.Role = commands.Param(description="Роль для удаления у участника")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может убирать роли!', ephemeral=True)
            return

        # Проверяем, состоит ли участник в подразделении
        if str(member.id) not in subclan['members']:
            await inter.response.send_message('Этот участник не состоит в подразделении!', ephemeral=True)
            return

        # Проверяем существование переданной роли среди ролей подразделения
        target_role = None
        
        # Получаем все ID ролей подразделения (основные и кастомные)
        subclan_role_ids = []
        subclan_roles_map = {} # Для быстрого доступа к объектам ролей по ID
        for role_type, role_id in subclan['roles'].items():
            subclan_role_ids.append(role_id)
            role_obj = inter.guild.get_role(role_id)
            if role_obj:
                 subclan_roles_map[role_id] = role_obj

        if 'custom_roles' in subclan:
            for custom_role_data in subclan['custom_roles'].values():
                subclan_role_ids.append(custom_role_data['id'])
                role_obj = inter.guild.get_role(custom_role_data['id'])
                if role_obj:
                     subclan_roles_map[custom_role_data['id']] = role_obj

        # Проверяем, является ли переданная роль одной из ролей подразделения
        if role.id in subclan_role_ids:
            target_role = role # Используем переданный объект роли

        if not target_role:
            await inter.response.send_message(f'Роль {role.mention} не найдена в подразделении или не является ролью подразделения!', ephemeral=True)
            return

        # Проверяем, не пытаемся ли убрать роль лидера
        leader_role_id = subclan['roles'].get('leader')
        if leader_role_id and target_role.id == leader_role_id:
            await inter.response.send_message('Нельзя удалить роль лидера!', ephemeral=True)
            return

        try:
            # Удаляем роль
            await member.remove_roles(target_role, reason=f"Изменение роли в подразделении {subclan_name}")
            
            # Отправляем уведомления
            announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
            if announcements_channel:
                embed = disnake.Embed(
                    title="Изменение роли участника",
                    description=f"{member.mention} получил роль {role.name}",
                    color=disnake.Color.blue()
                )
                await announcements_channel.send(embed=embed)

            await inter.response.send_message(f'Роль {role.name} успешно удалена у {member.mention}!', ephemeral=True)

        except Exception as e:
            await inter.response.send_message(f'Произошла ошибка при удалении роли: {str(e)}', ephemeral=True)

    @commands.slash_command(
        name="subclanroles",
        description="Просмотр всех ролей подразделения"
    )
    async def list_subclan_roles_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        embed = disnake.Embed(
            title=f"Роли подразделения {subclan_name}",
            color=disnake.Color.blue()
        )

        # Добавляем основные роли
        main_roles = {
            'leader': 'Лидер',
            'officer': 'Офицер',
            'member': 'Участник'
        }

        for role_type, role_name in main_roles.items():
            role = inter.guild.get_role(subclan['roles'][role_type])
            if role:
                embed.add_field(
                    name=role_name,
                    value=f"{role.mention}\nЦвет: {str(role.color)}",
                    inline=True
                )

        # Добавляем пользовательские роли
        if 'custom_roles' in subclan and subclan['custom_roles']:
            custom_roles_text = []
            for role_name, role_data in subclan['custom_roles'].items():
                role = inter.guild.get_role(role_data['id'])
                if role:
                    custom_roles_text.append(f"{role.mention} - {role_name}")
            
            if custom_roles_text:
                embed.add_field(
                    name="Пользовательские роли",
                    value="\n".join(custom_roles_text),
                    inline=False
                )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="subclansettings",
        description="Настройки подразделения"
    )
    async def subclan_settings_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        setting_type: str = commands.Param(
            description="Тип настройки",
            choices=["description", "max_members", "welcome_message"]
        ),
        value: str = commands.Param(description="Новое значение настройки")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может изменять настройки подразделения!', ephemeral=True)
            return

        try:
            if setting_type == "description":
                subclan['description'] = value
                await inter.response.send_message(f'Описание подразделения обновлено!', ephemeral=True)
            
            elif setting_type == "max_members":
                try:
                    max_members = int(value)
                    if max_members < len(subclan['members']):
                        await inter.response.send_message('Новое максимальное количество участников не может быть меньше текущего количества участников!', ephemeral=True)
                        return
                    subclan['max_members'] = max_members
                    await inter.response.send_message(f'Максимальное количество участников обновлено на {max_members}!', ephemeral=True)
                except ValueError:
                    await inter.response.send_message('Пожалуйста, укажите корректное число!', ephemeral=True)
                    return
            
            elif setting_type == "welcome_message":
                if 'settings' not in subclan:
                    subclan['settings'] = {}
                subclan['settings']['welcome_message'] = value
                await inter.response.send_message(f'Приветственное сообщение обновлено!', ephemeral=True)

            save_clan_data()

        except Exception as e:
            await inter.response.send_message(f'Произошла ошибка при обновлении настроек: {str(e)}', ephemeral=True)

    @commands.slash_command(
        name="subclanviewsettings",
        description="Просмотр настроек подразделения"
    )
    async def view_subclan_settings_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        embed = disnake.Embed(
            title=f"Настройки подразделения {subclan_name}",
            color=disnake.Color.blue()
        )

        # Основные настройки
        embed.add_field(
            name="Основные настройки",
            value=f"**Описание:** {subclan['description']}\n"
                  f"**Максимум участников:** {subclan['max_members']}\n"
                  f"**Текущее количество участников:** {len(subclan['members'])}",
            inline=False
        )

        # Приветственное сообщение
        welcome_message = subclan.get('settings', {}).get('welcome_message', 'Не установлено')
        embed.add_field(
            name="Приветственное сообщение",
            value=welcome_message,
            inline=False
        )

        # Каналы
        channels = []
        for channel_type, channel_id in subclan['channels'].items():
            channel = inter.guild.get_channel(channel_id)
            if channel:
                channels.append(f"{channel_type}: {channel.mention}")
        
        if channels:
            embed.add_field(
                name="Каналы",
                value="\n".join(channels),
                inline=False
            )

        # Роли
        roles = []
        for role_type, role_id in subclan['roles'].items():
            role = inter.guild.get_role(role_id)
            if role:
                roles.append(f"{role_type}: {role.mention}")

        if roles:
            embed.add_field(
                name="Роли",
                value="\n".join(roles),
                inline=False
            )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="subclangiverole",
        description="Выдать роль участнику подразделения"
    )
    async def give_subclan_role_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        member: disnake.Member = commands.Param(description="Участник для выдачи роли"),
        role: disnake.Role = commands.Param(description="Роль для выдачи из подразделения")
    ):
        # Отправляем отложенный ответ
        await inter.response.defer(ephemeral=True)

        if subclan_name not in clan_data.get('subclans', {}):
            await inter.edit_original_response(content='Подразделение не найдено!')
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.edit_original_response(content='Только лидер может выдавать роли!')
            return

        # Проверяем, состоит ли участник в подразделении
        if str(member.id) not in subclan['members']:
            await inter.edit_original_response(content='Этот участник не состоит в подразделении!')
            return

        try:
            # Получаем все роли подразделения
            subclan_roles = {}
            
            # Добавляем основные роли
            for role_type, role_id in subclan['roles'].items():
                role = inter.guild.get_role(role_id)
                if role:
                    subclan_roles[role_type] = role

            # Добавляем кастомные роли
            if 'custom_roles' in subclan:
                for custom_role_name, custom_role_data in subclan['custom_roles'].items():
                    role = inter.guild.get_role(custom_role_data['id'])
                    if role:
                        subclan_roles[custom_role_name] = role

            # Проверяем, существует ли запрошенная роль среди ролей подразделения
            target_role = None

            # Получаем все ID ролей подразделения (основные и кастомные)
            subclan_role_ids = []
            for role_type, role_id in subclan['roles'].items():
                subclan_role_ids.append(role_id)
            if 'custom_roles' in subclan:
                for custom_role_data in subclan['custom_roles'].values():
                    subclan_role_ids.append(custom_role_data['id'])

            # Проверяем, является ли переданная роль одной из ролей подразделения
            if role.id in subclan_role_ids:
                target_role = role # Используем переданный объект роли

            # Если роль не найдена в подразделении, отправляем ошибку и выходим
            if not target_role:
                await inter.edit_original_response(content=f'Роль {role.mention} не найдена в подразделении или не является ролью подразделения!')
                return # Выходим из функции

            # Проверяем, не пытаемся ли выдать роль лидера
            leader_role_id = subclan['roles'].get('leader')
            if leader_role_id and target_role.id == leader_role_id:
                await inter.edit_original_response(content='Нельзя выдать роль лидера через эту команду!')
                return # Выходим из функции

            # Проверяем, может ли бот управлять этой ролью
            if not inter.guild.me.guild_permissions.manage_roles:
                await inter.edit_original_response(content='У бота нет прав на управление ролями!')
                return

            if target_role >= inter.guild.me.top_role:
                await inter.edit_original_response(content='Роль бота слишком низкая для управления этой ролью!')
                return

            # Удаляем все роли подразделения у участника
            roles_to_remove = []
            for role in subclan_roles.values():
                if role != subclan_roles.get('leader') and role in member.roles:  # Не трогаем роль лидера
                    roles_to_remove.append(role)

            # Удаляем все роли одним действием
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason=f"Изменение роли в подразделении {subclan_name}")

            # Выдаем новую роль
            await member.add_roles(target_role, reason=f"Выдача роли в подразделении {subclan_name}")
            
            # Отправляем уведомления
            announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
            if announcements_channel:
                role_display_name = role.name
                if role.name.lower() == 'офицер':
                    role_display_name = 'Офицер'
                elif role.name.lower() == 'участник':
                    role_display_name = 'Участник'
                
                embed = disnake.Embed(
                    title="Изменение роли участника",
                    description=f"{member.mention} получил роль {role_display_name}",
                    color=disnake.Color.blue()
                )
                await announcements_channel.send(embed=embed)

            await inter.edit_original_response(content=f'Роль {role_display_name} успешно выдана {member.mention}!')

        except disnake.Forbidden:
            await inter.edit_original_response(content='У бота нет прав для управления ролями!')
        except disnake.HTTPException as e:
            await inter.edit_original_response(content=f'Произошла ошибка при выдаче роли: {str(e)}')
        except Exception as e:
            await inter.edit_original_response(content=f'Произошла неизвестная ошибка: {str(e)}')

    @commands.slash_command(
        name="subclanroleorder",
        description="Изменить порядок ролей подразделения"
    )
    async def change_role_order_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        role1: str = commands.Param(description="Первая роль"),
        role2: str = commands.Param(description="Вторая роль")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может менять порядок ролей!', ephemeral=True)
            return

        # Получаем роли
        role1_obj = None
        role2_obj = None

        # Проверяем основные роли
        if role1.lower() == 'лидер':
            role1_obj = inter.guild.get_role(subclan['roles']['leader'])
        elif role1.lower() == 'офицер':
            role1_obj = inter.guild.get_role(subclan['roles']['officer'])
        elif role1.lower() == 'участник':
            role1_obj = inter.guild.get_role(subclan['roles']['member'])
        elif 'custom_roles' in subclan and role1 in subclan['custom_roles']:
            role1_obj = inter.guild.get_role(subclan['custom_roles'][role1]['id'])

        if role2.lower() == 'лидер':
            role2_obj = inter.guild.get_role(subclan['roles']['leader'])
        elif role2.lower() == 'офицер':
            role2_obj = inter.guild.get_role(subclan['roles']['officer'])
        elif role2.lower() == 'участник':
            role2_obj = inter.guild.get_role(subclan['roles']['member'])
        elif 'custom_roles' in subclan and role2 in subclan['custom_roles']:
            role2_obj = inter.guild.get_role(subclan['custom_roles'][role2]['id'])

        if not role1_obj or not role2_obj:
            await inter.response.send_message('Одна или обе роли не найдены в подразделении!', ephemeral=True)
            return

        try:
            # Меняем позиции ролей
            await role1_obj.edit(position=role2_obj.position)
            
            # Отправляем уведомления
            announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
            if announcements_channel:
                embed = disnake.Embed(
                    title="Изменение порядка ролей",
                    description=f"Порядок ролей {role1_obj.mention} и {role2_obj.mention} был изменен",
                    color=disnake.Color.blue()
                )
                await announcements_channel.send(embed=embed)

            await inter.response.send_message(f'Порядок ролей успешно изменен!', ephemeral=True)

        except Exception as e:
            await inter.response.send_message(f'Произошла ошибка при изменении порядка ролей: {str(e)}', ephemeral=True)

    @commands.slash_command(
        name="subclandeleterole",
        description="Удалить роль из подразделения"
    )
    async def delete_subclan_role_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        role_name: str = commands.Param(description="Название роли для удаления")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может удалять роли из подразделения!', ephemeral=True)
            return

        # Проверяем существование роли
        role = None
        if role_name.lower() == 'офицер':
            role = inter.guild.get_role(subclan['roles']['officer'])
        elif role_name.lower() == 'участник':
            role = inter.guild.get_role(subclan['roles']['member'])
        elif 'custom_roles' in subclan and role_name in subclan['custom_roles']:
            role = inter.guild.get_role(subclan['custom_roles'][role_name]['id'])

        if not role:
            await inter.response.send_message('Роль не найдена в подразделении!', ephemeral=True)
            return

        # Проверяем, не пытаемся ли удалить роль лидера
        if role.id == subclan['roles']['leader']:
            await inter.response.send_message('Нельзя удалить роль лидера!', ephemeral=True)
            return

        try:
            # Удаляем роль с сервера
            await role.delete(reason=f"Удаление роли из подразделения {subclan_name}")

            # Удаляем роль из настроек подразделения
            if role_name.lower() == 'офицер':
                del subclan['roles']['officer']
            elif role_name.lower() == 'участник':
                del subclan['roles']['member']
            elif 'custom_roles' in subclan and role_name in subclan['custom_roles']:
                del subclan['custom_roles'][role_name]

            save_clan_data()
            
            # Отправляем уведомления
            announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
            if announcements_channel:
                embed = disnake.Embed(
                    title="Удаление роли из подразделения",
                    description=f"Роль {role_name} была удалена из подразделения",
                    color=disnake.Color.red()
                )
                await announcements_channel.send(embed=embed)

            await inter.response.send_message(f'Роль {role_name} успешно удалена из подразделения!', ephemeral=True)

        except Exception as e:
            await inter.response.send_message(f'Произошла ошибка при удалении роли: {str(e)}', ephemeral=True)

    @commands.slash_command(
        name="subclanchannel",
        description="Управление каналами подразделения"
    )
    async def subclan_channel(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @subclan_channel.sub_command(
        name="create",
        description="Создать новый канал в подразделении"
    )
    async def create_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        channel_type: str = commands.Param(
            description="Тип канала",
            choices=["text", "voice", "announcement"]
        ),
        name: str = commands.Param(description="Название канала"),
        topic: str = commands.Param(description="Тема канала", default=None),
        user_limit: int = commands.Param(
            description="Лимит пользователей (только для голосового канала)",
            default=0,
            min_value=0,
            max_value=99
        )
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может создавать каналы в подразделении!', ephemeral=True)
            return

        try:
            category = inter.guild.get_channel(subclan['channels']['category'])
            if not category:
                await inter.response.send_message('Категория подразделения не найдена!', ephemeral=True)
                return

            # Проверяем права бота
            if not inter.guild.me.guild_permissions.manage_channels:
                await inter.response.send_message('У бота нет прав на создание каналов!', ephemeral=True)
                return

            # Создаем канал в зависимости от типа
            channel = None
            if channel_type == "text":
                channel = await category.create_text_channel(
                    name=name,
                    topic=topic
                )
            elif channel_type == "voice":
                channel = await category.create_voice_channel(
                    name=name,
                    user_limit=user_limit if user_limit > 0 else None
                )
            elif channel_type == "announcement":
                channel = await category.create_news_channel(
                    name=name,
                    topic=topic
                )

            if not channel:
                await inter.response.send_message('Не удалось создать канал!', ephemeral=True)
                return

            # Настраиваем права доступа
            member_role = inter.guild.get_role(subclan['roles']['member'])
            officer_role = inter.guild.get_role(subclan['roles']['officer'])
            leader_role = inter.guild.get_role(subclan['roles']['leader'])

            if not all([member_role, officer_role, leader_role]):
                await channel.delete()
                await inter.response.send_message('Не удалось найти роли подразделения!', ephemeral=True)
                return

            await channel.set_permissions(inter.guild.default_role, read_messages=False)
            await channel.set_permissions(member_role, read_messages=True, send_messages=True)
            await channel.set_permissions(officer_role, read_messages=True, send_messages=True, manage_messages=True)
            await channel.set_permissions(leader_role, read_messages=True, send_messages=True, manage_messages=True, manage_channels=True)

            # Сохраняем информацию о канале
            if 'additional_channels' not in subclan:
                subclan['additional_channels'] = {}
            
            subclan['additional_channels'][str(channel.id)] = {
                'name': name,
                'type': channel_type,
                'created_at': datetime.now().isoformat()
            }
            save_clan_data()

            # Отправляем уведомление
            announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
            if announcements_channel:
                embed = disnake.Embed(
                    title="Новый канал создан",
                    description=f"В подразделении создан новый канал {channel.mention}",
                    color=disnake.Color.green()
                )
                await announcements_channel.send(embed=embed)

            await inter.response.send_message(f'Канал {channel.mention} успешно создан!', ephemeral=True)

        except Exception as e:
            await inter.response.send_message(f'Произошла ошибка при создании канала: {str(e)}', ephemeral=True)

    @subclan_channel.sub_command(
        name="edit",
        description="Редактировать канал подразделения"
    )
    async def edit_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        channel: disnake.abc.GuildChannel = commands.Param(description="Канал для редактирования"),
        new_name: str = commands.Param(description="Новое название канала", default=None),
        new_topic: str = commands.Param(description="Новая тема канала", default=None),
        user_limit: int = commands.Param(
            description="Новый лимит пользователей (только для голосового канала)",
            default=None,
            min_value=0,
            max_value=99
        )
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может редактировать каналы в подразделении!', ephemeral=True)
            return

        # Проверяем, принадлежит ли канал подразделению
        if not hasattr(channel, 'category_id') or channel.category_id != subclan['channels']['category']:
            await inter.response.send_message('Этот канал не принадлежит подразделению!', ephemeral=True)
            return

        try:
            # Обновляем канал
            update_params = {}
            
            if new_name:
                update_params['name'] = new_name
                
            if new_topic and isinstance(channel, (disnake.TextChannel, disnake.NewsChannel)):
                update_params['topic'] = new_topic
                
            if user_limit is not None and isinstance(channel, disnake.VoiceChannel):
                update_params['user_limit'] = user_limit if user_limit > 0 else None

            if update_params:
                await channel.edit(**update_params)

                # Обновляем информацию в данных
                if 'additional_channels' in subclan and str(channel.id) in subclan['additional_channels']:
                    if new_name:
                        subclan['additional_channels'][str(channel.id)]['name'] = new_name
                    save_clan_data()

                await inter.response.send_message(f'Канал {channel.mention} успешно обновлен!', ephemeral=True)
            else:
                await inter.response.send_message('Не указаны параметры для обновления!', ephemeral=True)

        except Exception as e:
            await inter.response.send_message(f'Произошла ошибка при редактировании канала: {str(e)}', ephemeral=True)

    @subclan_channel.sub_command(
        name="delete",
        description="Удалить канал подразделения"
    )
    async def delete_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения"),
        channel: disnake.abc.GuildChannel = commands.Param(description="Канал для удаления")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, является ли пользователь лидером подразделения
        if str(inter.author.id) != subclan['created_by']:
            await inter.response.send_message('Только лидер может удалять каналы в подразделении!', ephemeral=True)
            return

        # Проверяем, принадлежит ли канал подразделению
        if not hasattr(channel, 'category_id') or channel.category_id != subclan['channels']['category']:
            await inter.response.send_message('Этот канал не принадлежит подразделению!', ephemeral=True)
            return

        # Проверяем, не пытаемся ли удалить основные каналы
        if channel.id in subclan['channels'].values():
            await inter.response.send_message('Нельзя удалить основные каналы подразделения!', ephemeral=True)
            return

        try:
            # Создаем кнопки подтверждения
            confirm_button = disnake.ui.Button(
                style=disnake.ButtonStyle.danger,
                label="Подтвердить",
                custom_id="confirm_delete_channel"
            )
            cancel_button = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label="Отмена",
                custom_id="cancel_delete_channel"
            )

            # Создаем компонент с кнопками
            components = disnake.ui.ActionRow(confirm_button, cancel_button)

            # Отправляем сообщение с кнопками
            message = await inter.response.send_message(
                f"Вы уверены, что хотите удалить канал {channel.mention}?\n"
                "Это действие нельзя отменить!",
                components=[components],
                ephemeral=True
            )

            # Ждем нажатия кнопки
            try:
                interaction = await self.bot.wait_for(
                    "button_click",
                    check=lambda i: i.author == inter.author and i.message.id == message.id,
                    timeout=30.0
                )
            except:
                await inter.edit_original_response(
                    content="Время ожидания истекло. Удаление отменено.",
                    components=[]
                )
                return

            # Проверяем, какая кнопка была нажата
            if interaction.data.custom_id == "cancel_delete_channel":
                await interaction.response.edit_message(
                    content="Удаление канала отменено.",
                    components=[]
                )
                return

            # Если подтверждено, удаляем канал
            await interaction.response.edit_message(
                content="Удаление канала...",
                components=[]
            )

            # Удаляем канал
            await channel.delete()

            # Удаляем информацию из данных
            if 'additional_channels' in subclan and str(channel.id) in subclan['additional_channels']:
                del subclan['additional_channels'][str(channel.id)]
                save_clan_data()

            await interaction.edit_original_response(
                content=f'Канал успешно удален!',
                components=[]
            )

        except Exception as e:
            await inter.response.send_message(f'Произошла ошибка при удалении канала: {str(e)}', ephemeral=True)

    @subclan_channel.sub_command(
        name="list",
        description="Показать список каналов подразделения"
    )
    async def list_channels(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения")
    ):
        if subclan_name not in clan_data.get('subclans', {}):
            await inter.response.send_message('Подразделение не найдено!', ephemeral=True)
            return

        subclan = clan_data['subclans'][subclan_name]
        
        embed = disnake.Embed(
            title=f"Каналы подразделения {subclan_name}",
            color=disnake.Color.blue()
        )

        # Основные каналы
        main_channels = {
            'general': 'Общий канал',
            'announcements': 'Канал объявлений',
            'voice': 'Голосовой канал'
        }

        main_channels_text = []
        for channel_type, channel_name in main_channels.items():
            channel = inter.guild.get_channel(subclan['channels'][channel_type])
            if channel:
                main_channels_text.append(f"{channel.mention} - {channel_name}")

        if main_channels_text:
            embed.add_field(
                name="Основные каналы",
                value="\n".join(main_channels_text),
                inline=False
            )

        # Дополнительные каналы
        if 'additional_channels' in subclan and subclan['additional_channels']:
            additional_channels_text = []
            for channel_id, channel_data in subclan['additional_channels'].items():
                channel = inter.guild.get_channel(int(channel_id))
                if channel:
                    channel_type = channel_data['type']
                    type_emoji = {
                        'text': '💬',
                        'voice': '🔊',
                        'announcement': '📢'
                    }.get(channel_type, '❓')
                    additional_channels_text.append(f"{type_emoji} {channel.mention}")

            if additional_channels_text:
                embed.add_field(
                    name="Дополнительные каналы",
                    value="\n".join(additional_channels_text),
                    inline=False
                )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        """Обработчик события выхода участника из клана"""
        # Проверяем все подразделения
        for subclan_name, subclan in clan_data.get('subclans', {}).items():
            # Если участник был в подразделении
            if str(member.id) in subclan['members']:
                # Удаляем все роли подразделения
                for role_id in subclan['roles'].values():
                    role = member.guild.get_role(role_id)
                    if role and role in member.roles:
                        try:
                            await member.remove_roles(role)
                        except:
                            pass

                # Удаляем кастомные роли
                if 'custom_roles' in subclan:
                    for custom_role_data in subclan['custom_roles'].values():
                        role = member.guild.get_role(custom_role_data['id'])
                        if role and role in member.roles:
                            try:
                                await member.remove_roles(role)
                            except:
                                pass

                # Удаляем из списка участников
                subclan['members'].remove(str(member.id))

                # Удаляем заявку, если она была
                if 'applications' in subclan and str(member.id) in subclan['applications']:
                    del subclan['applications'][str(member.id)]

                # Отправляем уведомление в канал объявлений
                announcements_channel = member.guild.get_channel(subclan['channels']['announcements'])
                if announcements_channel:
                    embed = disnake.Embed(
                        title="Участник покинул клан",
                        description=f"{member.mention} был автоматически удален из подразделения, так как покинул клан.",
                        color=disnake.Color.red()
                    )
                    await announcements_channel.send(embed=embed)

        # Сохраняем изменения
        save_clan_data()

    @commands.slash_command(
        name="subclanleave",
        description="Покинуть подразделение"
    )
    async def leave_subclan_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        subclan_name: str = commands.Param(description="Название подразделения")
    ):
        # Отправляем отложенный ответ
        await inter.response.defer(ephemeral=True)

        if subclan_name not in clan_data.get('subclans', {}):
            await inter.edit_original_response(content='Подразделение не найдено!')
            return

        subclan = clan_data['subclans'][subclan_name]
        
        # Проверяем, состоит ли участник в подразделении
        if str(inter.author.id) not in subclan['members']:
            await inter.edit_original_response(content='Вы не состоите в этом подразделении!')
            return

        # Проверяем, не является ли участник лидером
        if str(inter.author.id) == subclan['created_by']:
            await inter.edit_original_response(content='Лидер не может покинуть подразделение! Используйте команду /subclandelete для удаления подразделения.')
            return

        # Создаем кнопки подтверждения
        confirm_button = disnake.ui.Button(
            style=disnake.ButtonStyle.danger,
            label="Подтвердить",
            custom_id="confirm_leave"
        )
        cancel_button = disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label="Отмена",
            custom_id="cancel_leave"
        )

        # Создаем компонент с кнопками
        components = disnake.ui.ActionRow(confirm_button, cancel_button)

        # Отправляем сообщение с кнопками
        message = await inter.edit_original_response(
            content=f"Вы уверены, что хотите покинуть подразделение '{subclan_name}'?\n"
                   "После выхода вы не сможете создать или присоединиться к подразделению в течение 24 часов.",
            components=[components]
        )

        # Ждем нажатия кнопки
        try:
            interaction = await self.bot.wait_for(
                "button_click",
                check=lambda i: i.author == inter.author and i.message.id == message.id,
                timeout=30.0
            )
        except:
            await inter.edit_original_response(
                content="Время ожидания истекло. Выход отменен.",
                components=[]
            )
            return

        # Проверяем, какая кнопка была нажата
        if interaction.data.custom_id == "cancel_leave":
            await interaction.response.edit_message(
                content="Выход из подразделения отменен.",
                components=[]
            )
            return

        # Если подтверждено, удаляем участника
        await interaction.response.edit_message(
            content="Выход из подразделения...",
            components=[]
        )

        try:
            # Удаляем все роли подразделения
            for role_id in subclan['roles'].values():
                role = inter.guild.get_role(role_id)
                if role and role in inter.author.roles:
                    try:
                        await inter.author.remove_roles(role)
                    except Exception as e:
                        print(f"Ошибка при удалении роли {role.name}: {str(e)}")

            # Удаляем кастомные роли
            if 'custom_roles' in subclan:
                for custom_role_data in subclan['custom_roles'].values():
                    role = inter.guild.get_role(custom_role_data['id'])
                    if role and role in inter.author.roles:
                        try:
                            await inter.author.remove_roles(role)
                        except Exception as e:
                            print(f"Ошибка при удалении кастомной роли {role.name}: {str(e)}")

            # Удаляем из списка участников
            subclan['members'].remove(str(inter.author.id))

            # Сохраняем время выхода
            if 'leave_cooldowns' not in clan_data:
                clan_data['leave_cooldowns'] = {}
            clan_data['leave_cooldowns'][str(inter.author.id)] = datetime.now().isoformat()

            # Отправляем уведомления
            announcements_channel = inter.guild.get_channel(subclan['channels']['announcements'])
            if announcements_channel:
                try:
                    embed = disnake.Embed(
                        title="Участник покинул подразделение",
                        description=f"{inter.author.mention} покинул подразделение.",
                        color=disnake.Color.orange()
                    )
                    await announcements_channel.send(embed=embed)
                except Exception as e:
                    print(f"Ошибка при отправке уведомления в канал объявлений: {str(e)}")

            save_clan_data()

            # Отправляем финальное сообщение через новый ответ
            await interaction.followup.send(
                content=f'Вы успешно покинули подразделение "{subclan_name}"!\n'
                       'Вы не сможете создать или присоединиться к подразделению в течение 24 часов.',
                ephemeral=True
            )

        except Exception as e:
            error_message = f'Произошла ошибка при выходе из подразделения: {str(e)}'
            print(error_message)  # Логируем ошибку
            try:
                await interaction.followup.send(
                    content=error_message,
                    ephemeral=True
                )
            except:
                # Если не удалось отправить сообщение через followup, пробуем через edit
                try:
                    await interaction.edit_original_response(
                        content=error_message,
                        components=[]
                    )
                except:
                    # Если и это не удалось, отправляем новое сообщение
                    await inter.followup.send(
                        content=error_message,
                        ephemeral=True
                    )

    def check_cooldown(self, user_id: str) -> tuple[bool, str]:
        """Проверяет кулдаун для пользователя"""
        if 'leave_cooldowns' not in clan_data:
            return True, ""

        last_leave = clan_data['leave_cooldowns'].get(str(user_id))
        if not last_leave:
            return True, ""

        last_leave_time = datetime.fromisoformat(last_leave)
        time_passed = datetime.now() - last_leave_time
        cooldown_time = timedelta(hours=24)

        if time_passed < cooldown_time:
            remaining = cooldown_time - time_passed
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            return False, f"{hours} ч. {minutes} мин."

        return True, ""

def setup(bot):
    bot.add_cog(Subclans(bot)) 