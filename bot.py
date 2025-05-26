"""
VCBot - Simplified Discord Bot for Virtual Congress
Main bot file with all Discord commands and message handling.
"""

import discord
from discord import app_commands
import asyncio
import aiohttp
import re
import csv
from typing import Literal
from functools import wraps
from pathlib import Path

# Import our simplified modules
import config
import ai_tools
import bill_utils
import message_utils
import file_utils

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Global variables (replacing complex state management)
discord_channels = {}

# Decorators for permissions and channel restrictions
def has_any_role(*role_names):
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if not any(role.name in role_names for role in interaction.user.roles):
                await interaction.response.send_message(config.Messages.PERMISSION_DENIED_AI_ACCESS, ephemeral=True)
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

def limit_to_channels(channel_ids: list, exempt_roles=[config.Roles.ADMIN]):
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if exempt_roles and any(role.name in exempt_roles for role in interaction.user.roles):
                return await func(interaction, *args, **kwargs)
            if interaction.channel.id not in channel_ids:
                await interaction.response.send_message(config.Messages.CHANNEL_RESTRICTED, ephemeral=True)
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

def handle_errors(error_message: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                print(f"Error in {func.__name__}: {e}")
                # Get interaction from args
                interaction = args[0] if args and hasattr(args[0], 'response') else None
                if interaction:
                    await message_utils.send_error(interaction, e, error_message)
                raise
        return wrapper
    return decorator

# Discord Commands

@tree.command(name="helper", description="Query the VCBot helper.")
@has_any_role(config.Roles.ADMIN, config.Roles.AI_ACCESS)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to process query")
async def helper(interaction: discord.Interaction, query: str):
    """AI assistance using Gemini."""
    print(f"Helper command: {interaction.user.display_name} asked: {query}")
    await interaction.response.defer(ephemeral=False)
    
    # Get channel history for context
    history = await message_utils.get_channel_history(interaction.channel, config.Limits.MAX_MESSAGES_HISTORY)
    context = message_utils.build_channel_context(history, config.BOT_ID)
    
    # Add current query to context
    from google.genai import types
    context.append(types.Content(
        role='user',
        parts=[types.Part.from_text(text=f"{interaction.user.display_name}: {query}")]
    ))
    
    # Process with AI
    ai_response = await ai_tools.process_ai_query(query, context, interaction.user.id, client)
    
    # Send response
    completion_msg = f"Complete. Input tokens: {ai_response['input_tokens']}, Output tokens: {ai_response['output_tokens']}"
    
    await message_utils.send_response(
        interaction,
        ai_response['text'],
        interaction.user.mention,
        query,
        completion_message=completion_msg
    )
    
    # Send PDF attachments if present
    if ai_response.get('pdf_attachments'):
        await message_utils.send_pdf_attachments(interaction, ai_response['pdf_attachments'])
    
    # Log query
    await file_utils.save_query_log(query, ai_response['text'])

@tree.command(name="bill_keyword_search", description="Perform a basic keyword search on the legislative corpus.")
@has_any_role(config.Roles.ADMIN, config.Roles.AI_ACCESS)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to search bills")
async def bill_keyword_search(interaction: discord.Interaction, search_query: str):
    """Search bills by keywords and attach PDFs."""
    await interaction.response.defer(ephemeral=False)
    
    # Search bills
    results = bill_utils.search_bills_keyword(search_query, 5)
    
    # Send completion message
    completion_message = f"Complete. Found {len(results)} bills matching your query."
    await interaction.followup.send(completion_message, ephemeral=True)
    
    # Send query header
    query_header = f"Query from {interaction.user.mention}: Search bills for '{search_query}'\n\nResults:"
    safe_header = message_utils.sanitize_text(query_header)
    await interaction.channel.send(safe_header)
    
    # Send PDF files
    for result in results:
        pdf_path = config.BILL_PDF_DIR / f"{result['filename']}.pdf"
        if pdf_path.exists():
            await interaction.channel.send(file=discord.File(pdf_path))

@tree.command(name="reference", description="reference a bill")
@has_any_role(config.Roles.ADMIN, config.Roles.REPRESENTATIVE, config.Roles.HOUSE_CLERK, config.Roles.MODERATOR)
@handle_errors("Failed to reference bill")
async def reference(interaction: discord.Interaction, link: str, type: Literal["hr", "hres", "hjres", "hconres"]):
    """Assign a reference number to a bill."""
    print(f"Reference command: {interaction.user.display_name} referencing {link} as {type}")
    
    # Get next reference number
    next_val = file_utils.get_next_reference(type)
    
    # Send success message
    await interaction.response.send_message(
        f"The bill {link} has been referenced successfully as {type.upper()} {next_val}.",
        ephemeral=True
    )
    
    # Announce in clerk channel
    clerk_channel = client.get_channel(config.CLERK_ANNOUNCE_CHANNEL)
    if clerk_channel:
        await clerk_channel.send(f'Bill {link} assigned reference {type.upper()} {next_val}')

@tree.command(name="modifyrefs", description="modify reference numbers")
@has_any_role(config.Roles.ADMIN, config.Roles.HOUSE_CLERK)
@handle_errors("Failed to modify reference")
async def modifyref(interaction: discord.Interaction, num: int, type: str):
    """Modify reference numbers."""
    print(f"Modify refs: {interaction.user.display_name} setting {type} to {num}")
    
    # Set reference number
    file_utils.set_reference(type, num)
    
    # Send success message
    await interaction.response.send_message(
        f"Reference number modified for {type.upper()}: {num}",
        ephemeral=False
    )

@tree.command(name="add_bill", description="Add a bill to the legislative corpus.")
@has_any_role(config.Roles.ADMIN)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to add bill")
async def add_bill(interaction: discord.Interaction, bill_link: str, database_type: Literal["bills"] = "bills"):
    """Add a bill to the corpus from a Google Doc link."""
    print(f"Add bill: {interaction.user.display_name} adding {bill_link}")
    await interaction.response.defer(ephemeral=False)
    
    # Add bill
    result = await bill_utils.add_bill_to_corpus(bill_link)
    
    if result['success']:
        # Send the bill file
        await interaction.channel.send(file=discord.File(result['file_path']))
        await interaction.followup.send(
            f"Complete. Added bill `{result['title']}` to `{database_type}` database.",
            ephemeral=True
        )
    else:
        raise Exception(f"Failed to add bill: {result['error']}")

@tree.command(name="econ_impact_report", description="Get a detailed economic impact report on a given piece of legislation.")
@has_any_role(config.Roles.ADMIN, config.Roles.EVENTS_TEAM)
@limit_to_channels([config.BOT_HELPER_CHANNEL])
@handle_errors("Failed to generate economic impact report")
async def econ_impact_report(interaction: discord.Interaction, bill_link: str, additional_context: str = None):
    """Generate economic impact report for a bill."""
    print(f"Economic impact report: {interaction.user.display_name} for {bill_link}")
    await interaction.response.defer(ephemeral=False)
    
    # Get recent news
    news_channel = discord_channels.get('news')
    recent_news = []
    if news_channel:
        news_history = await message_utils.get_channel_history(news_channel, config.Limits.MAX_MESSAGES_HISTORY)
        recent_news = [msg.content for msg in news_history if msg.content.strip()]
    
    # Generate report
    report_text = await bill_utils.generate_economic_impact_report(
        bill_link, recent_news, additional_context
    )
    
    # Send response as file
    query_header = f"Query from {interaction.user.mention}: Generate economic impact report on {bill_link}.\n\nResponse:"
    
    await message_utils.send_response(
        interaction,
        report_text,
        interaction.user.mention,
        f"Generate economic impact report on {bill_link}",
        force_file=True,
        completion_message="Complete. Economic impact report generated."
    )
    
    # Log query
    await file_utils.save_query_log(f'Generate economic impact report on {bill_link}', report_text)

@tree.command(name="role", description="Add a role to one or more users.")
@handle_errors("Failed to manage roles")
async def role(interaction: discord.Interaction, users: str, *, role: str):
    """Add or remove roles for users."""
    await interaction.response.defer(ephemeral=False)
    
    remove = role[0] == "-"
    clean_role = role.removeprefix("-").removeprefix("@").strip()

    # Check permissions
    allowed_roles = []
    for r in interaction.user.roles:
        if r.name in config.ALLOWED_ROLES_FOR_ROLES:
            allowed_roles.extend(config.ALLOWED_ROLES_FOR_ROLES[r.name])

    if clean_role not in allowed_roles:
        raise Exception(f"You do not have permission to add the role '{clean_role}'.")

    target_role = discord.utils.get(interaction.guild.roles, name=clean_role)
    if not target_role:
        raise Exception(f"Role '{clean_role}' not found in this server.")

    # Extract user IDs
    user_ids = re.findall(r"\d+", users)
    if not user_ids:
        raise Exception("No valid users specified. Please mention users or provide user IDs.")

    # Get members
    members = []
    for uid in dict.fromkeys(user_ids):  # Remove duplicates
        member = interaction.guild.get_member(int(uid))
        if member:
            members.append(member)

    if not members:
        raise Exception("Couldn't resolve any members from the provided user IDs.")

    # Apply role changes
    try:
        for m in members:
            if remove:
                await m.remove_roles(target_role)
            else:
                await m.add_roles(target_role)
    except discord.Forbidden:
        raise Exception("Bot lacks permission to manage roles. Please check bot role hierarchy.")
    except discord.HTTPException as e:
        raise Exception(f"Discord API error: {str(e)}")

    mentions = ", ".join(m.mention for m in members)
    await interaction.followup.send(
        f"{'Removed' if remove else 'Added'} role {clean_role} "
        f"{'from' if remove else 'to'} {mentions}."
    )

# Message Handlers (replacing complex MessageRouter)

async def handle_message(message: discord.Message):
    """Handle incoming messages."""
    if message.author.bot:
        return
    
    # Clerk channel - bill reference processing
    if message.channel.id == config.CLERK_CHANNEL:
        await handle_clerk_message(message)
    
    # News channel - append to news file
    elif message.channel.id == config.NEWS_CHANNEL:
        await handle_news_message(message)
    
    # Sign channel - process Google Docs
    elif message.channel.id == config.SIGN_CHANNEL and "docs.google.com" in message.content:
        await handle_sign_message(message)

async def handle_clerk_message(message: discord.Message):
    """Process clerk channel messages for bill references."""
    print(f"Processing clerk message from {message.author}")
    
    try:
        # Detect bill reference
        ref_update = bill_utils.detect_bill_reference(message.content)
        
        if ref_update['success']:
            # Update reference number
            updated_num = file_utils.get_next_reference(ref_update['bill_type'])
            print(f"Updated {ref_update['bill_type'].upper()} to {updated_num}")
            
    except Exception as e:
        print(f"Failed to process clerk message: {e}")

async def handle_news_message(message: discord.Message):
    """Append news messages to news file."""
    print(f"Appending news message to {config.NEWS_FILE}")
    
    try:
        await file_utils.append_file(str(config.NEWS_FILE), message.content + "\n")
    except Exception as e:
        print(f"Failed to append to news file: {e}")

async def handle_sign_message(message: discord.Message):
    """Handle bill signing with Google Docs links."""
    print(f"Processing bill signing from {message.author}")
    
    # Notify records channel
    records_channel = discord_channels.get('records')
    if records_channel:
        await records_channel.send(f'<@&1269061253964238919>, a new bill has been signed! {message.jump_url}')
    
    # Extract Google Doc link
    match = re.search(r"https?://docs\.google\.com/\S+", message.content)
    if match:
        doc_link = match.group(0)
        print(f"Found Google Doc link: {doc_link}")
        
        try:
            result = await bill_utils.add_bill_to_corpus(doc_link)
            if result['success']:
                print("Bill successfully added to database.")
            else:
                print(f"Failed to add bill: {result['error']}")
                if records_channel:
                    await records_channel.send(f"Error adding bill to database: {result['error']}")
        except Exception as e:
            print(f"Error adding bill: {e}")
            if records_channel:
                await records_channel.send("Unexpected error adding bill. Please check logs.")

# GitHub commit monitoring
async def check_github_commits():
    """Monitor GitHub for new commits."""
    await client.wait_until_ready()
    channel = client.get_channel(config.BOT_HELPER_CHANNEL)
    
    try:
        with open("last_commit.txt", "r") as f:
            last_commit_sha = f.read().strip()
    except FileNotFoundError:
        last_commit_sha = ""
    
    repo = "willow-wynn/VCBot"
    github_api_url = f"https://api.github.com/repos/{repo}/commits"
    github_url = "https://github.com/willow-wynn/VCBot"
    
    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            try:
                async with session.get(github_api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        latest_commit = data[0]
                        sha = latest_commit['sha']
                        
                        with open("last_commit.txt", "w") as f:
                            f.write(sha)
                        
                        if sha != last_commit_sha:
                            commit_msg = latest_commit['commit']['message']
                            commit_msg = message_utils.sanitize_text(commit_msg)
                            author = latest_commit['commit']['author']['name']
                            await channel.send(f"New commit to {repo}:\n**{commit_msg}** by {author}. \nSee it [here]({github_url}/commit/{sha})")
                            last_commit_sha = sha
                            
            except Exception as e:
                print(f"GitHub check failed: {e}")
            
            await asyncio.sleep(60)  # Check every minute

# Discord Events

@client.event
async def on_ready():
    """Bot startup initialization."""
    print(f"Logged in as {client.user}")
    
    # Initialize channels
    discord_channels['records'] = client.get_channel(config.RECORDS_CHANNEL)
    discord_channels['news'] = client.get_channel(config.NEWS_CHANNEL)
    discord_channels['sign'] = client.get_channel(config.SIGN_CHANNEL)
    discord_channels['clerk'] = client.get_channel(config.CLERK_CHANNEL)
    
    # Log channel status
    for name, channel in discord_channels.items():
        if channel:
            print(f"{name.title()} Channel: {channel.id}: {channel.name}")
        else:
            print(f"{name.title()} Channel: Not Found")
    
    # Start GitHub monitoring
    client.loop.create_task(check_github_commits())
    
    # Sync commands
    print("Syncing commands...")
    synced_commands = await tree.sync()
    print(f"Commands synced: {len(synced_commands)} commands" if synced_commands else "No commands to sync.")

@client.event
async def on_message(message):
    """Handle incoming messages."""
    try:
        await handle_message(message)
    except Exception as e:
        print(f"Error in message handler: {e}")

def main():
    """Main entry point."""
    print("Starting VCBot...")
    client.run(config.DISCORD_TOKEN)

if __name__ == "__main__":
    main()