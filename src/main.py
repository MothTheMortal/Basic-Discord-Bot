import asyncio
from os import getenv
from dotenv import load_dotenv
import discord
from discord.ui import Button, view
from discord.ext import commands
from discord import app_commands
import config
import asyncio
from time import time

bot = commands.Bot(command_prefix="?", help_command=None, intents=discord.Intents.all())


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket to Verify!", style=discord.ButtonStyle.green, emoji="✅", custom_id="verify")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(config.VERIFY_ROLE_ID)
        for userRole in interaction.user.roles:
            if userRole.id == role.id:
                await interaction.response.send_message(f"You are already verified.", ephemeral=True)
                return
        await interaction.response.send_message("Verification Ticket Created", ephemeral=True)

        category: discord.CategoryChannel = discord.utils.get(interaction.guild.categories, name="TICKET")
        channel: discord.TextChannel = await interaction.guild.create_text_channel(name=f"Verification for {interaction.user.name}", category=category)

        overwrite = discord.PermissionOverwrite(**{
            "view_channel": True,
            "send_messages": True,
            "read_messages": True})

        await channel.set_permissions(interaction.user, overwrite=overwrite)

        embed = discord.Embed(title="How to Verify", description=f"Type '{config.VERIFICATION_MESSAGE}' to verify!")
        embed.set_footer(text="You have 30 seconds.")
        await channel.send(content=f"{interaction.user.mention}", embed=embed)

        def check(ctx: discord.Message):
            return ctx.channel == channel and ctx.author.id == interaction.user.id and ctx.content.lower() == config.VERIFICATION_MESSAGE.lower()

        try:
            msg: discord.Message = await bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await channel.send("**Verification Failed!**")
            await asyncio.sleep(0.5)
            await channel.delete()
        else:
            await channel.send("**Verified Successfully!**")
            await asyncio.sleep(0.5)
            await channel.delete()
            await msg.author.add_roles(role, reason="Verification")


@bot.event
async def on_ready():
    print(f"{bot.user.name} is online!")
    # synced = await bot.tree.sync()
    # print(f"{len(synced)} slash commands loaded!")

    # Constants
    bot.add_view(view=VerifyView())

    # Checks
    guild = bot.get_guild(config.GUILD_ID)
    categoryNames = [i.name for i in guild.categories]
    if config.TICKET_CATEGORY_NAME not in categoryNames:
        overwrite = discord.PermissionOverwrite(**{
            "view_channel": False,
            "send_messages": False,
            "read_messages": False})

        category: discord.CategoryChannel = await guild.create_category(name="TICKET", overwrites={guild.default_role: overwrite})

    verifyChannel = bot.get_channel(config.VERIFY_CHANNEL_ID)
    if verifyChannel:
        if len([i async for i in verifyChannel.history() if i.author.id == bot.user.id]) < 1:  # Sends the Verify button if it doesn't exist
            await verifyChannel.send(content="", view=VerifyView())


@bot.tree.command(name="chat", description="Command used to talk as the bot.")
async def chat(ctx, channel: discord.TextChannel, msg: str):

    if not ctx.user.guild_permissions.manage_messages:
        return await ctx.response.send_message("**You do not have the necessary permission to run this command.**", ephemeral=True)

    await channel.send(msg)
    await ctx.response.send_message(f"Message sent in {channel.mention}", ephemeral=True)


@bot.tree.command(name="create-ticket", description="Command used to create a ticket to talk with staff.")
async def createTicket(ctx: discord.Interaction, reason: str):

    category: discord.CategoryChannel = discord.utils.get(ctx.guild.categories, name="TICKET")
    ticketChannelNames = [channel.name for channel in category.channels if channel.name.startswith("ticket")]
    if f"ticket-for-{ctx.user.name.lower()}" in ticketChannelNames:
        return await ctx.response.send_message("**You cannot create more than one ticket at the same time**", ephemeral=True)


    await ctx.response.send_message("Ticket Created", ephemeral=True)

    channel: discord.TextChannel = await ctx.guild.create_text_channel(name=f"Ticket for {ctx.user.name}", category=category)
    overwrite = discord.PermissionOverwrite(**{
        "view_channel": True,
        "send_messages": True,
        "read_messages": True})

    await channel.set_permissions(ctx.user, overwrite=overwrite)

    embed = discord.Embed(title=f"{ctx.user.name} created a Ticket!", description=f"**Reason**: {reason}")
    await channel.send(content=f"{f'<@&{config.STAFF_ROLE_ID}>' if config.STAFF_ROLE_ID else ''}", embed=embed)


@bot.tree.command(name="close-ticket", description="Command used to close an active ticket.")
async def closeTicket(ctx: discord.Interaction):

    if not ctx.user.guild_permissions.manage_messages:
        return await ctx.response.send_message("**You do not have the necessary permission to run this command.**", ephemeral=True)

    if ctx.channel.name.startswith("ticket-for"):
        await ctx.response.send_message("**Closing Ticket...**")
        await asyncio.sleep(1)
        await ctx.channel.delete(reason="Resolved Ticket")
    else:
        await ctx.response.send_message("Invalid Channel", ephemeral=True)


if __name__ == "__main__":
    load_dotenv()
    bot.run(getenv("BOT_TOKEN"))
