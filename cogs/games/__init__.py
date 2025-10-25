from .dice_game import DiceGame
from .number_guess import NumberGuess
from .rock_paper_scissors import RockPaperScissors

async def setup(bot):
    await bot.add_cog(DiceGame(bot))
    await bot.add_cog(NumberGuess(bot))
    await bot.add_cog(RockPaperScissors(bot))

__all__ = ['DiceGame', 'NumberGuess', 'RockPaperScissors'] 