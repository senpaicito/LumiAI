import discord
from discord.ext import commands
import logging
import asyncio
import json
from config import settings

class LumiDiscordBot:
    def __init__(self, ai_engine, token=None):
        self.ai_engine = ai_engine
        self.token = token or settings.DISCORD_TOKEN
        self.command_prefix = settings.get('discord.command_prefix', '!')
        self.enabled = getattr(settings, 'DISCORD_ENABLED', True)
        self.logger = logging.getLogger(__name__)
        
        # If bot is disabled, don't set up Discord components
        if not self.enabled:
            self.logger.info("Discord bot is disabled in settings")
            self.bot = None
            return
        
        # Set up Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Create bot instance
        self.bot = commands.Bot(
            command_prefix=self.command_prefix,
            intents=intents,
            help_command=None
        )
        
        self.setup_handlers()
    
    def setup_handlers(self):
        # If bot is disabled, don't set up handlers
        if not self.enabled or self.bot is None:
            return
            
        @self.bot.event
        async def on_ready():
            self.logger.info(f'Discord bot logged in as {self.bot.user.name}')
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name="your conversations | !lumi help"
                )
            )
        
        @self.bot.event
        async def on_message(message):
            # Ignore messages from the bot itself
            if message.author == self.bot.user:
                return
            
            # Process commands first
            await self.bot.process_commands(message)
            
            # Respond to mentions
            if self.bot.user in message.mentions:
                await self.handle_mention(message)
        
        @self.bot.command(name='lumi')
        async def lumi_chat(ctx, *, message=None):
            """Chat with Lumi AI Companion"""
            if not message:
                await ctx.send(
                    "Hello! I'm Lumi, your AI companion. "
                    "You can mention me or use `!lumi [your message]` to chat with me!"
                )
                return
            
            async with ctx.typing():
                try:
                    response = await self.ai_engine.generate_response(message)
                    await ctx.send(response)
                except Exception as e:
                    self.logger.error(f"Discord chat error: {e}")
                    await ctx.send("I'm having trouble thinking right now. Please try again later.")
        
        @self.bot.command(name='lumi_help')
        async def lumi_help(ctx):
            """Show help information"""
            help_embed = discord.Embed(
                title="Lumi AI Companion - Help",
                description="Here's how to interact with me:",
                color=0x00ff00
            )
            
            help_embed.add_field(
                name="Chat Commands",
                value=(
                    "`!lumi [message]` - Chat with Lumi directly\n"
                    "`@Lumi [message]` - Mention Lumi in any channel\n"
                    "`!lumi_help` - Show this help message\n"
                    "`!lumi_info` - Get information about Lumi"
                ),
                inline=False
            )
            
            help_embed.add_field(
                name="About Lumi",
                value=(
                    "I'm an AI companion with a curious and empathetic personality. "
                    "I enjoy meaningful conversations and learning about humans!"
                ),
                inline=False
            )
            
            await ctx.send(embed=help_embed)
        
        @self.bot.command(name='lumi_info')
        async def lumi_info(ctx):
            """Get information about Lumi"""
            if self.ai_engine.character_data:
                character = self.ai_engine.character_data
                
                info_embed = discord.Embed(
                    title=f"About {character['name']}",
                    description=character['base_personality'],
                    color=0x0099ff
                )
                
                info_embed.add_field(
                    name="Traits",
                    value=", ".join(character['traits']),
                    inline=True
                )
                
                info_embed.add_field(
                    name="Likes",
                    value=", ".join(character['likes'][:3]) + "...",
                    inline=True
                )
                
                info_embed.add_field(
                    name="Speech Style",
                    value=character['speech_style'],
                    inline=False
                )
                
                await ctx.send(embed=info_embed)
            else:
                await ctx.send("I'm Lumi, your AI companion! Character information isn't available right now.")
    
    async def handle_mention(self, message):
        """Handle when the bot is mentioned"""
        # Extract message content without the mention
        content = message.clean_content.replace(f'@{self.bot.user.name}', '').strip()
        
        if not content:
            await message.reply("Hello! How can I help you today?")
            return
        
        async with message.channel.typing():
            try:
                response = await self.ai_engine.generate_response(content)
                await message.reply(response)
            except Exception as e:
                self.logger.error(f"Discord mention error: {e}")
                await message.reply("I'm having trouble thinking right now. Please try again later.")
    
    async def start(self):
        """Start the Discord bot"""
        if not self.enabled:
            self.logger.info("Discord bot is disabled in settings")
            return False
        
        if not self.token:
            self.logger.error("Discord bot token not provided")
            return False
        
        try:
            await self.bot.start(self.token)
            return True
        except Exception as e:
            self.logger.error(f"Failed to start Discord bot: {e}")
            return False
    
    async def stop(self):
        """Stop the Discord bot"""
        if self.bot and self.enabled:
            await self.bot.close()