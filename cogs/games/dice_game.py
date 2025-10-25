import discord
from discord import app_commands
from discord.ext import commands
import random

class DiceGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="кубик",
        description="Бросить кубики в формате NdN (например: 2d6)"
    )
    @app_commands.describe(
        dice="Формат броска (например: 2d6 для двух шестигранных кубиков)"
    )
    async def roll_dice(self, interaction: discord.Interaction, dice: str = '1d6'):
        """Бросить кубики в формате NdN."""
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            await interaction.response.send_message('Формат должен быть NdN!', ephemeral=True)
            return

        if rolls > 25:
            await interaction.response.send_message('Слишком много кубиков! Максимум 25.', ephemeral=True)
            return
        if limit > 100:
            await interaction.response.send_message('Слишком много граней! Максимум 100.', ephemeral=True)
            return

        results = [random.randint(1, limit) for r in range(rolls)]
        total = sum(results)
        
        embed = discord.Embed(
            title="🎲 Результаты броска",
            color=discord.Color.blue()
        )
        embed.add_field(name="Броски", value=f"{', '.join(map(str, results))}", inline=False)
        embed.add_field(name="Сумма", value=str(total), inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(DiceGame(bot)) 