import discord
from discord import app_commands
from discord.ext import commands
import random

class RockPaperScissors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.choices = ['камень', 'ножницы', 'бумага']
        self.emojis = {
            'камень': '🪨',
            'ножницы': '✂️',
            'бумага': '📄'
        }

    @app_commands.command(
        name="кнб",
        description="Сыграть в камень-ножницы-бумага"
    )
    @app_commands.describe(
        choice="Ваш выбор (камень, ножницы или бумага)"
    )
    @app_commands.choices(choice=[
        app_commands.Choice(name="камень", value="камень"),
        app_commands.Choice(name="ножницы", value="ножницы"),
        app_commands.Choice(name="бумага", value="бумага")
    ])
    async def play_rps(self, interaction: discord.Interaction, choice: str):
        """Сыграть в камень-ножницы-бумага с ботом."""
        bot_choice = random.choice(self.choices)
        
        # Определяем победителя
        result = self.determine_winner(choice, bot_choice)
        
        embed = discord.Embed(
            title="Камень Ножницы Бумага",
            color=self.get_result_color(result)
        )
        
        embed.add_field(
            name="Ваш выбор",
            value=f"{self.emojis[choice]} {choice.capitalize()}",
            inline=True
        )
        embed.add_field(
            name="Выбор бота",
            value=f"{self.emojis[bot_choice]} {bot_choice.capitalize()}",
            inline=True
        )
        embed.add_field(
            name="Результат",
            value=result,
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    def determine_winner(self, player_choice, bot_choice):
        if player_choice == bot_choice:
            return "🤝 Ничья!"
        
        winning_combinations = {
            'камень': 'ножницы',
            'ножницы': 'бумага',
            'бумага': 'камень'
        }
        
        if winning_combinations[player_choice] == bot_choice:
            return "🎉 Вы победили!"
        return "😢 Вы проиграли!"

    def get_result_color(self, result):
        if "победили" in result:
            return discord.Color.green()
        elif "проиграли" in result:
            return discord.Color.red()
        return discord.Color.blue()

async def setup(bot):
    await bot.add_cog(RockPaperScissors(bot)) 