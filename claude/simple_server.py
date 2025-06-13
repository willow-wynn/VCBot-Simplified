#!/usr/bin/env python3
"""
VCBot MCP Server - Full Implementation
Enables Claude Desktop to interact with Discord through standardized MCP protocol.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add current directory to path for VCBot imports
sys.path.append(str(Path.cwd()))

# FastMCP imports
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP(
    "VCBot-Full",
    version="1.0.0",
    description="Full VCBot Discord integration with bill search, economic data, and more"
)

# Import VCBot modules safely
try:
    import config
    import bill_utils
    import file_utils
    from ai_tools import fetch_document_content
    import message_utils
    import discord
    VCBOT_AVAILABLE = True
    print("✅ VCBot modules imported successfully")
except Exception as e:
    VCBOT_AVAILABLE = False
    print(f"⚠️ VCBot modules not available: {e}")

# Skip economic_utils and stock_market imports to avoid conflicts with main bot
ECONOMIC_AVAILABLE = False
STOCK_AVAILABLE = False
print("⚠️ Economic and stock modules disabled (use direct file reading tools instead)")

# ==================== BASIC TOOLS ====================

@mcp.tool()
def hello_world() -> str:
    """Test tool that returns a greeting."""
    return "Hello from VCBot MCP Server! 🤖"

@mcp.tool()
def wait(seconds: float) -> dict:
    """
    Pause execution for a specified number of seconds.
    
    Args:
        seconds: Number of seconds to wait (can be fractional, max 60)
    
    Returns:
        Confirmation of wait completion
    """
    import time
    from datetime import datetime
    
    # Clamp to reasonable limits
    seconds = max(0.1, min(seconds, 60.0))
    
    start_time = datetime.now()
    time.sleep(seconds)
    end_time = datetime.now()
    
    actual_duration = (end_time - start_time).total_seconds()
    
    return {
        "requested_seconds": seconds,
        "actual_duration": round(actual_duration, 2),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "completed"
    }

@mcp.tool()
def call_a_friend(prompt: str, temperature: float = 0.7, max_tokens: int = -1) -> dict:
    try:
        import requests
        import json
        
        # Clamp temperature to valid range
        temperature = max(0.0, min(temperature, 2.0))
        
        # Load conversation history
        history_file = Path.cwd() / "friend_conversation.json"
        messages = []
        
        try:
            if history_file.exists():
                with open(history_file, 'r') as f:
                    messages = json.load(f)
        except:
            messages = []
        
        # Add the new user message
        messages.append({
            "role": "user", 
            "content": prompt
        })
        
        # Prepare the request payload (OpenAI-compatible format)
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # Try the OpenAI-compatible endpoint first
        try:
            response = requests.post(
                "http://localhost:1234/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    assistant_response = result["choices"][0]["message"]["content"]
                    
                    # Add assistant response to conversation history
                    messages.append({
                        "role": "assistant",
                        "content": assistant_response
                    })
                    
                    # Save updated conversation history
                    try:
                        with open(history_file, 'w') as f:
                            json.dump(messages, f, indent=2)
                    except:
                        pass
                    
                    return {
                        "success": True,
                        "response": assistant_response,
                        "model": result.get("model", "unknown"),
                        "usage": result.get("usage", {}),
                        "endpoint": "openai_compatible",
                        "prompt": prompt,
                        "temperature": temperature,
                        "conversation_length": len(messages)
                    }
                else:
                    return {"error": "No response choices returned from LM Studio"}
            else:
                # Try the LM Studio native API endpoint
                try:
                    native_response = requests.post(
                        "http://localhost:1234/api/v0/chat/completions",
                        headers={"Content-Type": "application/json"},
                        json=payload
                    )
                    
                    if native_response.status_code == 200:
                        native_result = native_response.json()
                        
                        if "choices" in native_result and len(native_result["choices"]) > 0:
                            assistant_response = native_result["choices"][0]["message"]["content"]
                            
                            # Add assistant response to conversation history
                            messages.append({
                                "role": "assistant",
                                "content": assistant_response
                            })
                            
                            # Save updated conversation history
                            try:
                                with open(history_file, 'w') as f:
                                    json.dump(messages, f, indent=2)
                            except:
                                pass
                            
                            return {
                                "success": True,
                                "response": assistant_response,
                                "model": native_result.get("model", "unknown"),
                                "usage": native_result.get("usage", {}),
                                "stats": native_result.get("stats", {}),
                                "endpoint": "lmstudio_native",
                                "prompt": prompt,
                                "temperature": temperature,
                                "conversation_length": len(messages)
                            }
                        else:
                            return {"error": "No response choices returned from LM Studio native API"}
                    else:
                        return {
                            "error": f"Both APIs failed. OpenAI endpoint: {response.status_code}, Native endpoint: {native_response.status_code}",
                            "openai_response": response.text[:200] if response.text else "No response",
                            "native_response": native_response.text[:200] if native_response.text else "No response"
                        }
                        
                except requests.exceptions.RequestException as e:
                    return {
                        "error": f"OpenAI endpoint failed ({response.status_code}), native endpoint connection failed: {str(e)}",
                        "openai_response": response.text[:200] if response.text else "No response"
                    }
                    
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Failed to connect to LM Studio: {str(e)}",
                "suggestion": "Make sure LM Studio is running with server started on localhost:1234"
            }
            
    except Exception as e:
        return {"error": f"Unexpected error calling local LLM: {str(e)}"}

@mcp.tool()
def clear_friend_conversation() -> dict:
    try:
        history_file = Path.cwd() / "friend_conversation.json"
        if history_file.exists():
            history_file.unlink()
        
        return {
            "success": True,
            "message": "Conversation history cleared"
        }
    except Exception as e:
        return {"error": f"Failed to clear conversation: {str(e)}"}

@mcp.tool()
def get_friend_conversation() -> dict:
    try:
        import json
        
        history_file = Path.cwd() / "friend_conversation.json"
        
        if not history_file.exists():
            return {
                "success": True,
                "messages": [],
                "conversation_length": 0,
                "status": "No conversation history found"
            }
        
        with open(history_file, 'r') as f:
            messages = json.load(f)
        
        return {
            "success": True,
            "messages": messages,
            "conversation_length": len(messages),
            "status": "Conversation history loaded"
        }
        
    except Exception as e:
        return {"error": f"Failed to load conversation: {str(e)}"}

@mcp.tool()
def get_server_status() -> dict:
    """Get the status of VCBot MCP server and available modules."""
    return {
        "server_name": "VCBot MCP Server",
        "version": "1.0.0",
        "status": "running",
        "working_directory": str(Path.cwd()),
        "modules_available": {
            "vcbot_core": VCBOT_AVAILABLE,
            "economic_utils": ECONOMIC_AVAILABLE,
            "stock_market": STOCK_AVAILABLE
        },
        "available_features": [
            "Basic tools" if True else None,
            "Bill search" if VCBOT_AVAILABLE else None,
            "Knowledge base" if VCBOT_AVAILABLE else None,
            "Economic data" if ECONOMIC_AVAILABLE else None,
            "Stock market" if STOCK_AVAILABLE else None
        ]
    }

# ==================== BILL MANAGEMENT TOOLS ====================

@mcp.tool()
def search_bills(query: str, limit: int = 5) -> dict:
    """
    Search for bills in the legislative corpus using keywords.
    
    Args:
        query: Search terms (e.g., 'healthcare', 'tax reform', 'infrastructure')
        limit: Maximum number of results (default: 5, max: 10)
    
    Returns:
        Dictionary with search results and metadata
    """
    if not VCBOT_AVAILABLE:
        return {"error": "VCBot modules not available"}
    
    try:
        # Enforce limit
        limit = min(max(1, limit), 10)
        
        # Use existing bill search
        results = bill_utils.search_bills_keyword(query, limit)
        
        # Format results with additional metadata
        formatted_results = []
        for result in results:
            filename = result.get("filename", result.get("title", ""))
            
            # Get additional metadata if available
            json_path = config.BILL_JSON_DIR / f"{filename}.json"
            metadata = {}
            if json_path.exists():
                try:
                    with open(json_path, 'r') as f:
                        metadata = json.load(f)
                except:
                    pass
            
            formatted_result = {
                "title": result.get("title", filename),
                "filename": filename,
                "score": result.get("score", 0),
                "summary": result.get("summary", metadata.get("summary", "No summary available")),
                "author": metadata.get("author", "Unknown"),
                "date_introduced": metadata.get("date_introduced", "Unknown"),
                "status": metadata.get("status", "Unknown"),
                "pdf_available": (config.BILL_PDF_DIR / f"{filename}.pdf").exists(),
                "text_available": (config.BILL_TEXT_DIR / f"{filename}.txt").exists()
            }
            
            formatted_results.append(formatted_result)
        
        return {
            "query": query,
            "count": len(formatted_results),
            "results": formatted_results,
            "search_info": {
                "total_bills_searched": "~500+ bills",
                "search_type": "keyword_matching"
            }
        }
        
    except Exception as e:
        return {"error": f"Failed to search bills: {str(e)}"}

@mcp.tool()
def get_bill_details(bill_title: str, include_full_text: bool = False) -> dict:
    """
    Get detailed information about a specific bill.
    
    Args:
        bill_title: Title or filename of the bill to retrieve
        include_full_text: Whether to include the complete bill text
    
    Returns:
        Detailed bill information including metadata and optionally full text
    """
    if not VCBOT_AVAILABLE:
        return {"error": "VCBot modules not available"}
    
    try:
        # Search for the bill first
        results = bill_utils.search_bills_keyword(bill_title, 1)
        
        if not results:
            return {
                "error": "Bill not found",
                "query": bill_title,
                "suggestions": "Try searching with different keywords or check the bill title spelling"
            }
        
        bill = results[0]
        filename = bill.get("filename", "")
        
        response = {
            "title": bill.get("title", filename),
            "filename": filename,
            "relevance_score": bill.get("score", 0)
        }
        
        # Get metadata
        json_path = config.BILL_JSON_DIR / f"{filename}.json"
        if json_path.exists():
            try:
                with open(json_path, 'r') as f:
                    metadata = json.load(f)
                    response["metadata"] = metadata
            except Exception as e:
                response["metadata_error"] = f"Failed to load metadata: {str(e)}"
        
        # Get full text if requested
        if include_full_text:
            text_path = config.BILL_TEXT_DIR / f"{filename}.txt"
            if text_path.exists():
                try:
                    with open(text_path, 'r', encoding='utf-8') as f:
                        full_text = f.read()
                        response["full_text"] = full_text
                        response["text_length"] = len(full_text)
                        response["word_count"] = len(full_text.split())
                except Exception as e:
                    response["text_error"] = f"Failed to load full text: {str(e)}"
            else:
                response["text_error"] = "Full text file not found"
        
        # Check file availability
        response["files"] = {
            "pdf_exists": (config.BILL_PDF_DIR / f"{filename}.pdf").exists(),
            "text_exists": (config.BILL_TEXT_DIR / f"{filename}.txt").exists(),
            "json_exists": json_path.exists()
        }
        
        return response
        
    except Exception as e:
        return {"error": f"Failed to get bill details: {str(e)}"}

# ==================== KNOWLEDGE BASE TOOLS ====================

@mcp.tool()
def get_knowledge_file(file_name: str) -> dict:
    """
    Access knowledge base files (rules, constitution, etc).
    
    Args:
        file_name: Name of knowledge file ("rules", "constitution", "house_rules", "senate_rules")
    
    Returns:
        File content and metadata
    """
    if not VCBOT_AVAILABLE:
        return {"error": "VCBot modules not available"}
    
    available_files = {
        "rules": "General Virtual Congress rules and procedures",
        "constitution": "The Virtual Congress Constitution",
        "house_rules": "House of Representatives specific rules",
        "senate_rules": "Senate specific rules"
    }
    
    # Validate file name
    if file_name not in available_files:
        return {
            "error": f"Unknown knowledge file: {file_name}",
            "available_files": list(available_files.keys()),
            "file_descriptions": available_files
        }
    
    try:
        # Use existing file reading functionality
        content = file_utils.read_knowledge_file(file_name)
        
        if "Error" in content or "not found" in content.lower():
            return {
                "error": content,
                "file_name": file_name
            }
        
        # Get file metadata
        file_path = config.KNOWLEDGE_DIR / f"{file_name}.txt"
        metadata = {}
        
        if file_path.exists():
            stat = file_path.stat()
            metadata = {
                "file_size": stat.st_size,
                "last_modified": stat.st_mtime,
                "file_path": str(file_path)
            }
        
        return {
            "file_name": file_name,
            "description": available_files[file_name],
            "content": content,
            "content_length": len(content),
            "word_count": len(content.split()),
            "line_count": len(content.split('\n')),
            "metadata": metadata
        }
        
    except Exception as e:
        return {"error": f"Failed to read knowledge file: {str(e)}"}

@mcp.tool()
def search_knowledge_base(query: str, file_filter: Optional[List[str]] = None) -> dict:
    """
    Search across knowledge base files for specific information.
    
    Args:
        query: Search terms to look for
        file_filter: Optional list of specific files to search (default: search all)
    
    Returns:
        Search results with file sources and relevant excerpts
    """
    if not VCBOT_AVAILABLE:
        return {"error": "VCBot modules not available"}
    
    available_files = ["rules", "constitution", "house_rules", "senate_rules"]
    
    if not query or len(query.strip()) < 2:
        return {
            "error": "Query must be at least 2 characters long",
            "query": query
        }
    
    # Determine which files to search
    files_to_search = file_filter if file_filter else available_files
    
    # Validate file filter
    if file_filter:
        invalid_files = [f for f in file_filter if f not in available_files]
        if invalid_files:
            return {
                "error": f"Unknown files in filter: {invalid_files}",
                "available_files": available_files
            }
    
    search_results = []
    query_lower = query.lower()
    
    for file_name in files_to_search:
        try:
            # Get file content
            content = file_utils.read_knowledge_file(file_name)
            
            if "Error" in content:
                continue
            
            content_lower = content.lower()
            
            # Search for query in content
            if query_lower in content_lower:
                # Find matches with context
                matches = []
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        # Get context around the match
                        context_start = max(0, i - 2)
                        context_end = min(len(lines), i + 3)
                        context_lines = lines[context_start:context_end]
                        
                        matches.append({
                            "line_number": i + 1,
                            "matched_line": line.strip(),
                            "context": '\n'.join(context_lines)
                        })
                
                if matches:
                    search_results.append({
                        "file_name": file_name,
                        "match_count": len(matches),
                        "matches": matches[:5],  # Limit to 5 matches per file
                        "relevance_score": len(matches) + content_lower.count(query_lower)
                    })
                    
        except Exception as e:
            continue
    
    # Sort results by relevance
    search_results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "query": query,
        "files_searched": files_to_search,
        "results_found": len(search_results),
        "results": search_results,
        "summary": {
            "total_matches": sum(r["match_count"] for r in search_results),
            "files_with_matches": len(search_results),
            "most_relevant_file": search_results[0]["file_name"] if search_results else None
        }
    }

# ==================== ECONOMIC ANALYSIS TOOLS ====================

@mcp.tool()
def get_economic_report() -> dict:
    """
    Get comprehensive economic report with current indicators.
    
    Returns:
        Current economic data including GDP, inflation, unemployment, market sentiment
    """
    if not ECONOMIC_AVAILABLE:
        return {"error": "Economic analysis module not available"}
    
    try:
        # Get fresh economic data
        report = economic_utils.econ_data.get_fresh_economic_report()
        
        if not report:
            return {"error": "No economic data available. Run /fetch_econ_data in Discord first."}
        
        # Format for MCP response
        summary = {
            "gdp": {
                "current": f"${report['gdp']['current_gdp']:,.1f}T",
                "growth": f"{report['gdp']['quarterly_growth_percent']:+.1f}%"
            },
            "inflation": {
                "rate": f"{report['inflation']['yoy_percent']:.2f}%",
                "fed_rate": f"{report['inflation']['federal_funds_rate']:.2f}%"
            },
            "unemployment": {
                "rate": f"{report['unemployment']['rate_percent']:.1f}%",
                "claims": report['unemployment']['jobless_claims']
            },
            "sentiment": {
                "confidence": f"{report['sentiment']['confidence_percent']}%",
                "anxiety": f"{report['sentiment']['anxiety_index_percent']}%"
            }
        }
        
        return {
            "status": "success",
            "last_updated": report.get("timestamp", "Unknown"),
            "summary": summary,
            "full_report": report,
            "analysis_type": "real_ai_generated"
        }
        
    except Exception as e:
        return {"error": f"Failed to get economic report: {str(e)}"}

@mcp.tool()
def get_economic_summary() -> dict:
    """
    Get condensed economic summary with key metrics only.
    
    Returns:
        Key economic indicators in summary format
    """
    if not ECONOMIC_AVAILABLE:
        return {"error": "Economic analysis module not available"}
    
    try:
        report = economic_utils.econ_data.get_fresh_economic_report()
        
        if not report:
            return {"error": "No economic data available"}
        
        return {
            "gdp_growth": report["gdp"]["quarterly_growth_percent"],
            "inflation_rate": report["inflation"]["yoy_percent"],
            "unemployment_rate": report["unemployment"]["rate_percent"],
            "market_confidence": report["sentiment"]["confidence_percent"],
            "federal_funds_rate": report["inflation"]["federal_funds_rate"],
            "last_updated": report.get("timestamp", "Unknown"),
            "economic_outlook": "Crisis" if report["inflation"]["yoy_percent"] > 6 else "Normal"
        }
        
    except Exception as e:
        return {"error": f"Failed to get economic summary: {str(e)}"}

# ==================== STOCK MARKET TOOLS ====================

@mcp.tool()
def get_stock_market_overview() -> dict:
    """
    Get current stock market overview with sector performance.
    
    Returns:
        Market parameters, sector performance, and individual stock data
    """
    if not STOCK_AVAILABLE:
        return {"error": "Stock market module not available"}
    
    try:
        market = stock_market.get_stock_market()
        
        if not market:
            return {"error": "Stock market not initialized"}
        
        overview = {
            "market_status": "open" if market.is_market_open() else "closed",
            "parameters": {
                "trend_direction": market.market_params.get("trend_direction", 0),
                "volatility": market.market_params.get("volatility", 0),
                "momentum": market.market_params.get("momentum", 0),
                "market_sentiment": market.market_params.get("market_sentiment", 0),
                "long_term_outlook": market.market_params.get("long_term_outlook", 0)
            },
            "sectors": {},
            "total_stocks": 24,
            "last_update": market.last_update.isoformat() if market.last_update else "Never"
        }
        
        # Get sector performance
        for sector_name, stock_symbols in market.sectors.items():
            sector_data = {
                "stocks": stock_symbols,
                "stock_count": len(stock_symbols),
                "average_price": 0,
                "total_value": 0
            }
            
            sector_prices = []
            for symbol in stock_symbols:
                try:
                    price_data = market.get_stock_price(symbol)
                    if price_data and "error" not in price_data:
                        current_price = price_data["current"]
                        sector_prices.append(current_price)
                except:
                    continue
            
            if sector_prices:
                sector_data["average_price"] = round(sum(sector_prices) / len(sector_prices), 2)
                sector_data["total_value"] = round(sum(sector_prices), 2)
            
            overview["sectors"][sector_name] = sector_data
        
        return overview
        
    except Exception as e:
        return {"error": f"Failed to get stock market overview: {str(e)}"}

@mcp.tool()
def get_stock_price(symbol: str, include_history: bool = False) -> dict:
    """
    Get current price and information for a specific stock.
    
    Args:
        symbol: Stock symbol (e.g., "AAPL", "MSFT", "GOOGL", "JPM", "XOM")
        include_history: Include recent price history
    
    Returns:
        Stock price, company info, and optionally price history
    """
    if not STOCK_AVAILABLE:
        return {"error": "Stock market module not available"}
    
    try:
        market = stock_market.get_stock_market()
        
        if not market:
            return {"error": "Stock market not initialized"}
        
        price_data = market.get_stock_price(symbol.upper())
        
        if "error" in price_data:
            return {
                "error": price_data["error"],
                "symbol": symbol.upper(),
                "available_stocks": "AAPL, MSFT, GOOGL, NVDA, JPM, BAC, V, GS, XOM, CVX, COP, JNJ, UNH, PFE, WMT, COST, HD, CAT, GE, LMT, NFLX, DIS, EA, BA"
            }
        
        result = {
            "symbol": symbol.upper(),
            "current_price": price_data["current"],
            "company_name": price_data.get("company_name", "Unknown"),
            "sector": price_data.get("sector", "Unknown"),
            "industry": price_data.get("industry", "Unknown"),
            "last_updated": price_data.get("last_updated", "Unknown")
        }
        
        # Add price history if requested
        if include_history:
            try:
                history = market.get_stock_history(symbol.upper(), hours=48)
                result["price_history"] = history
                result["history_hours"] = 48
            except:
                result["history_error"] = "Failed to retrieve price history"
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to get stock price: {str(e)}"}

@mcp.tool()
def list_all_stocks() -> dict:
    """
    List all available stocks organized by sector.
    
    Returns:
        Complete list of 24 real stocks across 8 economic sectors
    """
    if not STOCK_AVAILABLE:
        return {"error": "Stock market module not available"}
    
    try:
        market = stock_market.get_stock_market()
        
        if not market:
            return {"error": "Stock market not initialized"}
        
        stock_list = {
            "total_stocks": 24,
            "total_sectors": 8,
            "sectors": {}
        }
        
        for sector_name, stocks in market.sectors.items():
            sector_info = {
                "stock_count": len(stocks),
                "stocks": []
            }
            
            for symbol in stocks:
                try:
                    stock_info = market.get_stock_info(symbol)
                    sector_info["stocks"].append({
                        "symbol": symbol,
                        "company_name": stock_info.get("company_name", "Unknown"),
                        "industry": stock_info.get("industry", "Unknown")
                    })
                except:
                    sector_info["stocks"].append({
                        "symbol": symbol,
                        "company_name": "Unknown",
                        "industry": "Unknown"
                    })
            
            stock_list["sectors"][sector_name] = sector_info
        
        return stock_list
        
    except Exception as e:
        return {"error": f"Failed to list stocks: {str(e)}"}

# ==================== DOCUMENT PROCESSING TOOLS ====================

@mcp.tool()
def fetch_google_doc(doc_url: str, analyze_content: bool = False) -> dict:
    """
    Fetch and analyze content from a Google Doc.
    
    Args:
        doc_url: Google Docs URL to fetch
        analyze_content: Whether to perform content analysis
    
    Returns:
        Document content and optional analysis
    """
    if not VCBOT_AVAILABLE:
        return {"error": "VCBot modules not available"}
    
    try:
        # Validate URL
        if not doc_url or "docs.google.com" not in doc_url:
            return {
                "error": "Invalid Google Docs URL",
                "url": doc_url
            }
        
        # Extract document ID
        doc_id = None
        if "/d/" in doc_url:
            doc_id = doc_url.split('/d/')[1].split('/')[0]
        
        # Fetch document content
        import asyncio
        content = asyncio.run(fetch_document_content(doc_url))
        
        if not content:
            return {
                "error": "Failed to fetch document content or document is empty",
                "url": doc_url,
                "doc_id": doc_id
            }
        
        result = {
            "url": doc_url,
            "doc_id": doc_id,
            "content": content,
            "content_length": len(content),
            "word_count": len(content.split()),
            "line_count": len(content.split('\n'))
        }
        
        # Perform content analysis if requested
        if analyze_content:
            analysis = {
                "document_type": "unknown",
                "key_topics": [],
                "complexity": "moderate"
            }
            
            content_lower = content.lower()
            
            # Detect document type
            if any(term in content_lower for term in ["section", "act", "bill", "amendment"]):
                analysis["document_type"] = "legislation"
            elif any(term in content_lower for term in ["whereas", "resolved", "resolution"]):
                analysis["document_type"] = "resolution"
            elif any(term in content_lower for term in ["executive order", "memorandum"]):
                analysis["document_type"] = "executive_document"
            
            # Identify key topics
            topic_keywords = {
                "economic": ["economy", "economic", "budget", "tax", "spending"],
                "healthcare": ["health", "healthcare", "medical", "insurance"],
                "education": ["education", "school", "university", "student"],
                "defense": ["defense", "military", "security", "army"],
                "environment": ["environment", "climate", "pollution", "energy"]
            }
            
            for topic, keywords in topic_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    analysis["key_topics"].append(topic)
            
            result["analysis"] = analysis
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to fetch Google Doc: {str(e)}"}

# ==================== DISCORD MESSAGING TOOLS ====================

@mcp.tool()
def get_channel_list() -> dict:
    """
    Get list of available Discord channels for messaging.
    
    Returns:
        Dictionary of channel names and IDs
    """
    if not VCBOT_AVAILABLE:
        return {"error": "VCBot modules not available"}
    
    channels = {
        "news_channel": {"id": config.NEWS_CHANNEL, "name": "news-information"},
        "clerk_channel": {"id": config.CLERK_CHANNEL, "name": "clerk-announcements"},
        "records_channel": {"id": config.RECORDS_CHANNEL, "name": "records"},
        "sign_channel": {"id": config.SIGN_CHANNEL, "name": "bills-signed-into-law"},
        "main_chat": {"id": config.MAIN_CHAT_CHANNEL, "name": "virtual-congress-chat"},
        "bot_helper": {"id": config.BOT_HELPER_CHANNEL, "name": "bot-helper"},
        "clerk_announce": {"id": config.CLERK_ANNOUNCE_CHANNEL, "name": "clerk-announcements"}
    }
    
    return {
        "available_channels": channels,
        "note": "Use send_discord_message tool to send messages to these channels"
    }

@mcp.tool()
def send_discord_message(channel_id: str, message: str, embed: bool = False) -> dict:
    """
    Send a message to a Discord channel.
    
    Args:
        channel_id: Discord channel ID to send message to
        message: Message content to send
        embed: Whether to send as an embed (default: False)
    
    Returns:
        Success/failure status and message details
    """
    if not VCBOT_AVAILABLE:
        return {"error": "VCBot modules not available"}
    
    try:
        import asyncio
        import threading
        import time
        from discord import Intents, Client
        
        # Result container for thread communication
        result_container = {"result": None, "error": None}
        
        def run_in_thread():
            """Run Discord client in separate thread with its own event loop"""
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def send_message():
                    intents = Intents.default()
                    intents.message_content = True
                    client = Client(intents=intents)
                    
                    try:
                        await client.login(config.DISCORD_TOKEN)
                        
                        # Wait a moment for client to be ready
                        await asyncio.sleep(1)
                        
                        # Convert channel_id to int if it's a string
                        try:
                            channel_id_int = int(channel_id)
                        except (ValueError, TypeError):
                            return {"error": f"Invalid channel ID: {channel_id}"}
                        
                        channel = client.get_channel(channel_id_int)
                        if not channel:
                            # Try fetching channel if not in cache
                            try:
                                channel = await client.fetch_channel(channel_id_int)
                            except:
                                return {"error": f"Channel {channel_id} not found or bot lacks access"}
                        
                        if embed:
                            # Create a simple embed
                            embed_obj = discord.Embed(
                                description=message,
                                color=0x00ff00  # Green color
                            )
                            sent_message = await channel.send(embed=embed_obj)
                        else:
                            sent_message = await channel.send(message)
                        
                        return {
                            "success": True,
                            "message_id": sent_message.id,
                            "channel_id": channel_id_int,
                            "channel_name": channel.name,
                            "content": message,
                            "sent_as_embed": embed,
                            "timestamp": sent_message.created_at.isoformat()
                        }
                        
                    except Exception as e:
                        return {"error": f"Failed to send message: {str(e)}"}
                    finally:
                        try:
                            await client.close()
                        except:
                            pass
                
                # Run the async function in this thread's event loop
                result = loop.run_until_complete(send_message())
                result_container["result"] = result
                
            except Exception as e:
                result_container["error"] = str(e)
            finally:
                try:
                    loop.close()
                except:
                    pass
        
        # Run Discord operations in separate thread
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=30)  # 30 second timeout
        
        if thread.is_alive():
            return {"error": "Discord operation timed out"}
        
        if result_container["error"]:
            return {"error": f"Thread error: {result_container['error']}"}
        
        if result_container["result"]:
            return result_container["result"]
        else:
            return {"error": "No result returned from Discord operation"}
        
    except Exception as e:
        return {"error": f"Failed to create Discord client: {str(e)}"}

@mcp.tool()
def send_channel_announcement(channel_name: str, title: str, message: str) -> dict:
    """
    Send an announcement to a specific channel with formatting.
    
    Args:
        channel_name: Name of the channel (e.g., "news", "clerk", "main_chat")
        title: Title of the announcement
        message: Announcement content
    
    Returns:
        Success/failure status and message details
    """
    if not VCBOT_AVAILABLE:
        return {"error": "VCBot modules not available"}
    
    # Map channel names to IDs
    channel_map = {
        "news": config.NEWS_CHANNEL,
        "clerk": config.CLERK_CHANNEL, 
        "records": config.RECORDS_CHANNEL,
        "sign": config.SIGN_CHANNEL,
        "main_chat": config.MAIN_CHAT_CHANNEL,
        "bot_helper": config.BOT_HELPER_CHANNEL,
        "clerk_announce": config.CLERK_ANNOUNCE_CHANNEL
    }
    
    if channel_name not in channel_map:
        return {
            "error": f"Unknown channel name: {channel_name}",
            "available_channels": list(channel_map.keys())
        }
    
    channel_id = channel_map[channel_name]
    
    # Format announcement
    formatted_message = f"**{title}**\n\n{message}"
    
    # Send as embed for better formatting
    return send_discord_message(str(channel_id), formatted_message, embed=True)

@mcp.tool()
def get_channel_context(channel_id: str, message_limit: int = 10) -> dict:
    """
    Get recent message context from a Discord channel.
    
    Args:
        channel_id: Discord channel ID to fetch messages from
        message_limit: Number of recent messages to fetch (max 50)
    
    Returns:
        Channel context with recent messages
    """
    if not VCBOT_AVAILABLE:
        return {"error": "VCBot modules not available"}
    
    try:
        import asyncio
        import threading
        from discord import Intents, Client
        
        # Limit message count
        message_limit = min(max(1, message_limit), 50)
        
        # Result container for thread communication
        result_container = {"result": None, "error": None}
        
        def run_in_thread():
            """Run Discord client in separate thread with its own event loop"""
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def fetch_messages():
                    intents = Intents.default()
                    intents.message_content = True
                    client = Client(intents=intents)
                    
                    try:
                        await client.login(config.DISCORD_TOKEN)
                        await asyncio.sleep(1)  # Wait for client to be ready
                        
                        # Convert channel_id to int
                        try:
                            channel_id_int = int(channel_id)
                        except (ValueError, TypeError):
                            return {"error": f"Invalid channel ID: {channel_id}"}
                        
                        channel = client.get_channel(channel_id_int)
                        if not channel:
                            try:
                                channel = await client.fetch_channel(channel_id_int)
                            except:
                                return {"error": f"Channel {channel_id} not found or bot lacks access"}
                        
                        # Fetch recent messages
                        messages = []
                        async for message in channel.history(limit=message_limit):
                            msg_data = {
                                "id": message.id,
                                "author": {
                                    "id": message.author.id,
                                    "name": message.author.display_name,
                                    "username": str(message.author),
                                    "bot": message.author.bot
                                },
                                "content": message.content,
                                "timestamp": message.created_at.isoformat(),
                                "attachments": [{"filename": att.filename, "url": att.url} for att in message.attachments],
                                "embeds": len(message.embeds),
                                "reactions": [{"emoji": str(reaction.emoji), "count": reaction.count} for reaction in message.reactions]
                            }
                            messages.append(msg_data)
                        
                        # Reverse to get chronological order (oldest first)
                        messages.reverse()
                        
                        return {
                            "success": True,
                            "channel_id": channel_id_int,
                            "channel_name": channel.name,
                            "message_count": len(messages),
                            "messages": messages,
                            "fetched_at": __import__('datetime').datetime.now().isoformat()
                        }
                        
                    except Exception as e:
                        return {"error": f"Failed to fetch messages: {str(e)}"}
                    finally:
                        try:
                            await client.close()
                        except:
                            pass
                
                # Run the async function in this thread's event loop
                result = loop.run_until_complete(fetch_messages())
                result_container["result"] = result
                
            except Exception as e:
                result_container["error"] = str(e)
            finally:
                try:
                    loop.close()
                except:
                    pass
        
        # Run Discord operations in separate thread
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=30)  # 30 second timeout
        
        if thread.is_alive():
            return {"error": "Discord operation timed out"}
        
        if result_container["error"]:
            return {"error": f"Thread error: {result_container['error']}"}
        
        if result_container["result"]:
            return result_container["result"]
        else:
            return {"error": "No result returned from Discord operation"}
        
    except Exception as e:
        return {"error": f"Failed to fetch channel context: {str(e)}"}

# ==================== DIRECT ECONOMIC DATA TOOLS ====================

@mcp.tool()
def get_economic_data_direct() -> dict:
    """
    Get economic data directly from JSON files (bypasses broken economic_utils module).
    
    Returns:
        Current economic indicators from data files
    """
    try:
        import json
        from datetime import datetime
        
        economic_data = {}
        base_path = Path.cwd() / "economic_data"
        
        # Read GDP data
        try:
            with open(base_path / "gdp.json", 'r') as f:
                gdp_data = json.load(f)
                if gdp_data:
                    latest_gdp = gdp_data[-1]["data"]  # Get most recent entry
                    economic_data["gdp"] = {
                        "current_gdp": latest_gdp.get("value", 0),
                        "quarterly_growth_percent": latest_gdp.get("change_percent", 0),
                        "outlook": latest_gdp.get("outlook", "Unknown")
                    }
        except Exception as e:
            economic_data["gdp"] = {"error": f"Failed to load GDP data: {str(e)}"}
        
        # Read inflation data
        try:
            with open(base_path / "inflation.json", 'r') as f:
                inflation_data = json.load(f)
                if inflation_data:
                    latest_inflation = inflation_data[-1]["data"]
                    economic_data["inflation"] = {
                        "yoy_percent": latest_inflation.get("rate", 0),
                        "federal_funds_rate": latest_inflation.get("federal_funds_rate", 0),
                        "trend": latest_inflation.get("trend", "Unknown"),
                        "policy_impact": latest_inflation.get("policy_impact", "Unknown")
                    }
        except Exception as e:
            economic_data["inflation"] = {"error": f"Failed to load inflation data: {str(e)}"}
        
        # Read unemployment data
        try:
            with open(base_path / "unemployment.json", 'r') as f:
                unemployment_data = json.load(f)
                if unemployment_data:
                    latest_unemployment = unemployment_data[-1]["data"]
                    economic_data["unemployment"] = {
                        "rate_percent": latest_unemployment.get("rate", 0),
                        "jobless_claims": latest_unemployment.get("claims", 0),
                        "trend": latest_unemployment.get("trend", "Unknown")
                    }
        except Exception as e:
            economic_data["unemployment"] = {"error": f"Failed to load unemployment data: {str(e)}"}
        
        # Read sentiment data
        try:
            with open(base_path / "sentiment.json", 'r') as f:
                sentiment_data = json.load(f)
                if sentiment_data:
                    latest_sentiment = sentiment_data[-1]["data"]
                    economic_data["sentiment"] = {
                        "confidence_percent": latest_sentiment.get("confidence", 0),
                        "anxiety_index_percent": latest_sentiment.get("anxiety", 0),
                        "market_mood": latest_sentiment.get("mood", "Unknown")
                    }
        except Exception as e:
            economic_data["sentiment"] = {"error": f"Failed to load sentiment data: {str(e)}"}
        
        return {
            "status": "success",
            "data_source": "direct_file_reading",
            "last_updated": datetime.now().isoformat(),
            "economic_indicators": economic_data,
            "crisis_mode": economic_data.get("inflation", {}).get("yoy_percent", 0) > 6.0
        }
        
    except Exception as e:
        return {"error": f"Failed to read economic data files: {str(e)}"}

@mcp.tool()
def get_economic_summary_direct() -> dict:
    """
    Get condensed economic summary from direct file reading.
    
    Returns:
        Key economic metrics in summary format
    """
    try:
        full_data = get_economic_data_direct()
        
        if "error" in full_data:
            return full_data
        
        econ = full_data["economic_indicators"]
        
        return {
            "gdp_growth": econ.get("gdp", {}).get("quarterly_growth_percent", 0),
            "inflation_rate": econ.get("inflation", {}).get("yoy_percent", 0),
            "unemployment_rate": econ.get("unemployment", {}).get("rate_percent", 0),
            "market_confidence": econ.get("sentiment", {}).get("confidence_percent", 0),
            "federal_funds_rate": econ.get("inflation", {}).get("federal_funds_rate", 0),
            "last_updated": full_data.get("last_updated", "Unknown"),
            "economic_outlook": "Crisis" if econ.get("inflation", {}).get("yoy_percent", 0) > 6 else "Normal",
            "data_source": "direct_file_reading"
        }
        
    except Exception as e:
        return {"error": f"Failed to generate economic summary: {str(e)}"}

# ==================== DIRECT STOCK DATA TOOLS ====================

@mcp.tool()
def get_stock_data_direct() -> dict:
    """
    Get stock market data directly from JSON files (bypasses broken stock_market module).
    
    Returns:
        Current stock prices and market data
    """
    try:
        import json
        from datetime import datetime
        
        base_path = Path.cwd() / "stock_data"
        
        # Read market data
        market_data = {}
        try:
            with open(base_path / "market_data.json", 'r') as f:
                market_data = json.load(f)
        except Exception as e:
            return {"error": f"Failed to load market data: {str(e)}"}
        
        # Read daily analysis
        analysis_data = {}
        try:
            with open(base_path / "daily_analysis.json", 'r') as f:
                analysis_list = json.load(f)
                if analysis_list:
                    analysis_data = analysis_list[-1]  # Get most recent
        except Exception as e:
            analysis_data = {"error": f"Failed to load analysis: {str(e)}"}
        
        # Extract stock info by sector
        sectors = {}
        total_stocks = 0
        
        if "categories" in market_data:
            for sector_name, sector_info in market_data["categories"].items():
                sector_stocks = []
                for stock in sector_info.get("stocks", []):
                    sector_stocks.append({
                        "symbol": stock.get("symbol", ""),
                        "name": stock.get("name", ""),
                        "price": stock.get("price", 0),
                        "daily_range_low": stock.get("daily_range_low", 0),
                        "daily_range_high": stock.get("daily_range_high", 0),
                        "sector": stock.get("sector", "")
                    })
                    total_stocks += 1
                
                sectors[sector_name] = {
                    "name": sector_info.get("name", ""),
                    "description": sector_info.get("description", ""),
                    "stock_count": len(sector_stocks),
                    "stocks": sector_stocks
                }
        
        return {
            "status": "success",
            "data_source": "direct_file_reading",
            "last_updated": datetime.now().isoformat(),
            "total_stocks": total_stocks,
            "sectors": sectors,
            "market_analysis": analysis_data,
            "market_open": True  # Assume open for now
        }
        
    except Exception as e:
        return {"error": f"Failed to read stock data files: {str(e)}"}

@mcp.tool()
def get_stock_price_direct(symbol: str) -> dict:
    """
    Get specific stock price directly from market data files.
    
    Args:
        symbol: Stock symbol (e.g., "AAPL", "MSFT", "XOM")
    
    Returns:
        Stock price and details
    """
    try:
        symbol = symbol.upper()
        stock_data = get_stock_data_direct()
        
        if "error" in stock_data:
            return stock_data
        
        # Search for stock in all sectors
        for sector_name, sector_info in stock_data["sectors"].items():
            for stock in sector_info["stocks"]:
                if stock["symbol"] == symbol:
                    return {
                        "success": True,
                        "symbol": symbol,
                        "name": stock["name"],
                        "current_price": stock["price"],
                        "daily_range_low": stock["daily_range_low"],
                        "daily_range_high": stock["daily_range_high"],
                        "sector": sector_name,
                        "sector_name": sector_info["name"],
                        "last_updated": stock_data["last_updated"],
                        "data_source": "direct_file_reading"
                    }
        
        # Stock not found
        available_symbols = []
        for sector_info in stock_data["sectors"].values():
            for stock in sector_info["stocks"]:
                available_symbols.append(stock["symbol"])
        
        return {
            "error": f"Stock {symbol} not found",
            "available_symbols": sorted(available_symbols)
        }
        
    except Exception as e:
        return {"error": f"Failed to get stock price: {str(e)}"}

@mcp.tool()
def get_stock_sectors_direct() -> dict:
    """
    Get all stock sectors and their compositions from direct file reading.
    
    Returns:
        All sectors with stock listings
    """
    try:
        stock_data = get_stock_data_direct()
        
        if "error" in stock_data:
            return stock_data
        
        # Simplify sector data
        simplified_sectors = {}
        for sector_name, sector_info in stock_data["sectors"].items():
            simplified_sectors[sector_name] = {
                "name": sector_info["name"],
                "description": sector_info["description"],
                "stock_count": sector_info["stock_count"],
                "symbols": [stock["symbol"] for stock in sector_info["stocks"]]
            }
        
        return {
            "success": True,
            "total_sectors": len(simplified_sectors),
            "total_stocks": stock_data["total_stocks"],
            "sectors": simplified_sectors,
            "data_source": "direct_file_reading"
        }
        
    except Exception as e:
        return {"error": f"Failed to get stock sectors: {str(e)}"}

@mcp.tool()
def get_market_analysis_direct() -> dict:
    """
    Get current market analysis parameters from direct file reading.
    
    Returns:
        Market analysis parameters and invisible factors
    """
    try:
        import json
        
        base_path = Path.cwd() / "stock_data"
        
        try:
            with open(base_path / "daily_analysis.json", 'r') as f:
                analysis_list = json.load(f)
                if not analysis_list:
                    return {"error": "No analysis data available"}
                
                latest_analysis = analysis_list[-1]
                
                return {
                    "success": True,
                    "parameters": latest_analysis.get("parameters", {}),
                    "invisible_factors": latest_analysis.get("invisible_factors", {}),
                    "reasoning": latest_analysis.get("reasoning", {}),
                    "timestamp": latest_analysis.get("timestamp", "Unknown"),
                    "data_source": "direct_file_reading"
                }
                
        except Exception as e:
            return {"error": f"Failed to load analysis data: {str(e)}"}
        
    except Exception as e:
        return {"error": f"Failed to get market analysis: {str(e)}"}

# ==================== MCP RESOURCES ====================

@mcp.resource("vcbot://status")
async def get_bot_status_resource() -> str:
    """Get current VCBot status as a resource."""
    status = {
        "server_name": "VCBot MCP Server",
        "version": "1.0.0",
        "working_directory": str(Path.cwd()),
        "modules_available": {
            "vcbot_core": VCBOT_AVAILABLE,
            "economic_utils": ECONOMIC_AVAILABLE,
            "stock_market": STOCK_AVAILABLE
        },
        "data_status": {
            "bills_directory": str(Path.cwd() / "every-vc-bill") if VCBOT_AVAILABLE else "N/A",
            "knowledge_directory": str(Path.cwd() / "Knowledge") if VCBOT_AVAILABLE else "N/A",
            "economic_data": "Available" if ECONOMIC_AVAILABLE else "Not available",
            "stock_data": "Available" if STOCK_AVAILABLE else "Not available"
        }
    }
    
    return json.dumps(status, indent=2)

@mcp.resource("vcbot://bills/recent")
async def get_recent_bills_resource() -> str:
    """Get list of recently added bills as a resource."""
    if not VCBOT_AVAILABLE:
        return json.dumps({"error": "VCBot modules not available"})
    
    try:
        # Get recent bills from the JSON directory
        json_files = sorted(
            config.BILL_JSON_DIR.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:10]  # Last 10 bills
        
        bills = []
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    bills.append({
                        "title": data.get("title", json_file.stem),
                        "filename": json_file.stem,
                        "author": data.get("author", "Unknown"),
                        "date_introduced": data.get("date_introduced", "Unknown"),
                        "summary": data.get("summary", "")[:200] + "..." if data.get("summary", "") else ""
                    })
            except:
                continue
        
        return json.dumps({"recent_bills": bills}, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Failed to get recent bills: {str(e)}"})

@mcp.resource("vcbot://economy/current")
async def get_current_economy_resource() -> str:
    """Get current economic indicators as a resource."""
    if not ECONOMIC_AVAILABLE:
        return json.dumps({"error": "Economic analysis module not available"})
    
    try:
        report = economic_utils.econ_data.get_fresh_economic_report()
        if report:
            return json.dumps(report, indent=2)
        else:
            return json.dumps({"error": "No economic data available"})
    except Exception as e:
        return json.dumps({"error": f"Failed to get economic data: {str(e)}"})

# ==================== MCP PROMPTS ====================

@mcp.prompt()
async def analyze_bill_impact(bill_title: str) -> List[Dict[str, str]]:
    """
    Generate a prompt for analyzing a bill's potential impact.
    
    Args:
        bill_title: Title of the bill to analyze
        
    Returns:
        Prompt messages for comprehensive bill analysis
    """
    # Get bill details
    bill_details = await get_bill_details(bill_title, include_full_text=True)
    
    if "error" in bill_details:
        return [{"role": "user", "content": f"Error: Could not find bill '{bill_title}'. Try searching for it first."}]
    
    # Get current economic data if available
    econ_summary = {"error": "Not available"}
    if ECONOMIC_AVAILABLE:
        econ_summary = await get_economic_summary()
    
    # Build comprehensive analysis prompt
    messages = [
        {
            "role": "system",
            "content": "You are an expert policy analyst for Virtual Congress, specializing in legislative impact assessment and economic analysis."
        },
        {
            "role": "user",
            "content": f"""Please conduct a comprehensive analysis of the following legislation:

