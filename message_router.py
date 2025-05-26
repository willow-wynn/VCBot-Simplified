"""
Backward compatibility layer for MessageRouter.
This maintains the same interface as the original MessageRouter class but delegates to the simplified handlers.
"""

import discord
from typing import Dict, Callable, Optional, List, Any
from dataclasses import dataclass, field
import asyncio
import re

@dataclass
class MessageHandler:
    """Message handler wrapper for compatibility."""
    func: Callable[[discord.Message, Any], None]
    conditions: List[Callable[[discord.Message], bool]] = field(default_factory=list)
    description: str = ""

class MessageRouter:
    """Backward compatibility MessageRouter that delegates to bot.py handlers."""
    
    def __init__(self):
        self._channel_handlers: Dict[int, List[MessageHandler]] = {}
        self._global_handlers: List[MessageHandler] = []
    
    def register_channel(self, channel_id: int, conditions: List[Callable] = None):
        """Decorator to register a channel-specific handler."""
        def decorator(func):
            handler = MessageHandler(
                func=func,
                conditions=conditions or [],
                description=f"Handler for channel {channel_id}"
            )
            
            if channel_id not in self._channel_handlers:
                self._channel_handlers[channel_id] = []
            self._channel_handlers[channel_id].append(handler)
            
            return func
        return decorator
    
    def register_global(self, conditions: List[Callable] = None):
        """Decorator to register a global handler."""
        def decorator(func):
            handler = MessageHandler(
                func=func,
                conditions=conditions or [],
                description="Global message handler"
            )
            self._global_handlers.append(handler)
            return func
        return decorator
    
    def add_channel_handler(self, channel_id: int, handler: MessageHandler):
        """Add a channel handler programmatically."""
        if channel_id not in self._channel_handlers:
            self._channel_handlers[channel_id] = []
        self._channel_handlers[channel_id].append(handler)
    
    async def route(self, message: discord.Message, bot_state=None) -> None:
        """Route message to appropriate handlers."""
        # For backward compatibility, delegate to the simplified handlers in bot.py
        from bot import handle_message
        await handle_message(message)
    
    async def _should_execute(self, handler: MessageHandler, message: discord.Message) -> bool:
        """Check if handler should execute based on conditions."""
        try:
            for condition in handler.conditions:
                if asyncio.iscoroutinefunction(condition):
                    if not await condition(message):
                        return False
                else:
                    if not condition(message):
                        return False
            return True
        except Exception:
            return False
    
    async def _execute_handler(self, handler: MessageHandler, message: discord.Message, bot_state=None) -> None:
        """Execute a message handler safely."""
        try:
            if asyncio.iscoroutinefunction(handler.func):
                await handler.func(message, bot_state)
            else:
                handler.func(message, bot_state)
        except Exception as e:
            print(f"Error in message handler {handler.description}: {e}")

# Create router instance for compatibility
router = MessageRouter()

# Condition functions for compatibility
def not_bot_message(message: discord.Message) -> bool:
    """Condition: message is not from a bot."""
    return not message.author.bot

def contains_google_docs(message: discord.Message) -> bool:
    """Condition: message contains Google Docs link."""
    return "docs.google.com" in message.content

# Handler functions for compatibility - these delegate to bot.py
async def handle_clerk_message(message: discord.Message, bot_state=None):
    """Handle clerk channel messages."""
    from bot import handle_clerk_message
    await handle_clerk_message(message)

async def handle_news_message(message: discord.Message, bot_state=None):
    """Handle news channel messages."""
    from bot import handle_news_message  
    await handle_news_message(message)

async def handle_sign_message(message: discord.Message, bot_state=None):
    """Handle bill signing messages."""
    from bot import handle_sign_message
    await handle_sign_message(message)