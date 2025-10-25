# 🎮 Discord Clan Bot

<div align="center">
  <img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <br>
  <img src="https://img.shields.io/github/stars/animesao/clan-bot?style=social" alt="Stars">
  <img src="https://img.shields.io/github/forks/animesao/clan-bot?style=social" alt="Forks">
</div>

<p align="center">
  <strong>A powerful Discord bot for clan management, written in Python using the disnake library.</strong>
  <br>
  Manage your gaming clan with ease: applications, events, member control, and more!
</p>

## 📋 Table of Contents
- [English](#english)
- [Русский](#русский)

## English

### ✨ Features

- **📝 Application System**
  - Submit applications with age, experience, and motivation details
  - Attach screenshots
  - Review applications by administrators
  - Notifications for acceptance/rejection

- **📅 Event System**
  - Create events with date and time
  - Join events
  - View active events
  - Cancel events

- **👥 Member Management**
  - View member profiles
  - Warning system
  - Kick members from the clan
  - Automatic activity checks

- **⚙️ Administrative Commands**
  - Create announcements
  - Configure channels and roles
  - View settings
  - Clear messages

### 🚀 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/animesao/clan-bot.git
cd clan-bot
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure in `main.py`:**
```python
TOKEN = "your_bot_token"
```

4. **Run the bot:**
```bash
python main.py
```

### ⚙️ Setup

1. **Invite the bot to your server** with necessary permissions
2. **Configure channels** using `/setchannel`:
   - `welcome` - welcome channel
   - `announcement` - announcement channel
   - `log` - log channel

3. **Configure roles** using `/setrole`:
   - `leader` - clan leader role
   - `member` - clan member role
   - `applicant` - applicant role
   - `new_member` - new server member role

### 💬 Commands

#### 👤 General Commands
- `/apply` - Submit application to join the clan
- `/profile [member]` - View member's profile
- `/events` - View active events
- `/join [event_id]` - Join an event
- `/leave [event_id]` - Leave an event

#### 🛡️ Admin Commands
- `/accept [member]` - Accept application
- `/reject [member] [reason]` - Reject application
- `/applications` - View application list
- `/event [name] [date] [time] [description]` - Create event
- `/cancel [event_id]` - Cancel event
- `/warn [member] [reason]` - Issue warning
- `/warnings [member]` - View warnings
- `/kick [member] [reason]` - Kick member
- `/announce [title] [content]` - Create announcement
- `/setchannel [type] [channel]` - Set channel
- `/setrole [type] [role]` - Set role
- `/settings` - View current settings
- `/clear [amount]` - Clear messages in channel

### 📄 License

MIT

---

## Русский

### Функциональность

- **Система заявок на вступление в клан**
  - Подача заявки с информацией о возрасте, опыте и мотивации
  - Прикрепление скриншотов
  - Рассмотрение заявок администраторами
  - Уведомления о принятии/отклонении заявки

- **Система событий**
  - Создание событий с датой и временем
  - Присоединение к событиям
  - Просмотр активных событий
  - Отмена событий

- **Управление участниками**
  - Просмотр профилей участников
  - Система предупреждений
  - Исключение участников из клана
  - Автоматическая проверка активности

- **Административные команды**
  - Создание объявлений
  - Настройка каналов и ролей
  - Просмотр настроек
  - Очистка сообщений

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/animesao/clan-bot.git
cd clan-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Зайдите в `main.py` и настройте:
```python
TOKEN = "ваш_токен_бота"
```

4. Запустите бота:
```bash
python main.py
```

### Настройка

1. Пригласите бота на ваш сервер с необходимыми правами
2. Используйте команду `/setchannel` для настройки каналов:
   - `welcome` - канал для приветствий
   - `announcement` - канал для объявлений
   - `log` - канал для логов

3. Используйте команду `/setrole` для настройки ролей:
   - `leader` - роль лидера клана
   - `member` - роль участника клана
   - `applicant` - роль подавшего заявку
   - `new_member` - роль нового участника сервера

### Команды

#### Общие команды
- `/apply` - подать заявку на вступление в клан
- `/profile [участник]` - просмотреть профиль участника
- `/events` - просмотреть активные события
- `/join [id_события]` - присоединиться к событию
- `/leave [id_события]` - покинуть событие

#### Команды администратора
- `/accept [участник]` - принять заявку
- `/reject [участник] [причина]` - отклонить заявку
- `/applications` - просмотреть список заявок
- `/event [название] [дата] [время] [описание]` - создать событие
- `/cancel [id_события]` - отменить событие
- `/warn [участник] [причина]` - выдать предупреждение
- `/warnings [участник]` - просмотреть предупреждения
- `/kick [участник] [причина]` - исключить участника
- `/announce [заголовок] [содержание]` - создать объявление
- `/setchannel [тип] [канал]` - настроить канал
- `/setrole [тип] [роль]` - настроить роль
- `/settings` - просмотреть текущие настройки
- `/clear [количество]` - очистить сообщения в канале

### Лицензия

MIT