**BILL INFORMATION**
Title: {bill_details['title']}
Filename: {bill_details.get('filename', 'N/A')}
Author: {bill_details.get('metadata', {}).get('author', 'Unknown')}

**BILL TEXT**
{bill_details.get('full_text', 'Full text not available')}

**CURRENT ECONOMIC CONTEXT**
{json.dumps(econ_summary, indent=2) if "error" not in econ_summary else "Economic data not available"}

**ANALYSIS REQUIREMENTS**
Please provide a detailed analysis covering:

1. **Executive Summary**
   - Brief overview of the bill's purpose and scope
   - Key stakeholders and affected parties

2. **Economic Impact Assessment**
   - Direct fiscal implications (costs, revenue impacts)
   - Indirect economic effects on markets and sectors
   - Impact on inflation, employment, and economic growth

3. **Implementation Analysis**
   - Required resources and timeline
   - Potential implementation challenges
   - Regulatory and administrative requirements

4. **Political Feasibility**
   - Likelihood of passage in current Virtual Congress
   - Potential opposition and support coalitions

5. **Risk Assessment**
   - Potential unintended consequences
   - Long-term sustainability concerns

6. **Recommendations**
   - Overall recommendation (support/oppose/modify)
   - Suggested amendments or improvements

Please format your analysis professionally and cite specific provisions of the bill where relevant."""
        }
    ]
    
    return messages

@mcp.prompt()
async def draft_legislation(topic: str, bill_type: str = "bill") -> List[Dict[str, str]]:
    """
    Generate a prompt for drafting new legislation.
    
    Args:
        topic: Topic of the legislation
        bill_type: Type of legislation ("bill", "resolution", "amendment")
        
    Returns:
        Prompt messages for legislation drafting
    """
    # Get current economic context if available
    econ_context = ""
    if ECONOMIC_AVAILABLE:
        try:
            econ_summary = await get_economic_summary()
            if "error" not in econ_summary:
                econ_context = f"""
