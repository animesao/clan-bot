import disnake
from disnake.ext import commands, tasks
from .giveaway_utils import GiveawayManager
from datetime import datetime, timedelta
import random
import asyncio

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaway_manager = GiveawayManager()
        self.check_giveaways.start()
        
    def cog_unload(self):
        self.check_giveaways.cancel()

    @commands.slash_command(name="giveaway")
    @commands.has_permissions(administrator=True)
    async def giveaway(
        self,
        inter: disnake.ApplicationCommandInteraction,
        prize: str,
        winners: int = commands.Param(default=1, min_value=1, max_value=100, description="Число победителей от 1 до 100"),
        duration: str = commands.Param(description="Пример: 1d 12h 30m (d-дни, h-часы, m-минуты)"),
        description: str = None,
        image_url: str = commands.Param(default=None, description="URL изображения для розыгрыша (необязательно)")
    ):
        """Создать розыгрыш"""
        try:
            # Парсинг длительности
            total_seconds = 0
            parts = duration.lower().split()
        
            for part in parts:
                if part.endswith('d'):
                    total_seconds += int(part[:-1]) * 86400
                elif part.endswith('h'):
                    total_seconds += int(part[:-1]) * 3600
                elif part.endswith('m'):
                    total_seconds += int(part[:-1]) * 60
                
            if total_seconds < 60:
                return await inter.response.send_message(
                    "❌ Минимальная длительность розыгрыша - 1 минута",
                    ephemeral=True
                )
            
            end_time = datetime.now() + timedelta(seconds=total_seconds)
        
            # Создание эмбеда
            embed = disnake.Embed(
                title="🎉 РОЗЫГРЫШ",
                description=(
                    f"**Приз:** {prize}\n"
                    f"**Победителей:** {winners}\n"
                    f"**Заканчивается:** <t:{int(end_time.timestamp())}:R>\n"
                    f"{description if description else ''}\n"
                    "Нажмите на 🎉 чтобы участвовать!"
                ),
                color=0xC0C0C0
            )
            embed.set_footer(text=f"Розыгрыш от {inter.author.name}")
        
            # Добавление изображения, если URL предоставлен
            if image_url:
                embed.set_image(url=image_url)
        
            # Отправка сообщения
            message = await inter.channel.send(embed=embed)
            await message.add_reaction("🎉")
        
            # Сохранение данных розыгрыша
            await self.giveaway_manager.save_giveaway(
                message.id,
                {
                    'prize': prize,
                    'winners': winners,
                    'end_time': end_time.timestamp(),
                    'channel_id': inter.channel.id,
                    'guild_id': inter.guild.id,
                    'host_id': inter.author.id,
                    'ended': False
                }
            )
        
            await inter.response.send_message(
                "✅ Розыгрыш успешно создан!",
                ephemeral=True
            )
        
        except Exception as e:
            await inter.response.send_message(
                f"❌ Ошибка при создании розыгрыша: {str(e)}",
                ephemeral=True
            )

    @commands.slash_command(name="reroll")
    @commands.has_permissions(administrator=True)
    async def reroll(
        self,
        inter: disnake.ApplicationCommandInteraction,
        message_id: str,
        winners: int = 1
    ):
        """Выбрать новых победителей
        
        Parameters
        ----------
        message_id: ID сообщения с розыгрышем
        winners: Количество новых победителей
        """
        try:
            message = await inter.channel.fetch_message(int(message_id))
            reaction = disnake.utils.get(message.reactions, emoji="🎉")
            
            if not reaction:
                return await inter.response.send_message(
                    "❌ Не найдена реакция розыгрыша",
                    ephemeral=True
                )
                
            users = [user async for user in reaction.users() if not user.bot]
            
            if len(users) < winners:
                return await inter.response.send_message(
                    "❌ Недостаточно участников для выбора победителей",
                    ephemeral=True
                )
                
            new_winners = random.sample(users, winners)
            
            await inter.response.send_message(
                f"🎉 Новые победители: {', '.join(w.mention for w in new_winners)}!"
            )
            
        except Exception as e:
            await inter.response.send_message(
                f"❌ Ошибка при перевыборе победителей: {str(e)}",
                ephemeral=True
            )

    @tasks.loop(minutes=1)
    async def check_giveaways(self):
        """Проверка завершенных розыгрышей"""
        try:
            giveaways = await self.giveaway_manager.load_giveaways()
            current_time = datetime.now().timestamp()
            
            for message_id, data in giveaways.items():
                if not data['ended'] and current_time >= data['end_time']:
                    try:
                        guild = self.bot.get_guild(data['guild_id'])
                        if not guild:
                            continue
                            
                        channel = guild.get_channel(data['channel_id'])
                        if not channel:
                            continue
                            
                        message = await channel.fetch_message(int(message_id))
                        if not message:
                            continue
                            
                        reaction = disnake.utils.get(message.reactions, emoji="🎉")
                        if not reaction:
                            continue
                            
                        users = [user async for user in reaction.users() if not user.bot]
                        
                        if not users:
                            await channel.send(f"❌ Розыгрыш завершен, но никто не участвовал! Приз: {data['prize']}")
                        else:
                            winners = random.sample(users, min(data['winners'], len(users)))
                            await channel.send(
                                f"🎉 Розыгрыш завершен! Приз: {data['prize']}\n"
                                f"Победители: {', '.join(w.mention for w in winners)}!"
                            )
                            
                        # Обновление эмбеда
                        embed = message.embeds[0]
                        embed.description = embed.description.replace(
                            "Нажмите на 🎉 чтобы участвовать!",
                            "Розыгрыш завершен!"
                        )
                        await message.edit(embed=embed)
                        
                        # Отмечаем розыгрыш как завершенный
                        data['ended'] = True
                        await self.giveaway_manager.save_giveaway(int(message_id), data)
                        
                    except Exception as e:
                        print(f"Ошибка при завершении розыгрыша {message_id}: {e}")
                        
        except Exception as e:
            print(f"Ошибка при проверке розыгрышей: {e}")

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(GiveawayCog(bot))