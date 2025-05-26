"""
Simple bill utilities for VCBot.
Replaces the complex BillService and Repository classes with direct functions.
"""

import re
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import BILL_TEXT_DIR, BILL_PDF_DIR, BILL_JSON_DIR
from file_utils import get_bill_content, get_bill_metadata, save_bill_content, save_bill_metadata

def search_bills_keyword(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Perform keyword search through bills using text files and JSON metadata.
    Returns list of matching bills with title, filename, and relevance score.
    """
    print(f"Running keyword search for: '{query}' (max {top_k} results)")
    
    if not query or not query.strip():
        return []
    
    top_k = max(1, min(int(top_k), 10))
    query_lower = query.lower().strip()
    results = []
    
    try:
        # 1. Search through JSON metadata first (titles, authors, etc.)
        if BILL_JSON_DIR.exists():
            for json_file in BILL_JSON_DIR.glob("*.json"):
                try:
                    metadata = get_bill_metadata(json_file.stem)
                    if not metadata:
                        continue
                    
                    title = metadata.get('title', '')
                    author = metadata.get('author', '')
                    cosponsors = ' '.join(metadata.get('cosponsors', []))
                    category = metadata.get('category', '')
                    
                    # Check for matches in metadata
                    search_text = f"{title} {author} {cosponsors} {category}".lower()
                    if query_lower in search_text:
                        # Calculate relevance score
                        score = 0
                        if query_lower in title.lower():
                            score += 10  # Title match most important
                        if query_lower in author.lower():
                            score += 5
                        if query_lower in category.lower():
                            score += 3
                        if query_lower in cosponsors.lower():
                            score += 2
                            
                        results.append({
                            'title': title,
                            'filename': json_file.stem,
                            'match_type': 'metadata',
                            'score': score
                        })
                        
                except Exception as e:
                    print(f"Error reading JSON {json_file}: {e}")
                    continue
        
        # 2. Search through text file content if needed
        if len(results) < top_k and BILL_TEXT_DIR.exists():
            for txt_file in BILL_TEXT_DIR.glob("*.txt"):
                try:
                    filename_base = txt_file.stem
                    # Skip if already found in metadata
                    if any(r['filename'] == filename_base for r in results):
                        continue
                    
                    content = get_bill_content(filename_base)
                    if content and query_lower in content.lower():
                        # Extract title from filename
                        title = filename_base.replace('_', ' ').replace('-', ' ').title()
                        
                        results.append({
                            'title': title,
                            'filename': filename_base,
                            'match_type': 'content',
                            'score': 1
                        })
                        
                except Exception as e:
                    print(f"Error reading txt file {txt_file}: {e}")
                    continue
        
        # Sort by score and limit results
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        results = results[:top_k]
        
        print(f"Found {len(results)} matching bills")
        return results
        
    except Exception as e:
        print(f"Keyword search failed: {e}")
        return []

def get_bill_pdfs(search_results: List[Dict[str, Any]]) -> List[str]:
    """Get PDF file paths for search results."""
    pdf_files = []
    
    for result in search_results:
        filename = result.get('filename', '')
        if filename:
            pdf_path = BILL_PDF_DIR / f"{filename}.pdf"
            if pdf_path.exists():
                pdf_files.append(str(pdf_path))
                print(f"Found PDF: {pdf_path}")
    
    return pdf_files

def find_bill_by_title(title: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Find bills by title using fuzzy matching."""
    return search_bills_keyword(title, max_results)

def extract_google_doc_content(gdoc_url: str) -> str:
    """Extract text content from a public Google Doc."""
    # Extract file ID from URL
    match = re.search(r"/document/d/([a-zA-Z0-9-_]+)", gdoc_url)
    if not match:
        raise ValueError("Invalid Google Doc URL")
    
    file_id = match.group(1)
    export_url = f"https://docs.google.com/document/d/{file_id}/export?format=txt"
    
    response = requests.get(export_url)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch document: status {response.status_code}")
    
    return response.text

async def add_bill_to_corpus(bill_link: str) -> Dict[str, Any]:
    """Add a bill to the corpus from a Google Doc link."""
    try:
        # Extract content from Google Doc
        content = extract_google_doc_content(bill_link)
        
        # Generate filename from content (extract title)
        lines = content.strip().split('\n')
        title_line = next((line.strip() for line in lines if line.strip()), "Untitled Bill")
        
        # Clean filename
        filename = re.sub(r'[^a-zA-Z0-9\s-]', '', title_line)
        filename = re.sub(r'\s+', ' ', filename).strip()
        filename = filename.replace(' ', '_')[:50]  # Limit length
        
        # Save bill content
        save_bill_content(filename, content)
        
        # Create basic metadata
        metadata = {
            'title': title_line,
            'source_url': bill_link,
            'content_preview': content[:500] + "..." if len(content) > 500 else content
        }
        save_bill_metadata(filename, metadata)
        
        return {
            'success': True,
            'filename': filename,
            'title': title_line,
            'file_path': BILL_TEXT_DIR / f"{filename}.txt"
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def detect_bill_reference(text: str) -> Dict[str, Any]:
    """Detect bill reference pattern in text."""
    # Pattern: "HR 123", "H.R. 123", etc.
    patterns = [
        r'\b(hr|hres|hjres|hconres)\s*\.?\s*(\d+)\b',
        r'\bh\.r\.\s*(\d+)\b',
        r'\bhouse\s+(resolution|joint\s+resolution|concurrent\s+resolution)\s*(\d+)\b'
    ]
    
    text_lower = text.lower()
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            if 'h.r.' in pattern:
                bill_type = 'hr'
                number = int(match.group(1))
            elif 'resolution' in pattern:
                res_type = match.group(1)
                number = int(match.group(2))
                if 'joint' in res_type:
                    bill_type = 'hjres'
                elif 'concurrent' in res_type:
                    bill_type = 'hconres'
                else:
                    bill_type = 'hres'
            else:
                bill_type = match.group(1).lower()
                number = int(match.group(2))
            
            return {
                'success': True,
                'bill_type': bill_type,
                'reference_number': number,
                'message': f"Detected {bill_type.upper()} {number}"
            }
    
    return {
        'success': False,
        'message': "No bill reference pattern detected"
    }

async def generate_economic_impact_report(bill_link: str, recent_news: List[str], additional_context: str = None) -> str:
    """Generate an economic impact report for a bill using AI."""
    from ai_tools import call_gemini_for_report
    
    try:
        # Get bill content
        bill_content = extract_google_doc_content(bill_link)
        
        # Build context
        news_context = "\n".join(recent_news[:10]) if recent_news else "No recent news available."
        
        context = f"""
        Bill Content:
        {bill_content[:5000]}  # Limit content size
        
        Recent News Context:
        {news_context}
        
        Additional Context:
        {additional_context or "None provided"}
        """
        
        # Generate report using AI
        report = await call_gemini_for_report(
            bill_content=bill_content,
            context=context,
            report_type="economic_impact"
        )
        
        return report
        
    except Exception as e:
        return f"Failed to generate economic impact report: {e}"