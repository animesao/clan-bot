import disnake
from disnake.ext import commands
from datetime import datetime
from main import clan_data, save_clan_data
import asyncio

class Applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verification_messages = {}

    @commands.Cog.listener()
    async def on_ready(self):
        # Восстанавливаем все сообщения с кнопками верификации
        for guild in self.bot.guilds:
            if 'verification_messages' in clan_data and str(guild.id) in clan_data['verification_messages']:
                for channel_id, message_id in clan_data['verification_messages'][str(guild.id)].items():
                    try:
                        channel = guild.get_channel(int(channel_id))
                        if channel:
                            message = await channel.fetch_message(int(message_id))
                            if message:
                                # Создаем новое view с кнопкой
                                view = disnake.ui.View()
                                view.add_item(disnake.ui.Button(
                                    label="Подать заявку",
                                    custom_id="verify_button",
                                    style=disnake.ButtonStyle.primary
                                ))
                                # Обновляем сообщение с кнопкой
                                await message.edit(view=view)
                    except:
                        continue

    @commands.Cog.listener()
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        if inter.custom_id == "apply_modal":
            await inter.response.defer(ephemeral=True)
            age = inter.text_values["age"]
            experience = inter.text_values["experience"]
            motivation = inter.text_values["motivation"]
            screenshots = inter.text_values["screenshots"]

            # Проверка ссылок на изображения
            screenshot_links = screenshots.split('\n')
            valid_links = []
            for link in screenshot_links:
                if link.strip():  # Проверяем только что ссылка не пустая
                    valid_links.append(link.strip())

            if not valid_links:
                await inter.edit_original_response(content='Пожалуйста, предоставьте хотя бы одну ссылку на скриншот!')
                return

            clan_data['applications'][str(inter.author.id)] = {
                'timestamp': datetime.now().isoformat(),
                'status': 'pending',
                'nickname': 'nickname',
                'age': age,
                'experience': experience,
                'motivation': motivation,
                'screenshots': valid_links
            }
            save_clan_data()

            # Отправка уведомления лидеру клана
            await inter.edit_original_response(content='Ваша заявка успешно отправлена!')

    @commands.slash_command(
        name="set_apply_channel",
        description="Установить канал для подачи заявок"
    )
    @commands.has_permissions(administrator=True)
    async def set_apply_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(description="Канал для подачи заявок")
    ):
        await inter.response.defer(ephemeral=True)
        if 'apply_channels' not in clan_data['settings']:
            clan_data['settings']['apply_channels'] = []
        
        if channel.id not in clan_data['settings']['apply_channels']:
            clan_data['settings']['apply_channels'].append(channel.id)
            save_clan_data()
            await inter.edit_original_response(content=f'Канал {channel.mention} добавлен для подачи заявок!')
        else:
            await inter.edit_original_response(content=f'Канал {channel.mention} уже добавлен для подачи заявок!')

    @commands.slash_command(
        name="remove_apply_channel",
        description="Удалить канал для подачи заявок"
    )
    @commands.has_permissions(administrator=True)
    async def remove_apply_channel(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(description="Канал для удаления из списка заявок")
    ):
        await inter.response.defer(ephemeral=True)
        if 'apply_channels' in clan_data['settings'] and channel.id in clan_data['settings']['apply_channels']:
            clan_data['settings']['apply_channels'].remove(channel.id)
            save_clan_data()
            await inter.edit_original_response(content=f'Канал {channel.mention} удален из списка каналов для подачи заявок!')
        else:
            await inter.edit_original_response(content=f'Канал {channel.mention} не был добавлен для подачи заявок!')

    @commands.command(
        name="verification",
        description="Создать кнопку верификации"
    )
    @commands.has_permissions(administrator=True)
    async def verification(self, ctx):
        embed = disnake.Embed(
            title="Верификация",
            description="Чтобы попасть в клан нажмите на **Подать заявку** и заполните форму после \nэтого ожидаете до **24 часов** \n\nВы можете вступить если захотите в какое-то **подразделение**",
            color=disnake.Color.blue()
        )
        
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(
            label="Подать заявку",
            custom_id="verify_button",
            style=disnake.ButtonStyle.primary
        ))
        
        message = await ctx.send(embed=embed, view=view)
        
        # Сохраняем ID сообщения в базе данных
        if 'verification_messages' not in clan_data:
            clan_data['verification_messages'] = {}
        if str(ctx.guild.id) not in clan_data['verification_messages']:
            clan_data['verification_messages'][str(ctx.guild.id)] = {}
        
        clan_data['verification_messages'][str(ctx.guild.id)][str(ctx.channel.id)] = str(message.id)
        save_clan_data()

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "verify_button":
            # Проверка разрешенных каналов
            if 'apply_channels' in clan_data['settings'] and clan_data['settings']['apply_channels']:
                if inter.channel.id not in clan_data['settings']['apply_channels']:
                    allowed_channels = [f"<#{channel_id}>" for channel_id in clan_data['settings']['apply_channels']]
                    await inter.response.send_message(
                        f'Вы можете подать заявку только в следующих каналах: {", ".join(allowed_channels)}',
                        ephemeral=True
                    )
                    return

            if str(inter.author.id) in clan_data['applications']:
                await inter.response.send_message('Вы уже подали заявку! Пожалуйста, дождитесь ответа.', ephemeral=True)
                return

            # Выдача роли подавшему заявку
            applicant_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['applicant'])
            if applicant_role:
                await inter.author.add_roles(applicant_role)
                # Удаление роли нового участника, если она есть
                new_member_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['new_member'])
                if new_member_role and new_member_role in inter.author.roles:
                    await inter.author.remove_roles(new_member_role)

            # Создание модального окна для заявки
            modal = disnake.ui.Modal(
                title="Заявка в клан",
                custom_id="apply_modal",
                components=[
                    disnake.ui.TextInput(
                        label="Ваш никнейм",
                        custom_id="nickname",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        min_length=1,
                        max_length=32
                    ),
                    disnake.ui.TextInput(
                        label="Ваш возраст",
                        custom_id="age",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        min_length=1,
                        max_length=3
                    ),
                    disnake.ui.TextInput(
                        label="Опыт в игре",
                        custom_id="experience",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        min_length=10,
                        max_length=1000
                    ),
                    disnake.ui.TextInput(
                        label="Почему хотите вступить?",
                        custom_id="motivation",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        min_length=10,
                        max_length=1000
                    ),
                    disnake.ui.TextInput(
                        label="Ссылки на скриншоты (по одной на строку)",
                        custom_id="screenshots",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        placeholder="Вставьте ссылки на скриншоты (по одной на строку)"
                    )
                ]
            )
            await inter.response.send_modal(modal)
        elif inter.component.custom_id.startswith("view_screenshots_"):
            await inter.response.defer(ephemeral=True)
            user_id = inter.component.custom_id.split("_")[-1]
            if user_id in clan_data['applications']:
                screenshots = clan_data['applications'][user_id]['screenshots']
                embed = disnake.Embed(
                    title="Скриншоты заявки",
                    color=disnake.Color.blue()
                )
                for i, screenshot in enumerate(screenshots, 1):
                    embed.add_field(
                        name=f"Скриншот {i}",
                        value=f"[Открыть]({screenshot})",
                        inline=False
                    )
                await inter.edit_original_response(embed=embed)

    @commands.slash_command(
        name="accept",
        description="Принять заявку пользователя"
    )
    @commands.has_permissions(administrator=True)
    async def accept_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Пользователь, которого нужно принять")
    ):
        await inter.response.defer()
        
        # Проверка ролей
        leader_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['leader'])
        officer_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['officer'])
        
        if not (leader_role in inter.author.roles or officer_role in inter.author.roles):
            await inter.edit_original_response(content='У вас нет прав для принятия заявок! Только глава клана и офицеры могут принимать заявки.')
            return

        if str(member.id) not in clan_data['applications']:
            await inter.edit_original_response(content='Заявка от этого пользователя не найдена!')
            return

        try:
            # Удаление роли подавшего заявку
            applicant_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['applicant'])
            if applicant_role and applicant_role in member.roles:
                await member.remove_roles(applicant_role)

            # Выдача роли участника клана
            member_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['member'])
            if member_role:
                await member.add_roles(member_role)

            try:
                clan_data['members'][str(member.id)] = {
                    'joined_at': datetime.now().isoformat(),
                    'role': 'member',
                    'accepted_by': str(inter.author.id)
                }
                del clan_data['applications'][str(member.id)]
                save_clan_data()

                # Отправка уведомления в канал объявлений
                if clan_data['settings']['announcement_channel']:
                    channel = self.bot.get_channel(clan_data['settings']['announcement_channel'])
                    if channel:
                        embed = disnake.Embed(
                            title="Новый участник клана!",
                            description=f"{member.mention} присоединился к клану!\nПринял: {inter.author.mention}\n\nДата присоединения: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                            color=disnake.Color.green()
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        await channel.send(embed=embed)

                # Отправка уведомления в ЛС
                try:
                    embed = disnake.Embed(
                        title="Ваша заявка принята!",
                        description=f"Поздравляем! Вы были приняты в клан!\n\nДата присоединения: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                        color=disnake.Color.green()
                    )
                    await member.send(embed=embed)
                except:
                    pass

                await inter.edit_original_response(content=f'{member.mention} принят в клан!')
                # Удаляем сообщение через 5 секунд
                await asyncio.sleep(5)
                await inter.delete_original_response()
            except Exception as e:
                await inter.edit_original_response(content=f'Произошла ошибка при принятии заявки: {str(e)}')
        except Exception as e:
            await inter.edit_original_response(content=f'Произошла ошибка при принятии заявки: {str(e)}')

    @commands.slash_command(
        name="reject",
        description="Отклонить заявку пользователя"
    )
    @commands.has_permissions(administrator=True)
    async def reject_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Пользователь, заявку которого нужно отклонить"),
        reason: str = commands.Param(description="Причина отклонения")
    ):
        await inter.response.defer()
        
        # Проверка ролей
        leader_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['leader'])
        officer_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['officer'])
        
        if not (leader_role in inter.author.roles or officer_role in inter.author.roles):
            await inter.edit_original_response(content='У вас нет прав для отклонения заявок! Только глава клана и офицеры могут отклонять заявки.')
            return

        if str(member.id) not in clan_data['applications']:
            await inter.edit_original_response(content='Заявка от этого пользователя не найдена!')
            return

        try:
            # Удаление роли подавшего заявку
            applicant_role = disnake.utils.get(inter.guild.roles, id=clan_data['roles']['applicant'])
            if applicant_role and applicant_role in member.roles:
                await member.remove_roles(applicant_role)

            # Сохраняем данные заявки перед удалением
            application_data = clan_data['applications'][str(member.id)]
            del clan_data['applications'][str(member.id)]
            save_clan_data()

            # Отправка уведомления в ЛС
            try:
                embed = disnake.Embed(
                    title="Ваша заявка отклонена",
                    description=f"К сожалению, ваша заявка на вступление в клан была отклонена.\n\n"
                               f"**Причина:** {reason}\n\n"
                               f"**Ваша заявка:**\n"
                               f"Никнейм: {application_data['nickname']}\n"
                               f"Возраст: {application_data['age']}\n"
                               f"Опыт: {application_data['experience']}\n"
                               f"Мотивация: {application_data['motivation']}\n\n"
                               f"Дата отклонения: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                    color=disnake.Color.red()
                )
                await member.send(embed=embed)
            except:
                pass

            # Отправка уведомления в канал объявлений
            if clan_data['settings']['announcement_channel']:
                channel = self.bot.get_channel(clan_data['settings']['announcement_channel'])
                if channel:
                    embed = disnake.Embed(
                        title="Заявка отклонена",
                        description=f"Заявка от {member.mention} была отклонена.\nПричина: {reason}\nОтклонил: {inter.author.mention}\n\nДата отклонения: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                        color=disnake.Color.red()
                    )
                    await channel.send(embed=embed)

            await inter.edit_original_response(content=f'Заявка от {member.mention} отклонена.')
        except Exception as e:
            await inter.edit_original_response(content=f'Произошла ошибка при отклонении заявки: {str(e)}')

    @commands.slash_command(
        name="applications",
        description="Просмотр списка заявок"
    )
    @commands.has_permissions(administrator=True)
    async def view_applications_slash(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        if not clan_data['applications']:
            await inter.edit_original_response(content='Нет активных заявок.')
            return

        embed = disnake.Embed(title='Список заявок', color=disnake.Color.blue())
        for user_id, data in clan_data['applications'].items():
            try:
                user = await self.bot.fetch_user(int(user_id))
                embed.add_field(
                    name=f'Заявка от {user.name}',
                    value=f'Ваш никнейм: {data["nickname"]}\n'
                          f'Статус: {data["status"]}\n'
                          f'Возраст: {data["age"]}\n'
                          f'Опыт: {data["experience"]}\n'
                          f'Мотивация: {data["motivation"]}\n'
                          f'Время: {data["timestamp"]}',
                    inline=False
                )
            except:
                continue

        # Добавляем кнопки для просмотра скриншотов
        view = disnake.ui.View()
        for user_id in clan_data['applications'].keys():
            view.add_item(disnake.ui.Button(
                label=f"Просмотреть скриншоты {user_id}",
                custom_id=f"view_screenshots_{user_id}",
                style=disnake.ButtonStyle.primary
            ))
        await inter.edit_original_response(embed=embed, view=view)

def setup(bot):
    bot.add_cog(Applications(bot))