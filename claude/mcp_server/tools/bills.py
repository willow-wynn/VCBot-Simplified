"""
Bill management tools for MCP server
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import config
import bill_utils
from ai_tools import fetch_document_content

class BillTools:
    """Tools for bill search and management"""
    
    def __init__(self):
        self.bill_text_dir = config.BILL_TEXT_DIR
        self.bill_pdf_dir = config.BILL_PDF_DIR
        self.bill_json_dir = config.BILL_JSON_DIR
    
    async def search_bills(
        self,
        query: str,
        limit: int = 5,
        search_type: str = "keyword"
    ) -> List[Dict[str, Any]]:
        """Search for bills in the legislative corpus"""
        
        # Enforce reasonable limits
        limit = min(limit, 10)
        
        # Use existing bill search functionality
        results = bill_utils.search_bills_keyword(query, limit)
        
        # Format results with additional metadata
        formatted_results = []
        for result in results:
            filename = result.get("filename", result.get("title", ""))
            
            # Get additional metadata if available
            json_path = self.bill_json_dir / f"{filename}.json"
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
                "pdf_available": (self.bill_pdf_dir / f"{filename}.pdf").exists(),
                "text_available": (self.bill_text_dir / f"{filename}.txt").exists(),
                "json_available": json_path.exists()
            }
            
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    async def get_bill_details(
        self,
        bill_title: str,
        include_full_text: bool = False,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Get detailed information about a specific bill"""
        
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
            "score": bill.get("score", 0)
        }
        
        # Get metadata if requested
        if include_metadata:
            json_path = self.bill_json_dir / f"{filename}.json"
            if json_path.exists():
                try:
                    with open(json_path, 'r') as f:
                        metadata = json.load(f)
                        response["metadata"] = metadata
                except Exception as e:
                    response["metadata_error"] = f"Failed to load metadata: {str(e)}"
        
        # Get full text if requested
        if include_full_text:
            text_path = self.bill_text_dir / f"{filename}.txt"
            if text_path.exists():
                try:
                    with open(text_path, 'r', encoding='utf-8') as f:
                        full_text = f.read()
                        response["full_text"] = full_text
                        response["text_length"] = len(full_text)
                except Exception as e:
                    response["text_error"] = f"Failed to load full text: {str(e)}"
            else:
                response["text_error"] = "Full text file not found"
        
        # Check file availability
        response["files"] = {
            "pdf_exists": (self.bill_pdf_dir / f"{filename}.pdf").exists(),
            "text_exists": (self.bill_text_dir / f"{filename}.txt").exists(),
            "json_exists": (self.bill_json_dir / f"{filename}.json").exists()
        }
        
        return response
    
    async def get_bill_pdf(
        self,
        bill_title: str
    ) -> Dict[str, Any]:
        """Get PDF file information for a bill"""
        
        # Search for the bill first
        results = bill_utils.search_bills_keyword(bill_title, 1)
        
        if not results:
            return {
                "error": "Bill not found",
                "query": bill_title
            }
        
        bill = results[0]
        filename = bill.get("filename", "")
        pdf_path = self.bill_pdf_dir / f"{filename}.pdf"
        
        if pdf_path.exists():
            return {
                "title": bill.get("title", filename),
                "filename": filename,
                "pdf_path": str(pdf_path),
                "pdf_size": pdf_path.stat().st_size,
                "pdf_exists": True,
                "download_note": "PDF file is available for download through Discord bot commands"
            }
        else:
            return {
                "title": bill.get("title", filename),
                "filename": filename,
                "pdf_exists": False,
                "error": "PDF file not found"
            }
    
    async def add_bill_from_url(
        self,
        google_docs_url: str,
        bill_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a new bill from a Google Docs URL"""
        
        try:
            # Fetch document content
            doc_content = await fetch_document_content(google_docs_url)
            
            if not doc_content:
                return {
                    "success": False,
                    "error": "Failed to fetch document content from URL",
                    "url": google_docs_url
                }
            
            # Extract title from content if not provided
            if not bill_title:
                lines = doc_content.split('\n')
                for line in lines:
                    if line.strip() and len(line.strip()) > 10:
                        bill_title = line.strip()
                        break
                
                if not bill_title:
                    bill_title = f"Untitled Bill from {google_docs_url.split('/')[5] if '/' in google_docs_url else 'Unknown'}"
            
            # Create filename from title
            filename = bill_title.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = ''.join(c for c in filename if c.isalnum() or c in '_-')
            
            # Save text file
            text_path = self.bill_text_dir / f"{filename}.txt"
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(doc_content)
            
            # Create metadata
            metadata = {
                "title": bill_title,
                "source_url": google_docs_url,
                "date_added": "2024-01-01",  # Would use actual date
                "status": "Draft",
                "author": "Unknown",
                "summary": doc_content[:500] + "..." if len(doc_content) > 500 else doc_content
            }
            
            # Save metadata
            json_path = self.bill_json_dir / f"{filename}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                "success": True,
                "title": bill_title,
                "filename": filename,
                "text_path": str(text_path),
                "json_path": str(json_path),
                "content_length": len(doc_content),
                "source_url": google_docs_url
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to add bill: {str(e)}",
                "url": google_docs_url
            }
    
    async def list_recent_bills(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recently added bills"""
        
        # Get recent JSON files sorted by modification time
        json_files = sorted(
            self.bill_json_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]
        
        bills = []
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    metadata = json.load(f)
                    
                    bills.append({
                        "title": metadata.get("title", json_file.stem),
                        "filename": json_file.stem,
                        "author": metadata.get("author", "Unknown"),
                        "status": metadata.get("status", "Unknown"),
                        "date_added": metadata.get("date_added", "Unknown"),
                        "summary": metadata.get("summary", "")[:200] + "..." if metadata.get("summary", "") else "",
                        "last_modified": json_file.stat().st_mtime
                    })
            except:
                # Skip files with JSON errors
                continue
        
        return bills
    
    async def get_bill_statistics(self) -> Dict[str, Any]:
        """Get statistics about the bill corpus"""
        
        # Count files
        text_files = list(self.bill_text_dir.glob("*.txt"))
        pdf_files = list(self.bill_pdf_dir.glob("*.pdf"))
        json_files = list(self.bill_json_dir.glob("*.json"))
        
        # Calculate sizes
        total_text_size = sum(f.stat().st_size for f in text_files)
        total_pdf_size = sum(f.stat().st_size for f in pdf_files)
        
        return {
            "total_bills": len(json_files),
            "text_files": len(text_files),
            "pdf_files": len(pdf_files),
            "json_files": len(json_files),
            "total_text_size_mb": round(total_text_size / (1024 * 1024), 2),
            "total_pdf_size_mb": round(total_pdf_size / (1024 * 1024), 2),
            "directories": {
                "text": str(self.bill_text_dir),
                "pdf": str(self.bill_pdf_dir),
                "json": str(self.bill_json_dir)
            }
        }