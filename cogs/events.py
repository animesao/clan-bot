import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
from main import clan_data, save_clan_data

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="event",
        description="Создать событие клана"
    )
    @commands.has_permissions(administrator=True)
    async def create_event_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(description="Название события"),
        date: str = commands.Param(description="Дата события (ДД.ММ.ГГГГ)"),
        time: str = commands.Param(description="Время события (ЧЧ:ММ)"),
        description: str = commands.Param(description="Описание события")
    ):
        try:
            event_date = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M")
            if event_date < datetime.now():
                await inter.response.send_message('Дата события не может быть в прошлом!', ephemeral=True)
                return
        except ValueError:
            await inter.response.send_message('Неверный формат даты или времени! Используйте формат ДД.ММ.ГГГГ и ЧЧ:ММ', ephemeral=True)
            return

        event_id = str(len(clan_data['events']) + 1)
        clan_data['events'][event_id] = {
            'name': name,
            'date': event_date.isoformat(),
            'description': description,
            'participants': [],
            'created_by': inter.author.id
        }
        save_clan_data()

        # Отправка уведомления в канал объявлений
        if clan_data['settings']['announcement_channel']:
            channel = self.bot.get_channel(clan_data['settings']['announcement_channel'])
            if channel:
                embed = disnake.Embed(
                    title="Новое событие клана!",
                    description=f"**{name}**\n\n{description}\n\n"
                               f"Дата: {date}\n"
                               f"Время: {time}\n\n"
                               f"Используйте команду `/join {event_id}` чтобы присоединиться!",
                    color=disnake.Color.blue()
                )
                await channel.send(embed=embed)

        await inter.response.send_message(f'Событие "{name}" создано!', ephemeral=True)

    @commands.slash_command(
        name="join",
        description="Присоединиться к событию"
    )
    async def join_event_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        event_id: str = commands.Param(description="ID события")
    ):
        if event_id not in clan_data['events']:
            await inter.response.send_message('Событие не найдено!', ephemeral=True)
            return

        if str(inter.author.id) in clan_data['events'][event_id]['participants']:
            await inter.response.send_message('Вы уже участвуете в этом событии!', ephemeral=True)
            return

        clan_data['events'][event_id]['participants'].append(str(inter.author.id))
        save_clan_data()

        await inter.response.send_message(f'Вы присоединились к событию "{clan_data["events"][event_id]["name"]}"!', ephemeral=True)

    @commands.slash_command(
        name="events",
        description="Просмотр активных событий"
    )
    async def view_events_slash(self, inter: disnake.ApplicationCommandInteraction):
        active_events = {
            event_id: event for event_id, event in clan_data['events'].items()
            if datetime.fromisoformat(event['date']) > datetime.now()
        }

        if not active_events:
            await inter.response.send_message('Нет активных событий.', ephemeral=True)
            return

        embed = disnake.Embed(title='Активные события', color=disnake.Color.blue())
        for event_id, event in active_events.items():
            event_date = datetime.fromisoformat(event['date'])
            participants = len(event['participants'])
            embed.add_field(
                name=f"{event['name']} (ID: {event_id})",
                value=f"Дата: {event_date.strftime('%d.%m.%Y %H:%M')}\n"
                      f"Описание: {event['description']}\n"
                      f"Участников: {participants}",
                inline=False
            )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="leave",
        description="Покинуть событие"
    )
    async def leave_event_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        event_id: str = commands.Param(description="ID события")
    ):
        if event_id not in clan_data['events']:
            await inter.response.send_message('Событие не найдено!', ephemeral=True)
            return

        if str(inter.author.id) not in clan_data['events'][event_id]['participants']:
            await inter.response.send_message('Вы не участвуете в этом событии!', ephemeral=True)
            return

        clan_data['events'][event_id]['participants'].remove(str(inter.author.id))
        save_clan_data()

        await inter.response.send_message(f'Вы покинули событие "{clan_data["events"][event_id]["name"]}"!', ephemeral=True)

    @commands.slash_command(
        name="cancel",
        description="Отменить событие"
    )
    @commands.has_permissions(administrator=True)
    async def cancel_event_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        event_id: str = commands.Param(description="ID события")
    ):
        if event_id not in clan_data['events']:
            await inter.response.send_message('Событие не найдено!', ephemeral=True)
            return

        event_name = clan_data['events'][event_id]['name']
        participants = clan_data['events'][event_id]['participants']
        del clan_data['events'][event_id]
        save_clan_data()

        # Отправка уведомления в канал объявлений
        if clan_data['settings']['announcement_channel']:
            channel = self.bot.get_channel(clan_data['settings']['announcement_channel'])
            if channel:
                embed = disnake.Embed(
                    title="Событие отменено",
                    description=f"Событие **{event_name}** было отменено.",
                    color=disnake.Color.red()
                )
                await channel.send(embed=embed)

        # Отправка уведомлений участникам
        for user_id in participants:
            try:
                user = await self.bot.fetch_user(int(user_id))
                await user.send(f'Событие "{event_name}" было отменено.')
            except:
                pass

        await inter.response.send_message(f'Событие "{event_name}" отменено!', ephemeral=True)

    @commands.slash_command(
        name="finishevent",
        description="Завершить событие"
    )
    @commands.has_permissions(administrator=True)
    async def finish_event_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        event_id: str = commands.Param(description="ID события")
    ):
        if event_id not in clan_data.get('events', {}):
            await inter.response.send_message('Событие не найдено!', ephemeral=True)
            return

        event_name = clan_data['events'][event_id]['name']
        del clan_data['events'][event_id]
        save_clan_data()

        # Отправка уведомления в канал объявлений
        if clan_data['settings']['announcement_channel']:
            channel = self.bot.get_channel(clan_data['settings']['announcement_channel'])
            if channel:
                embed = disnake.Embed(
                    title="Событие завершено",
                    description=f"Событие **{event_name}** было успешно завершено.",
                    color=disnake.Color.green()
                )
                await channel.send(embed=embed)

        await inter.response.send_message(f'Событие "{event_name}" завершено!', ephemeral=True)

def setup(bot):
    bot.add_cog(Events(bot)) 