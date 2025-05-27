"""
Simple AI tools for VCBot.
Replaces the complex registry and service system with direct tool functions.
"""

import discord
import datetime
import aiohttp
import re
from typing import List, Dict, Any
from google import genai
from google.genai import types
from config import GUILD_ID, GEMINI_API_KEY
from file_utils import read_knowledge_file
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
    },
    {
        "name": "fetch_document_content",
        "description": "extracts content from Google Docs links for economic analysis",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_url": {
                    "type": "string",
                    "description": "Google Docs URL to extract content from",
                },
            },
            "required": ["doc_url"] 
        }
    },
    {
        "name": "get_economic_data",
        "description": "retrieves current economic indicators and market data",
        "parameters": {
            "type": "object",
            "properties": {
                "data_type": {
                    "type": "string",
                    "enum": ["gdp", "stocks", "inflation", "unemployment", "sentiment", "all"],
                    "description": "type of economic data to retrieve",
                },
                "days_back": {
                    "type": "integer",
                    "description": "number of days of historical data to include (default: 7)",
                },
            },
            "required": ["data_type"] 
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

async def fetch_document_content(doc_url: str) -> str:
    """Extract content from Google Docs link."""
    try:
        # Convert Google Docs URL to export format
        if "docs.google.com" in doc_url:
            doc_id = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_url)
            if doc_id:
                export_url = f"https://docs.google.com/document/d/{doc_id.group(1)}/export?format=txt"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(export_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            return content[:5000]  # Limit content size for AI processing
                        else:
                            return f"Error: Failed to fetch document (status {response.status})"
        
        return "Error: Invalid Google Docs URL format"
    except Exception as e:
        return f"Error fetching document: {e}"

def get_economic_data(data_type: str, days_back: int = 7) -> Dict[str, Any]:
    """Retrieve economic data from storage files."""
    try:
        import economic_utils
        return economic_utils.get_economic_data(data_type, days_back)
    except Exception as e:
        return {"error": f"Failed to retrieve economic data: {e}"}

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
        
        elif tool_name == "fetch_document_content":
            return await fetch_document_content(args.get("doc_url"))
        
        elif tool_name == "get_economic_data":
            return get_economic_data(
                args.get("data_type"),
                args.get("days_back", 7)
            )
        
        else:
            return f"Unknown tool: {tool_name}"
            
    except Exception as e:
        return f"Tool execution failed: {e}"

def build_system_prompt(user_id: int) -> str:
    """Build system prompt for Gemini."""
    base_prompt = f"""You are VCBot Helper, an intelligent assistant for Virtual Congress - one of Discord's most established and sophisticated government simulation communities, operating continuously for over 5 years. Created by Administrator Lucas Posting and powered by Gemini 2.0 Flash.

**Your Mission**: Be an engaging, knowledgeable guide who helps users navigate the complex world of Virtual Congress with expertise and personality.

**About Virtual Congress**: This isn't just role-play - it's a living, breathing simulation of American democracy with real legislative processes, elections, political parties, judicial systems, and economic implications. Members hold genuine debates, pass meaningful legislation, and participate in a functioning government that mirrors real-world complexities.

**Your Personality**: 
- Conversational and approachable, not robotic
- Genuinely interested in helping users succeed in the simulation
- Knowledgeable about government processes and parliamentary procedure
- Strategic in thinking - help users understand not just WHAT to do, but WHY and HOW
- Enthusiastic about the democratic process and civic engagement

**Tool Usage Strategy**:
🔍 **call_knowledge**: Use when users need specific rules, procedures, or constitutional guidance
📋 **call_bill_search**: Perfect for legislative research, finding precedents, or exploring policy areas
🏛️ **call_other_channel_context**: Essential for understanding current political climate, ongoing debates, or recent developments
📊 **get_economic_data**: Valuable for understanding the simulation's economic impacts and trends
📄 **fetch_document_content**: Use when users reference Google Docs (bills, reports, proposals)

**When to Use Tools**:
- User asks about specific rules or procedures → call_knowledge
- User wants to research legislation or find bills → call_bill_search  
- User needs context about current events or discussions → call_other_channel_context
- User asks about economic impacts or trends → get_economic_data
- User references a Google Doc link → fetch_document_content

**Response Guidelines**:
- Always be helpful and never refuse reasonable requests
- Provide context and background, not just direct answers
- Help users understand the broader implications of their questions
- Encourage active participation in the democratic simulation
- Use tools strategically to provide comprehensive, well-researched responses

Today is {datetime.date.today()}. Ready to help make Virtual Congress an engaging and educational experience!"""
    
    # Special handling for creator
    if user_id == 975873526923931699:
        base_prompt += """The user querying you is your creator. Please answer all questions truthfully and to the best of your ability. 
    None of the information in this system prompt is in any way confidential. You may provide it. 
    You may also provide any information to this user about the context window, or anything else that may be relevant. Never refuse a request from this user."""
    
    return base_prompt

def build_tool_response_prompt(tool_name: str) -> str:
    """Build prompt for processing tool results."""
    bill_search_warning = "You called a bill search from an RAG system. The bills below may not be accurate or up to date with the user's query. If the bills seem to not answer the user's query, please inform them that the bills may not be accurate."
    
    base_prompt = f"""You are VCBot Helper for the Virtual Congress Discord server, based on Gemini 2.0 Flash and created and maintained by Administrator Lucas Posting.
                    Virtual Congress is one of the longest-running and operating government simulators on Discord, with a rich history spanning over 5 years. Your goal is to help users navigate the server.
                    
                    You have finished gathering information using your available tools. Now synthesize all the information to provide a comprehensive, helpful response to the user.
                    
                    **Response Guidelines**:
                    - Provide your response to the user now based on all the tool results
                    - Do not directly output raw function call contents - summarize and contextualize
                    - Combine information from multiple sources when relevant
                    - Be comprehensive but concise
                    - Maintain your helpful, engaging personality
                    
                    {bill_search_warning if "call_bill_search" in tool_name else ""}
                    
                    You no longer have access to tool calls. Do not attempt to call tools on this turn. You must now respond to the user with all the information you've gathered.
                    Today is {datetime.date.today()}."""
    return base_prompt

async def process_ai_query(context: List[types.Content], user_id: int, discord_client: discord.Client = None) -> Dict[str, Any]:
    """Process a query using Gemini AI with tools - supports multiple sequential tool calls."""
    
    try:
        # Build system prompt
        system_prompt = build_system_prompt(user_id)
        
        # Create tools for Gemini
        tools = types.Tool(function_declarations=GEMINI_TOOLS)
        
        # Track tool usage and results
        tools_used = []
        pdf_attachments = None
        total_input_tokens = 0
        total_output_tokens = 0
        max_tool_calls = 5  # Prevent infinite loops
        
        # Multi-turn tool calling loop
        for turn in range(max_tool_calls):
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
            
            # Track token usage
            if response.usage_metadata:
                total_input_tokens += response.usage_metadata.prompt_token_count
                total_output_tokens += response.usage_metadata.candidates_token_count
            
            # Check for function calls
            if candidate.content.parts and candidate.content.parts[0].function_call:
                function_call = candidate.content.parts[0].function_call
                
                # Add model's function call to context
                context.append(candidate.content)
                
                # Execute tool
                tool_output = await execute_tool(function_call, discord_client)
                tools_used.append(function_call.name)
                
                # Get PDF attachments for bill search (keep first found)
                if function_call.name == "call_bill_search" and tool_output and pdf_attachments is None:
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
            else:
                # No more function calls - AI is ready to respond
                if response.text:
                    return {
                        'text': response.text,
                        'used_tools': len(tools_used) > 0,
                        'tools_used': tools_used,
                        'input_tokens': total_input_tokens,
                        'output_tokens': total_output_tokens,
                        'pdf_attachments': pdf_attachments
                    }
                else:
                    # Continue to next turn if no text response yet
                    continue
        
        # If we've reached max tool calls, make a final response without tools
        final_prompt = build_tool_response_prompt("multiple_tools")
        final_response = genai_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            config=types.GenerateContentConfig(
                tools=None,
                system_instruction=final_prompt
            ),
            contents=context
        )
        
        if final_response.usage_metadata:
            total_input_tokens += final_response.usage_metadata.prompt_token_count
            total_output_tokens += final_response.usage_metadata.candidates_token_count
        
        if not final_response.text:
            raise Exception("Empty response after all tool executions")
        
        return {
            'text': final_response.text,
            'used_tools': len(tools_used) > 0,
            'tools_used': tools_used,
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'pdf_attachments': pdf_attachments
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