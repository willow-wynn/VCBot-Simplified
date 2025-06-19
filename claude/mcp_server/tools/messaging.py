"""
Discord messaging tools for MCP server
"""

import os
import json
import aiohttp
from typing import Dict, Any, List, Optional
import config

class MessageTools:
    """Tools for Discord messaging operations"""
    
    def __init__(self):
        self.discord_token = os.getenv('DISCORD_TOKEN')
        self.base_url = "https://discord.com/api/v10"
        self.session = None
        
        # Channel name to ID mapping (these would be populated from config)
        self.channel_map = {
            "bot-helper": config.BOT_HELPER_CHANNEL,
            "official-rp-news": config.NEWS_CHANNEL,
            "records": config.RECORDS_CHANNEL,
            "clerk": config.CLERK_CHANNEL,
            # Add more channels as needed
        }
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            headers = {
                "Authorization": f"Bot {self.discord_token}",
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    def _get_channel_id(self, channel_name: str) -> Optional[str]:
        """Get channel ID from channel name"""
        return self.channel_map.get(channel_name)
    
    async def send_message(
        self,
        channel_name: str,
        content: str,
        embed_title: Optional[str] = None,
        embed_description: Optional[str] = None,
        embed_color: Optional[int] = 0x2ecc71
    ) -> Dict[str, Any]:
        """Send a message to a Discord channel"""
        
        channel_id = self._get_channel_id(channel_name)
        if not channel_id:
            return {
                "success": False,
                "error": f"Unknown channel: {channel_name}",
                "available_channels": list(self.channel_map.keys())
            }
        
        # For now, return a mock response
        # In production, this would use the Discord REST API
        response = {
            "success": True,
            "channel": channel_name,
            "channel_id": channel_id,
            "content": content,
            "message_id": "mock_message_id_1327483297202176080",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        if embed_title:
            response["embed"] = {
                "title": embed_title,
                "description": embed_description,
                "color": embed_color
            }
        
        # TODO: Implement actual Discord REST API call
        # session = await self._get_session()
        # url = f"{self.base_url}/channels/{channel_id}/messages"
        # data = {"content": content}
        # if embed_title:
        #     data["embeds"] = [{
        #         "title": embed_title,
        #         "description": embed_description,
        #         "color": embed_color
        #     }]
        # 
        # async with session.post(url, json=data) as resp:
        #     if resp.status == 200:
        #         result = await resp.json()
        #         return {
        #             "success": True,
        #             "message_id": result["id"],
        #             "channel": channel_name,
        #             "timestamp": result["timestamp"]
        #         }
        #     else:
        #         return {
        #             "success": False,
        #             "error": f"Discord API error: {resp.status}",
        #             "details": await resp.text()
        #         }
        
        return response
    
    async def get_channel_history(
        self,
        channel_name: str,
        limit: int = 20,
        search_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch recent messages from a Discord channel"""
        
        channel_id = self._get_channel_id(channel_name)
        if not channel_id:
            return [{
                "error": f"Unknown channel: {channel_name}",
                "available_channels": list(self.channel_map.keys())
            }]
        
        # Enforce reasonable limits
        limit = min(limit, 50)
        
        # Mock response for now
        mock_messages = [
            {
                "id": "123456789",
                "author": {
                    "username": "ExampleUser",
                    "display_name": "Example User",
                    "id": "987654321"
                },
                "content": f"Example message from {channel_name} channel",
                "timestamp": "2024-01-01T12:00:00Z",
                "edited_timestamp": None,
                "attachments": [],
                "embeds": [],
                "reactions": []
            },
            {
                "id": "123456790",
                "author": {
                    "username": "AnotherUser",
                    "display_name": "Another User",
                    "id": "987654322"
                },
                "content": "Another example message with some content to search",
                "timestamp": "2024-01-01T11:58:00Z",
                "edited_timestamp": None,
                "attachments": [],
                "embeds": [],
                "reactions": []
            }
        ]
        
        # Filter by search term if provided
        if search_term:
            filtered_messages = []
            for msg in mock_messages:
                if search_term.lower() in msg["content"].lower():
                    filtered_messages.append(msg)
            mock_messages = filtered_messages
        
        # TODO: Implement actual Discord REST API call
        # session = await self._get_session()
        # url = f"{self.base_url}/channels/{channel_id}/messages"
        # params = {"limit": limit}
        # 
        # async with session.get(url, params=params) as resp:
        #     if resp.status == 200:
        #         messages = await resp.json()
        #         
        #         # Filter by search term if provided
        #         if search_term:
        #             messages = [
        #                 msg for msg in messages
        #                 if search_term.lower() in msg["content"].lower()
        #             ]
        #         
        #         return messages[:limit]
        #     else:
        #         return [{
        #             "error": f"Discord API error: {resp.status}",
        #             "details": await resp.text()
        #         }]
        
        return mock_messages[:limit]
    
    async def reply_to_message(
        self,
        message_id: str,
        channel_name: str,
        content: str
    ) -> Dict[str, Any]:
        """Reply to a specific Discord message"""
        
        channel_id = self._get_channel_id(channel_name)
        if not channel_id:
            return {
                "success": False,
                "error": f"Unknown channel: {channel_name}",
                "available_channels": list(self.channel_map.keys())
            }
        
        # Mock response for now
        return {
            "success": True,
            "original_message_id": message_id,
            "reply_message_id": "mock_reply_id_67890",
            "channel": channel_name,
            "content": content,
            "timestamp": "2024-01-01T12:05:00Z"
        }
        
        # TODO: Implement actual Discord REST API call
        # session = await self._get_session()
        # url = f"{self.base_url}/channels/{channel_id}/messages"
        # data = {
        #     "content": content,
        #     "message_reference": {
        #         "message_id": message_id
        #     }
        # }
        # 
        # async with session.post(url, json=data) as resp:
        #     if resp.status == 200:
        #         result = await resp.json()
        #         return {
        #             "success": True,
        #             "reply_message_id": result["id"],
        #             "original_message_id": message_id,
        #             "timestamp": result["timestamp"]
        #         }
        #     else:
        #         return {
        #             "success": False,
        #             "error": f"Discord API error: {resp.status}",
        #             "details": await resp.text()
        #         }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()