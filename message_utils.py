"""
Simple message utilities for VCBot.
Replaces the complex ResponseFormatter class with direct functions.
"""

import discord
from typing import List, Optional
from io import StringIO
from pathlib import Path
from config import Limits

def sanitize_text(text: str) -> str:
    """Sanitize text to prevent mass pings while preserving user mentions."""
    if not text:
        return ""
    
    # Only sanitize mass ping mentions, preserve individual user mentions
    return (text.replace("@everyone", "@ everyone")
               .replace("@here", "@ here")
               .replace("<@&", "< @&"))  # Only sanitize role mentions, not user mentions

def chunk_text(text: str, max_length: int = Limits.MAX_MESSAGE_LENGTH) -> List[str]:
    """Split text into Discord-safe chunks."""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by lines to avoid breaking mid-sentence
    lines = text.split('\n')
    
    for line in lines:
        if len(line) > max_length:
            # Add current chunk if it has content
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # Split the long line
            while len(line) > max_length:
                chunks.append(line[:max_length])
                line = line[max_length:]
            
            current_chunk = line
        else:
            test_chunk = current_chunk + ('\n' if current_chunk else '') + line
            
            if len(test_chunk) > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk = test_chunk
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

async def send_response(interaction: discord.Interaction, 
                       text: str, 
                       user_mention: str = None,
                       query: str = None,
                       force_file: bool = False,
                       completion_message: str = "Complete."):
    """Send a response to Discord, handling chunking and files."""
    
    # Send completion notification first
    await interaction.followup.send(completion_message, ephemeral=True)
    
    # Send query header if provided
    if query and user_mention:
        truncated_query = query[:1900] if len(query) > 1900 else query
        query_header = f"Query from {user_mention}: {truncated_query}\n\nResponse:"
        safe_header = sanitize_text(query_header)
        if len(safe_header) > Limits.MAX_MESSAGE_LENGTH:
            safe_header = safe_header[:Limits.MAX_MESSAGE_LENGTH-3] + "..."
        await interaction.channel.send(safe_header)
    
    # Sanitize the text
    safe_text = sanitize_text(text)
    
    # Determine if we should use a file
    should_use_file = force_file or len(safe_text) > 30000
    chunks = chunk_text(safe_text)
    if len(chunks) > 5:
        should_use_file = True
    
    if should_use_file:
        # Send as file attachment
        file_obj = discord.File(StringIO(safe_text), filename="response.txt")
        await interaction.channel.send("Response attached as file due to length.", file=file_obj)
    else:
        # Send as text chunks
        for chunk in chunks:
            await interaction.channel.send(chunk)

async def send_pdf_attachments(interaction: discord.Interaction, pdf_paths: List[str]):
    """Send PDF file attachments."""
    if not pdf_paths:
        return
    
    print(f"Sending {len(pdf_paths)} PDF attachments")
    
    for pdf_path in pdf_paths:
        try:
            pdf_file = Path(pdf_path)
            if pdf_file.exists() and pdf_file.stat().st_size > 0:
                # Discord 25MB limit
                if pdf_file.stat().st_size > 25 * 1024 * 1024:
                    await interaction.followup.send(
                        f"📄 **{pdf_file.stem}** - File too large to attach (>25MB)",
                        ephemeral=False
                    )
                else:
                    with open(pdf_file, 'rb') as f:
                        discord_file = discord.File(f, filename=pdf_file.name)
                        await interaction.followup.send(
                            f"📄 **{pdf_file.stem}**",
                            file=discord_file,
                            ephemeral=False
                        )
            else:
                print(f"PDF file not found or empty: {pdf_path}")
                
        except Exception as e:
            print(f"Failed to send PDF attachment {pdf_path}: {e}")
            await interaction.followup.send(
                f"❌ Failed to attach PDF: {Path(pdf_path).name}",
                ephemeral=True
            )

async def send_error(interaction: discord.Interaction, error: Exception, message: str = "An error occurred"):
    """Send error message to user."""
    print(f"Error: {error}")
    
    error_msg = f"{message}: {error}"
    
    if interaction.response.is_done():
        await interaction.followup.send(error_msg, ephemeral=True)
    else:
        await interaction.response.send_message(error_msg, ephemeral=True)

def build_channel_context(channel_history: List[discord.Message], bot_id: int):
    """Build conversation context for Gemini from channel history."""
    from google.genai import types
    
    context = []
    for msg in reversed(channel_history):  # oldest first
        if not msg.content.strip() or msg.content.startswith("Complete."):
            continue
            
        is_bot = msg.author.id == bot_id
        
        # Special handling for "Query from" messages
        if is_bot and msg.content.startswith("Query from"):
            if ": " in msg.content:
                parts = msg.content.split(": ", 1)
                username_part = parts[0].replace("Query from ", "")
                query_text = parts[1]
                text_part = types.Part.from_text(text=f"{username_part}: {query_text}")
                role = 'user'
            else:
                text_part = types.Part.from_text(text=msg.content)
                role = 'user'
        elif is_bot:
            text_part = types.Part.from_text(text=msg.content)
            role = 'assistant'
        else:
            text_part = types.Part.from_text(text=f"{msg.author.display_name}: {msg.content}")
            role = 'user'
        
        context.append(types.Content(role=role, parts=[text_part]))
    
    return context

async def get_channel_history(channel: discord.TextChannel, limit: int = 50):
    """Get channel message history."""
    return [msg async for msg in channel.history(limit=limit)]