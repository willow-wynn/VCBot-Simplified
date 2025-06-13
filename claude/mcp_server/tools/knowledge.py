"""
Knowledge base tools for MCP server
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import config
import file_utils

class KnowledgeTools:
    """Tools for knowledge base access and search"""
    
    def __init__(self):
        self.knowledge_dir = config.KNOWLEDGE_DIR
        self.available_files = {
            "rules": "General Virtual Congress rules and procedures",
            "constitution": "The Virtual Congress Constitution",
            "house_rules": "House of Representatives specific rules",
            "senate_rules": "Senate specific rules",
            "rnr": "Rules and Regulations reference",
            "houserules": "House-specific operating procedures"
        }
    
    async def get_knowledge_file(self, file_name: str) -> Dict[str, Any]:
        """Access knowledge base files"""
        
        # Validate file name
        if file_name not in self.available_files:
            return {
                "status": "error",
                "error": f"Unknown knowledge file: {file_name}",
                "available_files": list(self.available_files.keys()),
                "file_descriptions": self.available_files
            }
        
        try:
            # Use existing file reading functionality
            content = file_utils.read_knowledge_file(file_name)
            
            if "Error" in content or "not found" in content.lower():
                return {
                    "status": "error",
                    "file_name": file_name,
                    "error": content
                }
            
            # Get file metadata
            file_path = self.knowledge_dir / f"{file_name}.txt"
            metadata = {}
            
            if file_path.exists():
                stat = file_path.stat()
                metadata = {
                    "file_size": stat.st_size,
                    "last_modified": stat.st_mtime,
                    "file_path": str(file_path)
                }
            
            return {
                "status": "success",
                "file_name": file_name,
                "description": self.available_files[file_name],
                "content": content,
                "content_length": len(content),
                "word_count": len(content.split()),
                "line_count": len(content.split('\n')),
                "metadata": metadata
            }
            
        except Exception as e:
            return {
                "status": "error",
                "file_name": file_name,
                "error": f"Failed to read knowledge file: {str(e)}"
            }
    
    async def search_knowledge_base(
        self,
        query: str,
        file_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Search across knowledge base files"""
        
        if not query or len(query.strip()) < 2:
            return {
                "status": "error",
                "error": "Query must be at least 2 characters long",
                "query": query
            }
        
        # Determine which files to search
        files_to_search = file_filter if file_filter else list(self.available_files.keys())
        
        # Validate file filter
        if file_filter:
            invalid_files = [f for f in file_filter if f not in self.available_files]
            if invalid_files:
                return {
                    "status": "error",
                    "error": f"Unknown files in filter: {invalid_files}",
                    "available_files": list(self.available_files.keys())
                }
        
        search_results = []
        query_lower = query.lower()
        
        for file_name in files_to_search:
            try:
                # Get file content
                file_result = await self.get_knowledge_file(file_name)
                
                if file_result["status"] == "error":
                    continue
                
                content = file_result["content"]
                content_lower = content.lower()
                
                # Search for query in content
                if query_lower in content_lower:
                    # Find all occurrences and extract context
                    matches = self._find_matches_with_context(content, query, context_chars=200)
                    
                    if matches:
                        search_results.append({
                            "file_name": file_name,
                            "description": self.available_files[file_name],
                            "match_count": len(matches),
                            "matches": matches,
                            "relevance_score": len(matches) + content_lower.count(query_lower)
                        })
                        
            except Exception as e:
                # Skip files that can't be processed
                continue
        
        # Sort results by relevance
        search_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return {
            "status": "success",
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
    
    def _find_matches_with_context(self, content: str, query: str, context_chars: int = 200) -> List[Dict[str, Any]]:
        """Find query matches and extract surrounding context"""
        
        matches = []
        content_lower = content.lower()
        query_lower = query.lower()
        
        start = 0
        while True:
            # Find next occurrence
            index = content_lower.find(query_lower, start)
            if index == -1:
                break
            
            # Extract context around the match
            context_start = max(0, index - context_chars // 2)
            context_end = min(len(content), index + len(query) + context_chars // 2)
            
            context = content[context_start:context_end]
            
            # Find the position within the context
            relative_start = index - context_start
            relative_end = relative_start + len(query)
            
            matches.append({
                "position": index,
                "context": context,
                "match_start": relative_start,
                "match_end": relative_end,
                "matched_text": content[index:index + len(query)]
            })
            
            # Move to next potential match
            start = index + 1
        
        return matches
    
    async def list_knowledge_files(self) -> Dict[str, Any]:
        """List all available knowledge base files"""
        
        file_details = {}
        
        for file_name, description in self.available_files.items():
            file_path = self.knowledge_dir / f"{file_name}.txt"
            
            file_info = {
                "description": description,
                "exists": file_path.exists(),
                "file_path": str(file_path)
            }
            
            if file_path.exists():
                try:
                    stat = file_path.stat()
                    content = file_path.read_text(encoding='utf-8')
                    
                    file_info.update({
                        "file_size": stat.st_size,
                        "last_modified": stat.st_mtime,
                        "content_length": len(content),
                        "word_count": len(content.split()),
                        "line_count": len(content.split('\n'))
                    })
                except Exception as e:
                    file_info["error"] = f"Failed to read file metadata: {str(e)}"
            
            file_details[file_name] = file_info
        
        return {
            "status": "success",
            "total_files": len(self.available_files),
            "available_files": len([f for f in file_details.values() if f["exists"]]),
            "missing_files": len([f for f in file_details.values() if not f["exists"]]),
            "files": file_details,
            "knowledge_directory": str(self.knowledge_dir)
        }
    
    async def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get a summary of all knowledge base content"""
        
        summary = {
            "status": "success",
            "files_processed": 0,
            "total_words": 0,
            "total_characters": 0,
            "file_summaries": {},
            "common_topics": {},
            "cross_references": []
        }
        
        # Process each available file
        for file_name in self.available_files.keys():
            try:
                file_result = await self.get_knowledge_file(file_name)
                
                if file_result["status"] == "success":
                    content = file_result["content"]
                    
                    summary["files_processed"] += 1
                    summary["total_words"] += file_result["word_count"]
                    summary["total_characters"] += file_result["content_length"]
                    
                    # Create file summary
                    file_summary = {
                        "word_count": file_result["word_count"],
                        "description": self.available_files[file_name],
                        "key_terms": self._extract_key_terms(content),
                        "structure": self._analyze_structure(content)
                    }
                    
                    summary["file_summaries"][file_name] = file_summary
                    
            except Exception as e:
                continue
        
        # Analyze common topics across files
        all_terms = {}
        for file_summary in summary["file_summaries"].values():
            for term, count in file_summary["key_terms"].items():
                all_terms[term] = all_terms.get(term, 0) + count
        
        # Get most common terms
        summary["common_topics"] = dict(
            sorted(all_terms.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        return summary
    
    def _extract_key_terms(self, content: str) -> Dict[str, int]:
        """Extract key terms from content"""
        
        # Simple term extraction (could be enhanced with NLP)
        words = content.lower().split()
        
        # Filter out common words and short words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
            "with", "by", "from", "as", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "shall", "this", "that", "these", "those"
        }
        
        filtered_words = [
            word.strip('.,!?;:"()[]{}') for word in words
            if len(word) > 3 and word.lower() not in stop_words
        ]
        
        # Count occurrences
        term_counts = {}
        for word in filtered_words:
            if word.isalpha():  # Only include alphabetic words
                term_counts[word] = term_counts.get(word, 0) + 1
        
        # Return top terms
        return dict(sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:15])
    
    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure"""
        
        lines = content.split('\n')
        
        structure = {
            "total_lines": len(lines),
            "empty_lines": len([line for line in lines if not line.strip()]),
            "sections": 0,
            "subsections": 0,
            "has_numbered_items": False,
            "has_bullet_points": False
        }
        
        for line in lines:
            line = line.strip()
            
            # Count sections (all caps lines or lines starting with numbers)
            if line and (line.isupper() or (line[0].isdigit() and '.' in line[:10])):
                if len(line) < 100:  # Likely a header, not a long sentence
                    structure["sections"] += 1
            
            # Count subsections (lines starting with letters or Roman numerals)
            if line and len(line) < 100:
                if (line.startswith(('a.', 'b.', 'c.', 'i.', 'ii.', 'iii.')) or
                    line.startswith(('A.', 'B.', 'C.', 'I.', 'II.', 'III.'))):
                    structure["subsections"] += 1
            
            # Check for numbered items
            if line and line[0].isdigit() and ')' in line[:5]:
                structure["has_numbered_items"] = True
            
            # Check for bullet points
            if line.startswith(('•', '-', '*')):
                structure["has_bullet_points"] = True
        
        return structure