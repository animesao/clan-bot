import discord
from discord import app_commands
from discord.ext import commands
import random

class NumberGuess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    @app_commands.command(
        name="угадай",
        description="Начать игру в угадывание числа"
    )
    @app_commands.describe(
        max_number="Максимальное число (по умолчанию 100)"
    )
    async def start_guess(self, interaction: discord.Interaction, max_number: int = 100):
        """Начать игру в угадывание числа."""
        if max_number < 10:
            await interaction.response.send_message('Пожалуйста, выберите число больше 10!', ephemeral=True)
            return
        if max_number > 1000:
            await interaction.response.send_message('Пожалуйста, выберите число меньше 1000!', ephemeral=True)
            return

        number = random.randint(1, max_number)
        self.active_games[interaction.user.id] = {
            'number': number,
            'max': max_number,
            'attempts': 0
        }

        embed = discord.Embed(
            title="🎯 Игра в угадывание числа",
            description=f"Я загадал число от 1 до {max_number}!\nИспользуйте `/число <ваше предположение>` чтобы играть!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="число",
        description="Сделать предположение в игре угадывания числа"
    )
    @app_commands.describe(
        guess="Ваше предположение"
    )
    async def make_guess(self, interaction: discord.Interaction, guess: int):
        """Сделать предположение в игре угадывания числа."""
        if interaction.user.id not in self.active_games:
            await interaction.response.send_message("Вы еще не начали игру! Используйте `/угадай` чтобы начать.", ephemeral=True)
            return

        game = self.active_games[interaction.user.id]
        game['attempts'] += 1

        if guess < 1 or guess > game['max']:
            await interaction.response.send_message(f"Пожалуйста, угадайте число от 1 до {game['max']}!", ephemeral=True)
            return

        if guess == game['number']:
            embed = discord.Embed(
                title="🎉 Поздравляем!",
                description=f"Вы угадали число за {game['attempts']} попыток!",
                color=discord.Color.gold()
            )
            del self.active_games[interaction.user.id]
        elif guess < game['number']:
            embed = discord.Embed(
                title="📈 Слишком мало!",
                description="Попробуйте число побольше!",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="📉 Слишком много!",
                description="Попробуйте число поменьше!",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="сдаюсь",
        description="Сдаться в текущей игре угадывания числа"
    )
    async def give_up(self, interaction: discord.Interaction):
        """Сдаться в текущей игре угадывания числа."""
        if interaction.user.id not in self.active_games:
            await interaction.response.send_message("У вас нет активной игры!", ephemeral=True)
            return

        game = self.active_games[interaction.user.id]
        embed = discord.Embed(
            title="Игра окончена!",
            description=f"Загаданное число было {game['number']}!\nВы сделали {game['attempts']} попыток.",
            color=discord.Color.dark_red()
        )
        del self.active_games[interaction.user.id]
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(NumberGuess(bot)) 