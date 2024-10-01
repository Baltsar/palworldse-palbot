import nextcord
from nextcord.ext import commands
from nextcord import Interaction
import random
import time
import json
import os
from utils.palgame import (
    get_pals,
    add_experience,
    level_up
)
from utils.database import add_points
from utils.errorhandling import restrict_command

class AdventureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.pals = self.load_pals()

    def load_pals(self):
        with open(os.path.join('gamedata', 'game.json'), 'r') as file:
            return json.load(file)

    def check_cooldown(self, user_id):
        if user_id in self.cooldowns:
            time_elapsed = time.time() - self.cooldowns[user_id]
            cooldown_period = 6 * 60 * 60
            if time_elapsed < cooldown_period:
                return cooldown_period - time_elapsed
        return None

    def update_cooldown(self, user_id):
        self.cooldowns[user_id] = time.time()

    async def autocomplete_pals(self, interaction: nextcord.Interaction, current: str):
        user_pals = await get_pals(str(interaction.user.id))
        choices = []

        if current:
            choices = [pal[0] for pal in user_pals if current.lower() in pal[0].lower()]
        else:
            top_pals = sorted(user_pals, key=lambda pal: pal[1], reverse=True)[:5]
            choices = [pal[0] for pal in top_pals]

        if interaction.response.is_done():
            return

        await interaction.response.send_autocomplete(choices=choices[:10])

    def get_pal_image(self, pal_name):
        for pal in self.pals:
            if pal['Name'] == pal_name:
                return pal.get('WikiImage')
        return None

    @nextcord.slash_command(name="adventure", description="Send one of your Pals on an adventure!")
    @restrict_command()
    async def adventure(
        self,
        interaction: Interaction,
        pal_name: str = nextcord.SlashOption(description="Choose your Pal", autocomplete=True)
    ):
        user_id = str(interaction.user.id)

        remaining_time = self.check_cooldown(user_id)
        if remaining_time is not None:
            remaining_hours = int(remaining_time // 3600)
            remaining_minutes = int((remaining_time % 3600) // 60)
            await interaction.response.send_message(
                f"Your Pal is still recovering from their last adventure! Please wait {remaining_hours} hours and {remaining_minutes} minutes.",
                ephemeral=True
            )
            return

        user_pals = await get_pals(user_id)
        if pal_name not in [pal[0] for pal in user_pals]:
            await interaction.response.send_message("You don't have this Pal! Please select one of your own Pals.", ephemeral=True)
            return

        pal_image = self.get_pal_image(pal_name)

        self.update_cooldown(user_id)

        currency_earned = random.randint(50, 200)
        experience_gained = random.randint(100, 500)
        await add_experience(user_id, pal_name, experience_gained)

        leveled_up = await level_up(user_id, pal_name)

        await add_points(user_id, interaction.user.name, currency_earned)

        description = f"Your Pal {pal_name} returned from an adventure and earned {currency_earned} coins and gained {experience_gained} experience!"
        if leveled_up:
            description += f"\n🎉 {pal_name} leveled up!"

        embed = nextcord.Embed(
            title="Adventure Successful!",
            description=description,
            color=nextcord.Color.green()
        )
        if pal_image:
            embed.set_thumbnail(url=pal_image)

        await interaction.response.send_message(embed=embed)

    @adventure.on_autocomplete("pal_name")
    async def autocomplete_pal_name(self, interaction: nextcord.Interaction, current: str):
        if interaction.guild is None:
            return []
        
        await self.autocomplete_pals(interaction, current)

def setup(bot):
    bot.add_cog(AdventureCog(bot))

    if not hasattr(bot, "all_slash_commands"):
        bot.all_slash_commands = []
    bot.all_slash_commands.extend(
        [
            AdventureCog.adventure
        ]
    )
