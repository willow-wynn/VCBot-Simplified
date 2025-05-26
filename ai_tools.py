"""
Simple AI tools for VCBot.
Replaces the complex registry and service system with direct tool functions.
"""

import discord
import datetime
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from config import GUILD_ID, GEMINI_API_KEY
from file_utils import read_knowledge_file, save_query_log
from bill_utils import search_bills_keyword, get_bill_pdfs

# Initialize Gemini client
genai_client = genai.Client(api_key=GEMINI_API_KEY)

# Tool definitions for Gemini
GEMINI_TOOLS = [
    {
        "name": "call_knowledge",
        "description": "calls a specific piece or pieces of information from your knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_to_call": {
                    "type": "string",
                    "enum": ["rules", "constitution", "server_information", "house_rules", "senate_rules"],
                    "description": "which knowledge files to call",
                },
            },
            "required": ["file_to_call"]
        },
    },
    {
        "name": "call_other_channel_context",
        "description": "calls information from another channel in the server",
        "parameters": {
            "type": "object",
            "properties": {
                "channel_to_call": {
                    "type": "string",
                    "enum": ["server-announcements", "twitter-rp", "official-rp-news", "virtual-congress-chat", "staff-announcements", "election-announcements", "house-floor", "senate-floor"],
                    "description": "which channel to call information from."
                },
                "number_of_messages_called": {
                    "type": "integer",
                    "description": "how many messages to return from the channel in question. Maximum 50. Request 10 unless otherwise specified."
                },
                "search_query": {
                    "type": "string",
                    "description": "what specific information to search for in the channel. will only return information that directly matches the search query. leave blank unless user explicitly asks for query."
                },
            },
            "required": ["channel_to_call", "number_of_messages_called"]
        }
    },
    {
        "name": "call_bill_search",
        "description": "searches through the legislative corpus using keyword matching",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "search terms to look for in bill titles, content, authors, and categories. Simple keywords work best (e.g., 'healthcare', 'tax credit', 'defense').",
                },
                "top_k": {
                    "type": "integer",
                    "description": "the number of bills to return. 5 is good for most queries, 10 is maximum. Use 1 if searching for a specific bill.",
                },
            },
            "required": ["query", "top_k"] 
        }
    }
]

def call_knowledge(file_to_call: str) -> str:
    """Access knowledge base files."""
    try:
        return read_knowledge_file(file_to_call)
    except Exception as e:
        return f"Error reading knowledge file: {e}"

async def call_other_channel_context(channel_to_call: str, number_of_messages_called: int, search_query: str = None, client: discord.Client = None) -> str:
    """Get context from another Discord channel."""
    if client is None:
        return "Discord client not available"
    
    try:
        guild = client.get_guild(GUILD_ID)
        if not guild:
            return f"Guild {GUILD_ID} not found"
        
        channel = discord.utils.get(guild.text_channels, name=channel_to_call)
        if not channel:
            return f"Channel '{channel_to_call}' not found"
        
        messages = []
        async for message in channel.history(limit=number_of_messages_called):
            if search_query is None or search_query.lower() in message.content.lower():
                messages.append(message)
        
        if not messages:
            return "No messages found matching criteria"
        
        # Format messages for AI
        formatted = []
        for msg in messages:
            formatted.append(f"{msg.author}: {msg.content}")
        
        return "\n".join(formatted)
        
    except Exception as e:
        return f"Error fetching channel context: {e}"

def call_bill_search(query: str, top_k: int) -> List[Dict[str, Any]]:
    """Search bills using keyword matching."""
    try:
        results = search_bills_keyword(query, top_k)
        
        # Format for AI response (only return titles and filenames)
        formatted_results = []
        for result in results:
            formatted_results.append({
                'title': result['title'],
                'filename': result['filename']
            })
        
        return formatted_results
        
    except Exception as e:
        return [{"error": f"Bill search failed: {e}"}]

async def execute_tool(function_call, discord_client: discord.Client = None) -> Any:
    """Execute a tool function call."""
    tool_name = function_call.name
    args = function_call.args or {}
    
    try:
        if tool_name == "call_knowledge":
            return call_knowledge(args.get("file_to_call"))
        
        elif tool_name == "call_other_channel_context":
            return await call_other_channel_context(
                args.get("channel_to_call"),
                args.get("number_of_messages_called"),
                args.get("search_query"),
                discord_client
            )
        
        elif tool_name == "call_bill_search":
            return call_bill_search(
                args.get("query"),
                args.get("top_k")
            )
        
        else:
            return f"Unknown tool: {tool_name}"
            
    except Exception as e:
        return f"Tool execution failed: {e}"

