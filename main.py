import disnake
from disnake.ext import commands, tasks
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import asyncio

# Загрузка переменных окружения
load_dotenv()
TOKEN = 'token'

# Настройка интентов
intents = disnake.Intents.default()
intents.message_content = True
intents.members = True

# Инициализация бота
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    test_guilds=[ID]  # ID вашего сервера
)

# Отключаем встроенную команду help
bot.remove_command('help')

# Структура данных клана
clan_data = {
    'members': {},  # ID участника: {joined_at, role}
    'applications': {},  # ID заявки: {timestamp, status, age, experience, motivation, screenshots}
    'roles': {
        'leader': None,
        'member': None,
        'applicant': None,
        'new_member': None
    },
    'events': {},  # ID события: {name, date, description, participants, created_by}
    'warnings': {},  # ID предупреждения: {user_id, reason, timestamp, issued_by}
    'announcements': [],  # Список объявлений
    'subclans': {},  # Подразделения клана
    'factions': {  # Система группировок
        'enabled': False,  # Включена ли система
        'message_id': None,  # ID сообщения с embed
        'channel_id': None,  # ID канала с выбором группировок
        'factions': {}  # Словарь группировок: {id: {name, role_id, emoji, description, color}}
    },
    'notifications': {
        'youtube': {},
        'twitch': {}
    },
    'settings': {
        'welcome_channel': None,
        'announcement_channel': None,
        'log_channel': None,
        'prefix': '!',  # Префикс команд
        'auto_role': None,  # Автоматическая роль для новых участников
        'welcome_message': 'Добро пожаловать на сервер!',  # Сообщение приветствия
        'inactivity_days': 30,  # Количество дней неактивности
        'max_warnings': 3,  # Максимальное количество предупреждений
        'event_reminder_hours': 24,  # За сколько часов напоминать о событии
        'allowed_screenshot_domains': [],  # Разрешенные домены для скриншотов
        'moderation_roles': [],  # ID ролей модераторов
        'admin_roles': [],  # ID ролей администраторов
        'custom_commands': {},  # Пользовательские команды
        'auto_delete_messages': False,  # Автоматическое удаление сообщений
        'auto_delete_delay': 60,  # Задержка удаления сообщений в секундах
        'log_events': True,  # Логирование событий
        'log_types': {  # Типы событий для логирования
            'member_join': True,
            'member_leave': True,
            'message_delete': True,
            'message_edit': True,
            'role_changes': True,
            'channel_changes': True,
            'server_changes': True
        }
    }
}

# Функции для работы с данными
def save_clan_data():
    try:
        with open('clan_data.json', 'w', encoding='utf-8') as f:
            json.dump(clan_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")
        return False

def load_clan_data():
    global clan_data
    try:
        with open('clan_data.json', 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
            # Обновляем существующие данные, сохраняя структуру
            for key in clan_data:
                if key in loaded_data:
                    if isinstance(clan_data[key], dict):
                        clan_data[key].update(loaded_data[key])
                    else:
                        clan_data[key] = loaded_data[key]
        return True
    except FileNotFoundError:
        save_clan_data()
        return True
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return False

# События бота
@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе!')
    if load_clan_data():
        print('Данные успешно загружены!')
    else:
        print('Ошибка при загрузке данных!')
    check_inactive_members.start()
    cleanup_old_events.start()
    check_event_reminders.start()
    
    # Устанавливаем статус "играет в STALCRAFT: X"
    await bot.change_presence(
        activity=disnake.Activity(
            type=disnake.ActivityType.playing,
            name="STALCRAFT: X"
        )
    )

@bot.event
async def on_member_join(member):
    if clan_data['settings']['welcome_channel']:
        channel = bot.get_channel(clan_data['settings']['welcome_channel'])
        if channel:
            embed = disnake.Embed(
                title="Добро пожаловать!",
                description=f"{member.mention} {clan_data['settings']['welcome_message']}\n"
                           f"Используйте команду `/apply` чтобы подать заявку на вступление в клан.",
                color=disnake.Color.green()
            )
            await channel.send(embed=embed)

    # Выдача автоматической роли
    if clan_data['settings']['auto_role']:
        role = disnake.utils.get(member.guild.roles, id=clan_data['settings']['auto_role'])
        if role:
            await member.add_roles(role)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('У вас нет прав для выполнения этой команды!', ephemeral=True)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'Отсутствует обязательный аргумент: {error.param.name}', ephemeral=True)
    elif isinstance(error, commands.BadArgument):
        await ctx.send('Неверный аргумент!', ephemeral=True)
    else:
        await ctx.send(f'Произошла ошибка: {str(error)}', ephemeral=True)

# Фоновые задачи
@tasks.loop(hours=24)
async def check_inactive_members():
    now = datetime.now()
    for member_id, data in clan_data['members'].items():
        joined_at = datetime.fromisoformat(data['joined_at'])
        if now - joined_at > timedelta(days=clan_data['settings']['inactivity_days']):
            guild = bot.get_guild(1377866241712066630)  # ID вашего сервера
            if guild:
                member = guild.get_member(int(member_id))
                if member:
                    # Отправка уведомления в ЛС
                    try:
                        await member.send('Вы были отмечены как неактивный участник клана. '
                                        'Если вы хотите остаться в клане, пожалуйста, проявите активность.')
                    except:
                        pass

@tasks.loop(hours=1)
async def cleanup_old_events():
    now = datetime.now()
    for event_id, event in list(clan_data['events'].items()):
        event_date = datetime.fromisoformat(event['date'])
        if event_date < now:
            del clan_data['events'][event_id]
    save_clan_data()

@tasks.loop(hours=1)
async def check_event_reminders():
    now = datetime.now()
    reminder_time = timedelta(hours=clan_data['settings']['event_reminder_hours'])
    
    for event_id, event in clan_data['events'].items():
        event_date = datetime.fromisoformat(event['date'])
        if now < event_date < now + reminder_time:
            # Отправка напоминания участникам
            for participant_id in event['participants']:
                try:
                    user = await bot.fetch_user(int(participant_id))
                    await user.send(f'Напоминание: событие "{event["name"]}" начнется через {clan_data["settings"]["event_reminder_hours"]} часов!')
                except:
                    pass

@bot.command()
async def invite_server(ctx):
       # Находим текстовый канал на сервере
    channel = disnake.utils.get(ctx.guild.text_channels)
    if channel is not None:
           # Создаем бесконечное приглашение
        invite = await channel.create_invite(max_age=0, max_uses=0)
        await ctx.send(f'Вот ваше бесконечное приглашение: {invite}')
    else:
        await ctx.send('На сервере нет текстовых каналов.')

bot.load_extension('cogs.applications')
bot.load_extension('cogs.events')
bot.load_extension('cogs.members')
bot.load_extension('cogs.admin')
bot.load_extension('cogs.subclans')
bot.load_extension('cogs.giveaways.giveaway_commands')
bot.load_extension('cogs.factions')
bot.load_extension('cogs.temp.commands')
bot.load_extension('cogs.lvl.leveling')
bot.load_extension('cogs.automod')
bot.load_extension('cogs.trading')

# Запуск бота
bot.run(TOKEN)