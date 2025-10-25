import disnake
from disnake.ext import commands
import json
import os
from datetime import datetime, timedelta
import random

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldown = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.member)
        self.voice_cooldown = commands.CooldownMapping.from_cooldown(1, 300, commands.BucketType.member)
        self.data_file = 'cogs/lvl/lvl_data.json'
        self.backup_file = 'cogs/lvl/lvl_data_backup.json'
        self.last_save = datetime.now()
        
        # Создаем начальные настройки
        self.default_settings = {
            'enabled': True,
            'xp_per_message': 5,
            'xp_per_voice_minute': 2,
            'xp_cooldown': 20,
            'voice_cooldown': 100,
            'level_roles': {},
            'rewards': {},
            'announcements': {
                'channel_id': None,
                'enabled': True
            },
            'leaderboard': {
                'message_id': None,
                'channel_id': None,
                'update_interval': 300
            }
        }
        
        # Загружаем данные из файла
        self.data = self.load_data()

    def load_data(self):
        """Загружает данные из файла"""
        try:
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            # Пробуем загрузить основной файл
            if os.path.exists(self.data_file) and os.path.getsize(self.data_file) > 0:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            # Если основной файл не существует или пуст, пробуем загрузить бэкап
            elif os.path.exists(self.backup_file) and os.path.getsize(self.backup_file) > 0:
                with open(self.backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print("Загружены данные из резервной копии")
            else:
                # Создаем новую структуру данных
                data = {
                    'settings': self.default_settings,
                    'users': {},
                    'last_update': datetime.now().isoformat()
                }
                print("Создана новая структура данных")
            
            print(f"Данные уровней успешно загружены из {self.data_file}")
            return data
            
        except Exception as e:
            print(f"Ошибка при загрузке данных уровней: {e}")
            # Создаем пустую структуру данных
            data = {
                'settings': self.default_settings,
                'users': {},
                'last_update': datetime.now().isoformat()
            }
            print("Создана пустая структура данных с начальными настройками")
            return data

    def save_data(self, guild_id, force=False):
        """Сохраняет данные"""
        try:
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            # Обновляем время последнего обновления
            self.data['last_update'] = datetime.now().isoformat()
            
            # Сначала сохраняем в бэкап
            with open(self.backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            
            # Затем сохраняем в основной файл
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            
            # Обновляем время последнего сохранения
            self.last_save = datetime.now()
            
            print(f"Данные уровней успешно сохранены в {self.data_file}")
            
        except Exception as e:
            print(f"Ошибка при сохранении данных уровней: {e}")
            # Пробуем восстановить из бэкапа при ошибке
            try:
                if os.path.exists(self.backup_file):
                    with open(self.backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)
                    with open(self.data_file, 'w', encoding='utf-8') as f:
                        json.dump(backup_data, f, ensure_ascii=False, indent=4)
                    print("Данные восстановлены из резервной копии")
            except Exception as backup_error:
                print(f"Ошибка при восстановлении из резервной копии: {backup_error}")

    def calculate_level(self, xp):
        """Вычисляет уровень на основе опыта"""
        level = 0
        while xp >= self.get_xp_for_level(level + 1):
            level += 1
        return level

    def get_xp_for_level(self, level):
        """Вычисляет необходимый опыт для достижения уровня"""
        return 5 * (level ** 2) + 50 * level + 100

    def get_progress(self, xp, level):
        """Вычисляет прогресс до следующего уровня"""
        current_level_xp = self.get_xp_for_level(level)
        next_level_xp = self.get_xp_for_level(level + 1)
        return (xp - current_level_xp) / (next_level_xp - current_level_xp) * 100

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.data['settings']['enabled'] or message.author.bot:
            return

        # Проверяем кулдаун
        bucket = self.xp_cooldown.get_bucket(message)
        if bucket.update_rate_limit():
            return

        # Получаем или создаем данные пользователя
        user_id = str(message.author.id)
        if user_id not in self.data['users']:
            self.data['users'][user_id] = {
                'xp': 0,
                'level': 0,
                'total_messages': 0,
                'voice_time': 0,
                'last_voice_update': None
            }

        user_data = self.data['users'][user_id]
        old_level = user_data['level']

        # Добавляем опыт
        user_data['xp'] += self.data['settings']['xp_per_message']
        user_data['total_messages'] += 1

        # Проверяем повышение уровня
        new_level = self.calculate_level(user_data['xp'])
        if new_level > old_level:
            user_data['level'] = new_level
            await self.handle_level_up(message.author, new_level)

        # Сохраняем данные
        self.save_data(message.guild.id if message.guild else 0)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.data['settings']['enabled'] or member.bot:
            return

        # Проверяем кулдаун
        bucket = self.voice_cooldown.get_bucket(member)
        if bucket.update_rate_limit():
            return

        user_id = str(member.id)
        if user_id not in self.data['users']:
            self.data['users'][user_id] = {
                'xp': 0,
                'level': 0,
                'total_messages': 0,
                'voice_time': 0,
                'last_voice_update': None
            }

        user_data = self.data['users'][user_id]

        # Если пользователь присоединился к голосовому каналу
        if after.channel and (not before.channel or before.channel != after.channel):
            user_data['last_voice_update'] = datetime.now().isoformat()
            self.save_data(member.guild.id)
        # Если пользователь покинул голосовой канал
        elif before.channel and (not after.channel or before.channel != after.channel):
            if user_data['last_voice_update']:
                last_update = datetime.fromisoformat(user_data['last_voice_update'])
                time_spent = datetime.now() - last_update
                minutes = time_spent.total_seconds() / 60
                
                # Добавляем опыт за время в голосовом канале
                xp_gained = int(minutes * self.data['settings']['xp_per_voice_minute'])
                user_data['xp'] += xp_gained
                user_data['voice_time'] += minutes

                # Проверяем повышение уровня
                old_level = user_data['level']
                new_level = self.calculate_level(user_data['xp'])
                if new_level > old_level:
                    user_data['level'] = new_level
                    await self.handle_level_up(member, new_level)

                user_data['last_voice_update'] = None
                self.save_data(member.guild.id)

    @commands.Cog.listener()
    async def on_ready(self):
        """При запуске бота проверяем и восстанавливаем данные"""
        print("Проверка и восстановление данных уровней...")
        for guild in self.bot.guilds:
            # Проверяем и восстанавливаем данные пользователей
            for user_id, user_data in self.data['users'].items():
                # Проверяем наличие всех необходимых полей
                required_fields = ['xp', 'level', 'total_messages', 'voice_time', 'last_voice_update']
                for field in required_fields:
                    if field not in user_data:
                        user_data[field] = 0 if field != 'last_voice_update' else None
                
                # Пересчитываем уровень на основе опыта
                user_data['level'] = self.calculate_level(user_data['xp'])

            # Принудительно сохраняем данные при запуске
            self.save_data(guild.id, force=True)
        
        print("Проверка и восстановление данных уровней завершены")

    async def handle_level_up(self, member, new_level):
        """Обрабатывает повышение уровня"""
        # Проверяем награды за уровень
        if str(new_level) in self.data['settings']['rewards']:
            reward = self.data['settings']['rewards'][str(new_level)]
            role = member.guild.get_role(reward['role_id'])
            if role:
                try:
                    await member.add_roles(role)
                    await member.send(f"Поздравляем! Вы получили роль {role.mention} за достижение {new_level} уровня!")
                except:
                    pass

        # Отправляем уведомление
        if self.data['settings']['announcements']['enabled'] and self.data['settings']['announcements']['channel_id']:
            channel = member.guild.get_channel(self.data['settings']['announcements']['channel_id'])
            if channel:
                embed = disnake.Embed(
                    title="🎉 Повышение уровня!",
                    description=f"{member.mention} достиг {new_level} уровня!",
                    color=disnake.Color.green()
                )
                await channel.send(embed=embed)

    @commands.slash_command(
        name="level",
        description="Показать уровень участника"
    )
    async def show_level(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник", default=None)
    ):
        if not self.data['settings']['enabled']:
            await inter.response.send_message("Система уровней отключена!", ephemeral=True)
            return

        target = member or inter.author
        user_id = str(target.id)

        if user_id not in self.data['users']:
            await inter.response.send_message(f"У {target.mention} пока нет уровня!", ephemeral=True)
            return

        user_data = self.data['users'][user_id]
        level = user_data['level']
        xp = user_data['xp']
        progress = self.get_progress(xp, level)
        next_level_xp = self.get_xp_for_level(level + 1)

        embed = disnake.Embed(
            title=f"Уровень {target.name}",
            color=disnake.Color.blue()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(
            name="Уровень",
            value=f"**{level}**",
            inline=True
        )
        embed.add_field(
            name="Опыт",
            value=f"**{xp}/{next_level_xp}**",
            inline=True
        )
        embed.add_field(
            name="Прогресс",
            value=f"**{progress:.1f}%**",
            inline=True
        )
        
        # Добавляем статистику
        embed.add_field(
            name="Статистика",
            value=f"Сообщений: **{user_data['total_messages']}**\n"
                  f"Время в голосовых: **{int(user_data['voice_time'])} мин.**",
            inline=False
        )

        await inter.response.send_message(embed=embed)

    @commands.slash_command(
        name="leaderboard",
        description="Показать таблицу лидеров"
    )
    async def show_leaderboard(
        self,
        inter: disnake.ApplicationCommandInteraction,
        type: str = commands.Param(
            description="Тип таблицы лидеров",
            choices=["xp", "messages", "voice"]
        )
    ):
        if not self.data['settings']['enabled']:
            await inter.response.send_message("Система уровней отключена!", ephemeral=True)
            return

        if not self.data['users']:
            await inter.response.send_message("Пока нет данных для таблицы лидеров!", ephemeral=True)
            return

        # Сортируем пользователей
        if type == "xp":
            sorted_users = sorted(
                self.data['users'].items(),
                key=lambda x: x[1]['xp'],
                reverse=True
            )
            title = "Таблица лидеров по опыту"
            value_key = 'xp'
            value_format = lambda x: f"{x:,} XP"
        elif type == "messages":
            sorted_users = sorted(
                self.data['users'].items(),
                key=lambda x: x[1]['total_messages'],
                reverse=True
            )
            title = "Таблица лидеров по сообщениям"
            value_key = 'total_messages'
            value_format = lambda x: f"{x:,} сообщений"
        else:  # voice
            sorted_users = sorted(
                self.data['users'].items(),
                key=lambda x: x[1]['voice_time'],
                reverse=True
            )
            title = "Таблица лидеров по времени в голосовых каналах"
            value_key = 'voice_time'
            value_format = lambda x: f"{int(x)} мин."

        embed = disnake.Embed(
            title=title,
            color=disnake.Color.gold()
        )

        # Добавляем топ-10 пользователей
        for i, (user_id, data) in enumerate(sorted_users[:10], 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                value = data[value_key]
                embed.add_field(
                    name=f"{i}. {user.name}",
                    value=value_format(value),
                    inline=False
                )
            except:
                continue

        await inter.response.send_message(embed=embed)

    @commands.slash_command(
        name="levelsettings",
        description="Настройки системы уровней"
    )
    async def level_settings(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @level_settings.sub_command(
        name="toggle",
        description="Включить/выключить систему уровней"
    )
    async def toggle_leveling(
        self,
        inter: disnake.ApplicationCommandInteraction,
        enabled: bool = commands.Param(description="Включить/выключить систему уровней")
    ):
        # Проверяем права
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("У вас нет прав для изменения настроек!", ephemeral=True)
            return

        self.data['settings']['enabled'] = enabled
        self.save_data(inter.guild.id, force=True)

        status = "включена" if enabled else "выключена"
        await inter.response.send_message(f"Система уровней {status}!", ephemeral=True)

    @level_settings.sub_command(
        name="setxp",
        description="Установить количество опыта за действия"
    )
    async def set_xp(
        self,
        inter: disnake.ApplicationCommandInteraction,
        action: str = commands.Param(
            description="Действие",
            choices=["message", "voice"]
        ),
        amount: int = commands.Param(
            description="Количество опыта",
            min_value=1
        )
    ):
        # Проверяем права
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("У вас нет прав для изменения настроек!", ephemeral=True)
            return

        if action == "message":
            self.data['settings']['xp_per_message'] = amount
        else:
            self.data['settings']['xp_per_voice_minute'] = amount

        self.save_data(inter.guild.id, force=True)
        await inter.response.send_message(f"Количество опыта за {action} установлено на {amount}!", ephemeral=True)

    @level_settings.sub_command(
        name="setcooldown",
        description="Установить задержку между начислениями опыта"
    )
    async def set_cooldown(
        self,
        inter: disnake.ApplicationCommandInteraction,
        action: str = commands.Param(
            description="Действие",
            choices=["message", "voice"]
        ),
        seconds: int = commands.Param(
            description="Задержка в секундах",
            min_value=1
        )
    ):
        # Проверяем права
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("У вас нет прав для изменения настроек!", ephemeral=True)
            return

        if action == "message":
            self.data['settings']['xp_cooldown'] = seconds
            self.xp_cooldown = commands.CooldownMapping.from_cooldown(1, seconds, commands.BucketType.member)
        else:
            self.data['settings']['voice_cooldown'] = seconds
            self.voice_cooldown = commands.CooldownMapping.from_cooldown(1, seconds, commands.BucketType.member)

        self.save_data(inter.guild.id, force=True)
        await inter.response.send_message(f"Задержка для {action} установлена на {seconds} секунд!", ephemeral=True)

    @level_settings.sub_command(
        name="setannouncements",
        description="Настроить канал для объявлений о повышении уровня"
    )
    async def set_announcements(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(description="Канал для объявлений"),
        enabled: bool = commands.Param(description="Включить/выключить объявления", default=True)
    ):
        # Проверяем права
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("У вас нет прав для изменения настроек!", ephemeral=True)
            return

        self.data['settings']['announcements']['channel_id'] = channel.id
        self.data['settings']['announcements']['enabled'] = enabled
        self.save_data(inter.guild.id, force=True)

        status = "включены" if enabled else "выключены"
        await inter.response.send_message(f"Объявления о повышении уровня {status} в канале {channel.mention}!", ephemeral=True)

    @level_settings.sub_command(
        name="addreward",
        description="Добавить награду за достижение уровня"
    )
    async def add_reward(
        self,
        inter: disnake.ApplicationCommandInteraction,
        level: int = commands.Param(description="Уровень", min_value=1),
        role: disnake.Role = commands.Param(description="Роль для выдачи")
    ):
        # Проверяем права
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("У вас нет прав для изменения настроек!", ephemeral=True)
            return

        if 'rewards' not in self.data['settings']:
            self.data['settings']['rewards'] = {}

        self.data['settings']['rewards'][str(level)] = {
            'role_id': role.id,
            'role_name': role.name
        }
        self.save_data(inter.guild.id, force=True)

        await inter.response.send_message(f"Награда за {level} уровень установлена: {role.mention}!", ephemeral=True)

    @level_settings.sub_command(
        name="removereward",
        description="Удалить награду за уровень"
    )
    async def remove_reward(
        self,
        inter: disnake.ApplicationCommandInteraction,
        level: int = commands.Param(description="Уровень", min_value=1)
    ):
        # Проверяем права
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("У вас нет прав для изменения настроек!", ephemeral=True)
            return

        if 'rewards' not in self.data['settings'] or str(level) not in self.data['settings']['rewards']:
            await inter.response.send_message(f"Награда за {level} уровень не найдена!", ephemeral=True)
            return

        del self.data['settings']['rewards'][str(level)]
        self.save_data(inter.guild.id, force=True)

        await inter.response.send_message(f"Награда за {level} уровень удалена!", ephemeral=True)

    @level_settings.sub_command(
        name="rewards",
        description="Показать список наград за уровни"
    )
    async def show_rewards(
        self,
        inter: disnake.ApplicationCommandInteraction
    ):
        if 'rewards' not in self.data['settings'] or not self.data['settings']['rewards']:
            await inter.response.send_message("Награды за уровни не настроены!", ephemeral=True)
            return

        embed = disnake.Embed(
            title="Награды за уровни",
            color=disnake.Color.blue()
        )

        for level, reward in sorted(self.data['settings']['rewards'].items(), key=lambda x: int(x[0])):
            role = inter.guild.get_role(reward['role_id'])
            if role:
                embed.add_field(
                    name=f"Уровень {level}",
                    value=role.mention,
                    inline=True
                )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @level_settings.sub_command(
        name="reset",
        description="Сбросить прогресс участника"
    )
    async def reset_progress(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Участник для сброса прогресса")
    ):
        # Проверяем права
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("У вас нет прав для изменения настроек!", ephemeral=True)
            return

        user_id = str(member.id)
        if user_id not in self.data['users']:
            await inter.response.send_message(f"У {member.mention} нет прогресса для сброса!", ephemeral=True)
            return

        # Создаем кнопки подтверждения
        confirm_button = disnake.ui.Button(
            style=disnake.ButtonStyle.danger,
            label="Подтвердить",
            custom_id="confirm_reset"
        )
        cancel_button = disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label="Отмена",
            custom_id="cancel_reset"
        )

        # Создаем компонент с кнопками
        components = disnake.ui.ActionRow(confirm_button, cancel_button)

        # Отправляем сообщение с кнопками
        message = await inter.response.send_message(
            f"Вы уверены, что хотите сбросить прогресс {member.mention}?\n"
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
                content="Время ожидания истекло. Сброс отменен.",
                components=[]
            )
            return

        # Проверяем, какая кнопка была нажата
        if interaction.data.custom_id == "cancel_reset":
            await interaction.response.edit_message(
                content="Сброс прогресса отменен.",
                components=[]
            )
            return

        # Если подтверждено, сбрасываем прогресс
        await interaction.response.edit_message(
            content="Сброс прогресса...",
            components=[]
        )

        # Удаляем данные пользователя
        del self.data['users'][user_id]
        self.save_data(inter.guild.id, force=True)

        await interaction.edit_original_response(
            content=f"Прогресс {member.mention} успешно сброшен!",
            components=[]
        )

def setup(bot):
    bot.add_cog(Leveling(bot)) 