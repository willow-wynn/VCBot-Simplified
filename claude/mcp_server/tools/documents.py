"""
Document processing tools for MCP server
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from ai_tools import fetch_document_content

class DocumentTools:
    """Tools for document fetching and analysis"""
    
    def __init__(self):
        pass
    
    async def fetch_google_doc(
        self,
        doc_url: str,
        extract_sections: bool = False,
        analyze_content: bool = False
    ) -> Dict[str, Any]:
        """Fetch and parse a Google Doc"""
        
        try:
            # Validate URL
            if not doc_url or "docs.google.com" not in doc_url:
                return {
                    "status": "error",
                    "error": "Invalid Google Docs URL",
                    "url": doc_url
                }
            
            # Extract document ID
            doc_id = None
            if "/d/" in doc_url:
                doc_id = doc_url.split('/d/')[1].split('/')[0]
            
            # Fetch document content
            content = await fetch_document_content(doc_url)
            
            if not content:
                return {
                    "status": "error",
                    "error": "Failed to fetch document content or document is empty",
                    "url": doc_url,
                    "doc_id": doc_id
                }
            
            result = {
                "status": "success",
                "url": doc_url,
                "doc_id": doc_id,
                "content": content,
                "content_length": len(content),
                "word_count": len(content.split()),
                "line_count": len(content.split('\n'))
            }
            
            # Extract sections if requested
            if extract_sections:
                sections = self._extract_sections(content)
                result["sections"] = sections
                result["section_count"] = len(sections)
            
            # Perform content analysis if requested
            if analyze_content:
                analysis = self._analyze_content(content)
                result["analysis"] = analysis
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to fetch Google Doc: {str(e)}",
                "url": doc_url
            }
    
    def _extract_sections(self, content: str) -> list:
        """Extract sections from document content"""
        
        sections = []
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Identify section headers (all caps, starts with number, or starts with #)
            if (line and 
                (line.isupper() or 
                 line.startswith('#') or 
                 (line[0].isdigit() and '.' in line[:10]))):
                
                # Save previous section
                if current_section:
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    "title": line,
                    "content": [],
                    "word_count": 0
                }
            
            elif current_section and line:
                current_section["content"].append(line)
        
        # Add the last section
        if current_section:
            sections.append(current_section)
        
        # Calculate word counts
        for section in sections:
            section["content_text"] = '\n'.join(section["content"])
            section["word_count"] = len(section["content_text"].split())
        
        return sections
    
    def _analyze_content(self, content: str) -> dict:
        """Analyze document content for key characteristics"""
        
        lines = content.split('\n')
        words = content.split()
        
        # Basic statistics
        analysis = {
            "total_lines": len(lines),
            "total_words": len(words),
            "total_characters": len(content),
            "average_words_per_line": round(len(words) / len(lines), 2) if lines else 0,
            "document_type": "unknown"
        }
        
        # Detect document type based on content patterns
        content_lower = content.lower()
        
        if any(term in content_lower for term in ["section", "act", "bill", "amendment"]):
            analysis["document_type"] = "legislation"
        elif any(term in content_lower for term in ["whereas", "resolved", "resolution"]):
            analysis["document_type"] = "resolution"
        elif any(term in content_lower for term in ["executive order", "memorandum", "directive"]):
            analysis["document_type"] = "executive_document"
        elif any(term in content_lower for term in ["minutes", "meeting", "agenda"]):
            analysis["document_type"] = "meeting_document"
        elif any(term in content_lower for term in ["report", "analysis", "findings"]):
            analysis["document_type"] = "report"
        
        # Identify key topics
        key_terms = {
            "economic": ["economy", "economic", "budget", "tax", "spending", "inflation", "gdp"],
            "healthcare": ["health", "healthcare", "medical", "insurance", "medicare", "medicaid"],
            "education": ["education", "school", "university", "student", "teacher"],
            "defense": ["defense", "military", "security", "army", "navy", "air force"],
            "environment": ["environment", "climate", "pollution", "conservation", "energy"],
            "technology": ["technology", "cyber", "digital", "internet", "ai", "artificial intelligence"]
        }
        
        topic_scores = {}
        for topic, terms in key_terms.items():
            score = sum(content_lower.count(term) for term in terms)
            if score > 0:
                topic_scores[topic] = score
        
        analysis["topic_scores"] = topic_scores
        analysis["primary_topics"] = sorted(topic_scores.keys(), key=lambda x: topic_scores[x], reverse=True)[:3]
        
        return analysis
    
    async def analyze_document_impact(
        self,
        doc_url: str,
        analysis_type: str = "economic",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze document for policy or economic impact"""
        
        # First, fetch the document
        doc_result = await self.fetch_google_doc(doc_url, extract_sections=True, analyze_content=True)
        
        if doc_result["status"] == "error":
            return doc_result
        
        content = doc_result["content"]
        sections = doc_result.get("sections", [])
        content_analysis = doc_result.get("analysis", {})
        
        # Perform impact analysis based on type
        try:
            if analysis_type == "economic":
                impact_analysis = self._analyze_economic_impact(content, sections, context)
            elif analysis_type == "policy":
                impact_analysis = self._analyze_policy_impact(content, sections, context)
            elif analysis_type == "legislative":
                impact_analysis = self._analyze_legislative_impact(content, sections, context)
            else:
                impact_analysis = self._analyze_general_impact(content, sections, context)
            
            return {
                "status": "success",
                "document": {
                    "url": doc_url,
                    "doc_id": doc_result["doc_id"],
                    "content_length": doc_result["content_length"],
                    "section_count": len(sections)
                },
                "content_analysis": content_analysis,
                "impact_analysis": impact_analysis,
                "analysis_type": analysis_type,
                "context": context
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to analyze document impact: {str(e)}",
                "url": doc_url,
                "analysis_type": analysis_type
            }
    
    def _analyze_economic_impact(self, content: str, sections: list, context: Optional[str]) -> dict:
        """Analyze document for economic impact"""
        
        content_lower = content.lower()
        
        # Economic indicators to look for
        economic_terms = {
            "fiscal": ["budget", "spending", "revenue", "deficit", "surplus", "appropriation"],
            "monetary": ["interest", "inflation", "federal reserve", "monetary policy"],
            "taxation": ["tax", "deduction", "credit", "exemption", "levy"],
            "employment": ["job", "employment", "unemployment", "worker", "labor"],
            "trade": ["trade", "import", "export", "tariff", "commerce"],
            "financial": ["financial", "banking", "investment", "market", "securities"]
        }
        
        impact_scores = {}
        for category, terms in economic_terms.items():
            score = sum(content_lower.count(term) for term in terms)
            if score > 0:
                impact_scores[category] = score
        
        # Estimate impact magnitude
        total_economic_mentions = sum(impact_scores.values())
        if total_economic_mentions > 20:
            magnitude = "high"
        elif total_economic_mentions > 10:
            magnitude = "medium"
        elif total_economic_mentions > 0:
            magnitude = "low"
        else:
            magnitude = "minimal"
        
        return {
            "type": "economic",
            "magnitude": magnitude,
            "total_economic_mentions": total_economic_mentions,
            "category_scores": impact_scores,
            "primary_categories": sorted(impact_scores.keys(), key=lambda x: impact_scores[x], reverse=True)[:3],
            "fiscal_impact": "high" if impact_scores.get("fiscal", 0) > 5 else "low",
            "market_impact": "high" if impact_scores.get("financial", 0) > 3 else "low",
            "recommendations": [
                "Conduct detailed fiscal analysis" if impact_scores.get("fiscal", 0) > 3 else None,
                "Assess market implications" if impact_scores.get("financial", 0) > 2 else None,
                "Review employment effects" if impact_scores.get("employment", 0) > 2 else None
            ]
        }
    
    def _analyze_policy_impact(self, content: str, sections: list, context: Optional[str]) -> dict:
        """Analyze document for policy impact"""
        
        content_lower = content.lower()
        
        # Policy areas to analyze
        policy_areas = {
            "regulatory": ["regulation", "rule", "compliance", "oversight", "enforcement"],
            "social": ["social", "welfare", "benefits", "assistance", "support"],
            "environmental": ["environment", "climate", "pollution", "conservation"],
            "healthcare": ["health", "healthcare", "medical", "treatment", "care"],
            "education": ["education", "school", "student", "teacher", "learning"],
            "defense": ["defense", "security", "military", "protection", "safety"]
        }
        
        policy_scores = {}
        for area, terms in policy_areas.items():
            score = sum(content_lower.count(term) for term in terms)
            if score > 0:
                policy_scores[area] = score
        
        return {
            "type": "policy",
            "affected_areas": list(policy_scores.keys()),
            "area_scores": policy_scores,
            "primary_areas": sorted(policy_scores.keys(), key=lambda x: policy_scores[x], reverse=True)[:3],
            "scope": "broad" if len(policy_scores) > 3 else "focused",
            "complexity": "high" if sum(policy_scores.values()) > 15 else "moderate"
        }
    
    def _analyze_legislative_impact(self, content: str, sections: list, context: Optional[str]) -> dict:
        """Analyze document for legislative impact"""
        
        content_lower = content.lower()
        
        # Legislative characteristics
        legislative_elements = {
            "amendments": content_lower.count("amend"),
            "new_provisions": content_lower.count("establish") + content_lower.count("create"),
            "repeals": content_lower.count("repeal") + content_lower.count("revoke"),
            "deadlines": content_lower.count("deadline") + content_lower.count("within"),
            "penalties": content_lower.count("penalty") + content_lower.count("fine"),
            "funding": content_lower.count("fund") + content_lower.count("appropriat")
        }
        
        return {
            "type": "legislative",
            "elements": legislative_elements,
            "primary_actions": [k for k, v in legislative_elements.items() if v > 0],
            "complexity_score": sum(legislative_elements.values()),
            "implementation_requirements": "high" if legislative_elements["funding"] > 2 else "moderate"
        }
    
    def _analyze_general_impact(self, content: str, sections: list, context: Optional[str]) -> dict:
        """Perform general document impact analysis"""
        
        return {
            "type": "general",
            "word_count": len(content.split()),
            "section_count": len(sections),
            "complexity": "high" if len(content.split()) > 5000 else "moderate",
            "scope": "comprehensive" if len(sections) > 10 else "focused",
            "note": "General analysis performed. Use specific analysis types for detailed impact assessment."
        }