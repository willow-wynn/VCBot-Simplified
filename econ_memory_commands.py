"""
Economic Memory Management Commands
Allows admins to manage economic analysis memory entries
"""

import discord
from discord import app_commands
from typing import Literal, Any
from datetime import datetime, timezone
from functools import wraps
import economic_utils
from config import Roles, BOT_HELPER_CHANNEL

def has_any_role(*roles):
    """Decorator to check if user has any of the specified roles"""
    def predicate(interaction: discord.Interaction) -> bool:
        if not hasattr(interaction.user, 'roles'):
            return False
        user_roles = [role.name for role in interaction.user.roles]
        return any(role in user_roles for role in roles)
    return app_commands.check(predicate)

def limit_to_channels(channel_ids):
    """Decorator to limit command to specific channels"""
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.channel_id in channel_ids
    return app_commands.check(predicate)

def handle_errors(error_message: str):
    """Decorator to handle command errors gracefully"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                interaction = args[0] if args else None
                if interaction and hasattr(interaction, 'followup'):
                    try:
                        await interaction.followup.send(f"❌ {error_message}: {str(e)}")
                    except:
                        print(f"Error in {func.__name__}: {e}")
                else:
                    print(f"Error in {func.__name__}: {e}")
        return wrapper
    return decorator

@app_commands.command(name="econ_memory_list", description="List all economic analysis memory entries")
@has_any_role(Roles.ADMIN, "RP Events Team")
@limit_to_channels([BOT_HELPER_CHANNEL])
@handle_errors("Failed to list memory entries")
async def econ_memory_list(interaction: discord.Interaction):
    """List all economic memory entries"""
    await interaction.response.defer()
    
    entries = economic_utils.econ_data.load_memory_entries()
    
    if not entries:
        await interaction.followup.send("📝 No economic memory entries found.")
        return
    
    # Create embed with memory entries
    embed = discord.Embed(
        title="🧠 Economic Analysis Memory",
        description=f"{len(entries)} memory entries",
        color=0x0099ff,
        timestamp=datetime.utcnow()
    )
    
    # Show entries in chunks to avoid embed limits
    entries_text = ""
    for entry in entries:
        entry_id = entry.get('id', 'Unknown')
        content = entry.get('content', '')[:100]  # Truncate long entries
        timestamp = entry.get('timestamp', 'Unknown')[:10]
        
        if len(content) > 100:
            content += "..."
        
        entry_line = f"**{entry_id}.** [{timestamp}] {content}\n"
        
        # Check if adding this line would exceed embed field limit
        if len(entries_text + entry_line) > 1024:
            embed.add_field(name="Memory Entries", value=entries_text.strip(), inline=False)
            entries_text = entry_line
        else:
            entries_text += entry_line
    
    # Add remaining entries
    if entries_text:
        embed.add_field(name="Memory Entries" if not embed.fields else "Memory Entries (continued)", value=entries_text.strip(), inline=False)
    
    embed.set_footer(text="Use /econ_memory to add or remove entries")
    
    await interaction.followup.send(embed=embed)

@app_commands.command(name="econ_memory", description="Add or remove economic analysis memory entries")
@app_commands.describe(
    action="Action to perform",
    content_or_id="Content to add (for add) or ID to remove (for remove)"
)
@has_any_role(Roles.ADMIN, "RP Events Team")
@limit_to_channels([BOT_HELPER_CHANNEL])
@handle_errors("Failed to manage memory entry")
async def econ_memory(interaction: discord.Interaction, action: Literal["add", "remove"], content_or_id: str):
    """Add or remove economic memory entries"""
    await interaction.response.defer()
    
    if action == "add":
        # Add new memory entry
        if not content_or_id.strip():
            await interaction.followup.send("❌ Memory content cannot be empty")
            return
        
        if len(content_or_id) > 500:
            await interaction.followup.send("❌ Memory content too long (max 500 characters)")
            return
        
        entry_id = economic_utils.econ_data.add_memory_entry(content_or_id.strip(), interaction.user.id)
        
        embed = discord.Embed(
            title="✅ Memory Entry Added",
            description=f"Added memory entry #{entry_id}",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Content", value=content_or_id.strip()[:500], inline=False)
        embed.add_field(name="Entry ID", value=str(entry_id), inline=True)
        embed.add_field(name="Added by", value=interaction.user.mention, inline=True)
        
        await interaction.followup.send(embed=embed)
        
        # Log the admin action
        economic_utils.log_admin_action(interaction.user.id, "add_memory", {"entry_id": entry_id, "content": content_or_id.strip()})
        
    elif action == "remove":
        # Remove memory entry by ID
        try:
            entry_id = int(content_or_id.strip())
        except ValueError:
            await interaction.followup.send("❌ Invalid entry ID. Must be a number.")
            return
        
        # Get entry details before removal
        entries = economic_utils.econ_data.load_memory_entries()
        entry_to_remove = next((entry for entry in entries if entry.get('id') == entry_id), None)
        
        if not entry_to_remove:
            await interaction.followup.send(f"❌ Memory entry #{entry_id} not found")
            return
        
        success = economic_utils.econ_data.remove_memory_entry(entry_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Memory Entry Removed",
                description=f"Removed memory entry #{entry_id}",
                color=0xff6b6b,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Removed Content", value=entry_to_remove.get('content', 'Unknown')[:500], inline=False)
            embed.add_field(name="Removed by", value=interaction.user.mention, inline=True)
            
            await interaction.followup.send(embed=embed)
            
            # Log the admin action
            economic_utils.log_admin_action(interaction.user.id, "remove_memory", {"entry_id": entry_id, "content": entry_to_remove.get('content', '')})
        else:
            await interaction.followup.send(f"❌ Failed to remove memory entry #{entry_id}")

# Integration instructions
def add_memory_commands_to_tree(tree):
    """Add memory management commands to the command tree"""
    tree.add_command(econ_memory_list)
    tree.add_command(econ_memory)
    print("✅ Added economic memory management commands")