**Current Economic Context:**
- GDP Growth: {econ_summary['gdp_growth']}%
- Inflation Rate: {econ_summary['inflation_rate']}%
- Unemployment: {econ_summary['unemployment_rate']}%
- Market Confidence: {econ_summary['market_confidence']}%
"""
        except:
            pass
    
    messages = [
        {
            "role": "system",
            "content": f"You are a legislative drafter for Virtual Congress, tasked with creating well-structured {bill_type}s that follow proper legislative format and procedures."
        },
        {
            "role": "user",
            "content": f"""Draft a comprehensive {bill_type} on the topic: {topic}

{econ_context}

**Legislative Requirements:**
1. **Proper Format**: Follow standard legislative format for Virtual Congress
2. **Clear Title**: Create a descriptive title that accurately reflects the content
3. **Structured Sections**: Organize into logical sections with clear headings
4. **Definitions**: Include necessary definitions for key terms
5. **Implementation**: Specify how the legislation will be implemented
6. **Funding**: Address any fiscal implications and funding mechanisms
7. **Timeline**: Provide realistic timelines for implementation
8. **Enforcement**: Include enforcement mechanisms where appropriate

**Content Guidelines:**
- Be specific and actionable
- Consider both intended and unintended consequences
- Address potential opposition concerns
- Ensure compatibility with existing Virtual Congress laws
- Include sunset clauses or review periods where appropriate