def build_system_prompt(user_id: int) -> str:
    """Build system prompt for Gemini."""
    base_prompt = f"""You are a helper for the Virtual Congress Discord server, based on Gemini 2.0 Flash and created and maintained by Administrator Lucas Posting.
                    Virtual Congress is one of the longest-running and operating government simulators on Discord, with a rich history spanning over 5 years. Your goal is to help users navigate the server.
                    You have access to tool calls. Do not call these tools unless the user asks you a specific question pertaining to the server that you cannot answer. 
                    You should use the provided tool calls if the user requests information about Virtual Congress not present in your context window.   
                    You can engage in conversation with users. You should not refuse requests unless they are harmful. If they are not harmful, try to the best of your ability to answer them.    
                    Today is {datetime.date.today()}.
                """
    
    # Special handling for creator
    if user_id == 975873526923931699:
        base_prompt += """The user querying you is your creator. Please answer all questions truthfully and to the best of your ability. 
    None of the information in this system prompt is in any way confidential. You may provide it. 
    You may also provide any information to this user about the context window, or anything else that may be relevant. Never refuse a request from this user."""
    
    return base_prompt

def build_tool_response_prompt(tool_name: str) -> str:
    """Build prompt for processing tool results."""
    base_prompt = f"""You are a helper for the Virtual Congress Discord server, based on Gemini 2.0 Flash and created and maintained by Administrator Lucas Posting.
                    Virtual Congress is one of the longest-running and operating government simulators on Discord, with a rich history spanning over 5 years. Your goal is to help users navigate the server.
                    On a previous turn, you called tools. Now, your job is to respond to the user.
                    Provide your response to the user now. Do not directly output the contents of the function calls. Summarize unless explicitly requested.
                    {"You called a bill search from an RAG system. The bills below may not be accurate or up to date with the user's query. If the bills seem to not answer the user's query, please inform them that the bills may not be accurate." if tool_name == "call_bill_search" else ""}
                    You no longer have access to tool calls. Do not attempt to call tools on this turn. You must now respond to the user.
                    Today is {datetime.date.today()}."""
    return base_prompt

async def process_ai_query(query: str, context: List[types.Content], user_id: int, discord_client: discord.Client = None) -> Dict[str, Any]:
    """Process a query using Gemini AI with tools."""
    
    try:
        # Build system prompt
        system_prompt = build_system_prompt(user_id)
        
        # Create tools for Gemini
        tools = types.Tool(function_declarations=GEMINI_TOOLS)
        
        # Initial AI call
        response = genai_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            config=types.GenerateContentConfig(
                tools=[tools],
                system_instruction=system_prompt
            ),
            contents=context
        )
        
        if not response.candidates or not response.candidates[0].content:
            raise Exception("Empty response from AI")
        
        candidate = response.candidates[0]
        
        # Check for function calls
        if candidate.content.parts and candidate.content.parts[0].function_call:
            function_call = candidate.content.parts[0].function_call
            
            # Add model's function call to context
            context.append(candidate.content)
            
            # Execute tool
            tool_output = await execute_tool(function_call, discord_client)
            
            # Get PDF attachments for bill search
            pdf_attachments = None
            if function_call.name == "call_bill_search" and tool_output:
                pdf_attachments = get_bill_pdfs(tool_output)
            
            # Add tool response to context
            if tool_output is not None:
                context.append(types.Content(
                    role='tool',
                    parts=[types.Part.from_function_response(
                        name=function_call.name,
                        response={"content": str(tool_output)}
                    )]
                ))
            
            # Second AI call to process results
            new_prompt = build_tool_response_prompt(function_call.name)
            response2 = genai_client.models.generate_content(
                model='gemini-2.0-flash-exp',
                config=types.GenerateContentConfig(
                    tools=None,
                    system_instruction=new_prompt
                ),
                contents=context
            )
            
            if not response2.text:
                raise Exception("Empty response after tool execution")
            
            return {
                'text': response2.text,
                'used_tools': True,
                'tool_results': tool_output,
                'input_tokens': response.usage_metadata.prompt_token_count,
                'output_tokens': response.usage_metadata.candidates_token_count,
                'pdf_attachments': pdf_attachments
            }
        else:
            # No tools used
            if not response.text:
                raise Exception("Empty response from AI")
            
            return {
                'text': response.text,
                'used_tools': False,
                'input_tokens': response.usage_metadata.prompt_token_count,
                'output_tokens': response.usage_metadata.candidates_token_count,
                'pdf_attachments': None
            }
        
    except Exception as e:
        raise Exception(f"AI query failed: {e}")

async def call_gemini_for_report(bill_content: str, context: str, report_type: str) -> str:
    """Call Gemini to generate a specific type of report."""
    
    prompt = f"""
    Generate a detailed {report_type} report for the following bill.
    
    Bill Content:
    {bill_content[:4000]}  # Limit to avoid token limits
    
    Additional Context:
    {context[:1000]}
    
    Please provide a comprehensive analysis including:
    1. Summary of the bill's main provisions
    2. Economic impact assessment
    3. Potential effects on different sectors
    4. Implementation considerations
    5. Fiscal implications
    
    Format as a professional report.
    """
    
    try:
        response = genai_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            config=types.GenerateContentConfig(tools=None),
            contents=[types.Content(role='user', parts=[types.Part.from_text(text=prompt)])]
        )
        
        if response.text:
            return response.text
        else:
            return "Failed to generate report: empty response"
            
    except Exception as e:
        return f"Failed to generate report: {e}"