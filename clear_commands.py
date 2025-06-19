#!/usr/bin/env python3
"""
Clear all Discord slash commands - both guild and global.
Run this script to remove old/deprecated commands from Discord.
"""

import discord
from discord import app_commands
import asyncio
import config

async def clear_all_commands():
    """Clear all commands from Discord - both guild and global."""
    
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    
    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        
        try:
            # Clear guild commands if GUILD_ID is set
            if config.GUILD_ID:
                guild = discord.Object(id=config.GUILD_ID)
                print(f"Clearing commands from guild {config.GUILD_ID}...")
                
                # Clear guild commands
                tree.clear_commands(guild=guild)
                synced = await tree.sync(guild=guild)
                print(f"✅ Guild commands cleared. Sync returned {len(synced)} commands (should be 0)")
                
            # Clear global commands
            print("Clearing global commands...")
            tree.clear_commands(guild=None)  # Explicitly pass None for global
            synced_global = await tree.sync(guild=None)  # Sync globally with None
            print(f"✅ Global commands cleared. Sync returned {len(synced_global)} commands (should be 0)")
            
            # Also clear commands from any other guilds the bot is in
            print("\nChecking other guilds...")
            for guild in client.guilds:
                if config.GUILD_ID and guild.id == config.GUILD_ID:
                    continue  # Already cleared this one
                print(f"Clearing commands from guild {guild.id} ({guild.name})...")
                tree.clear_commands(guild=guild)
                await tree.sync(guild=guild)
                print(f"✅ Cleared commands from {guild.name}")
            
            print("\n✅ All commands cleared successfully!")
            print("Note: Discord caches global commands for up to 1 hour, so they may still appear briefly.")
            print("You can now restart your bot to register the current commands.")
            
        except Exception as e:
            print(f"❌ Error clearing commands: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await client.close()
    
    # Run the client
    await client.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    print("🧹 Clearing all Discord slash commands...")
    print("This will remove all old/deprecated commands from Discord.")
    print("Make sure your bot is offline before running this!\n")
    
    try:
        asyncio.run(clear_all_commands())
    except KeyboardInterrupt:
        print("\n⚠️ Script interrupted by user")
    except Exception as e:
        print(f"❌ Script failed: {e}")