Please draft the {bill_type} following these requirements and ensuring it addresses the core issues related to {topic}."""
        }
    ]
    
    return messages

@mcp.prompt()
async def economic_briefing() -> List[Dict[str, str]]:
    """
    Generate a prompt for creating an economic briefing.
    
    Returns:
        Prompt messages for economic analysis
    """
    # Get current economic data
    econ_report = {"error": "Not available"}
    stock_overview = {"error": "Not available"}
    
    if ECONOMIC_AVAILABLE:
        try:
            econ_report = await get_economic_report()
        except:
            pass
    
    if STOCK_AVAILABLE:
        try:
            stock_overview = await get_stock_market_overview()
        except:
            pass
    
    messages = [
        {
            "role": "system",
            "content": "You are the chief economic advisor for Virtual Congress, preparing a briefing for government leaders."
        },
        {
            "role": "user",
            "content": f"""Prepare a comprehensive economic briefing based on the latest data:

**ECONOMIC INDICATORS**
{json.dumps(econ_report, indent=2) if "error" not in econ_report else "Economic data not currently available"}

**STOCK MARKET DATA**
{json.dumps(stock_overview, indent=2) if "error" not in stock_overview else "Stock market data not currently available"}

**BRIEFING REQUIREMENTS**
Create a professional briefing document that includes:

1. **Executive Summary**
   - Current economic state in 2-3 sentences
   - Key trends and immediate concerns

2. **Detailed Analysis**
   - GDP and growth trends
   - Inflation analysis and monetary policy implications
   - Labor market conditions
   - Market sentiment and confidence levels

3. **Sector Performance**
   - Stock market performance by sector
   - Notable economic drivers
   - Areas of concern or opportunity

4. **Policy Implications**
   - Recommended policy responses
   - Areas requiring government attention
   - Potential legislative priorities

5. **Risk Assessment**
   - Economic risks on the horizon
   - Market volatility concerns
   - External factors to monitor

6. **Recommendations**
   - Immediate actions needed
   - Medium-term strategic priorities
   - Monitoring and review schedule

Format this as a professional government briefing document suitable for Virtual Congress leadership."""
        }
    ]
    
    return messages

if __name__ == "__main__":
    print("🚀 Starting Full VCBot MCP Server...")
    print("📊 Modules loaded:")
    print(f"  - VCBot Core: {'✅' if VCBOT_AVAILABLE else '❌'}")
    print(f"  - Economic Utils: {'✅' if ECONOMIC_AVAILABLE else '❌'}")
    print(f"  - Stock Market: {'✅' if STOCK_AVAILABLE else '❌'}")
    mcp.run()