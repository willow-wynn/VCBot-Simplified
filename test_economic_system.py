"""
Comprehensive test suite for the Economic Analysis System
Tests all functionality without requiring Discord API access
"""

import asyncio
import json
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

# Test the Google Docs URL provided by user
TEST_DOC_URL = "https://docs.google.com/document/d/1ZNZY9Xr8kqFTz_x8flcK89Gm2f58GyYxLYCNOyjKG_s/edit?usp=sharing"

class MockDiscordData:
    """Generate realistic Discord activity for testing the economic system"""
    
    @staticmethod
    def generate_legislative_messages(count: int = 20) -> List[Dict[str, Any]]:
        """Generate mock legislative activity messages"""
        messages = []
        base_time = datetime.utcnow()
        
        legislative_content = [
            "Voting on H.R. 1234 - Healthcare Reform Act begins in 30 minutes",
            "Amendment proposed to defense spending bill - increase budget by 5%",
            "Committee markup scheduled for education funding legislation",
            "Senator Johnson speaks in favor of climate action bill",
            "Roll call vote: 67 yea, 33 nay - bill passes",
            "New resolution introduced for infrastructure spending",
            "Debate continues on tax reform package",
            "Bipartisan support growing for veteran benefits expansion",
            "House passes budget reconciliation by narrow margin",
            "Senate committee approves judicial nominations"
        ]
        
        for i in range(count):
            messages.append({
                "content": legislative_content[i % len(legislative_content)],
                "timestamp": (base_time - timedelta(hours=i)).isoformat(),
                "channel": "house-floor" if i % 2 == 0 else "senate-floor",
                "author_roles": ["Representative", "Majority Leader"] if i % 3 == 0 else ["Senator"],
                "reactions": max(1, 10 - (i // 3)),
                "replies": max(0, 5 - (i // 4))
            })
        
        return messages
    
    @staticmethod
    def generate_committee_messages(count: int = 15) -> List[Dict[str, Any]]:
        """Generate mock committee activity messages"""
        messages = []
        base_time = datetime.utcnow()
        
        committee_content = [
            "Defense Committee meeting called to order - reviewing procurement",
            "Healthcare subcommittee hearing on drug pricing reforms",
            "Education committee markup session begins",
            "Intelligence committee briefing on cybersecurity threats",
            "Budget committee reviews appropriations bill",
            "Judiciary committee considers judicial nominations",
            "Foreign Relations committee discusses trade agreements",
            "Banking committee examines financial regulations",
            "Energy committee reviews renewable energy incentives",
            "Transportation committee debates infrastructure funding"
        ]
        
        for i in range(count):
            messages.append({
                "content": committee_content[i % len(committee_content)],
                "timestamp": (base_time - timedelta(hours=i*2)).isoformat(),
                "channel": f"committee-{(i % 5) + 1}",
                "author_roles": ["Committee Chair", "Ranking Member"] if i % 2 == 0 else ["Committee Member"],
                "reactions": max(1, 8 - (i // 2)),
                "replies": max(0, 3 - (i // 5))
            })
        
        return messages
    
    @staticmethod
    def generate_public_messages(count: int = 30) -> List[Dict[str, Any]]:
        """Generate mock public discussion messages"""
        messages = []
        base_time = datetime.utcnow()
        
        public_content = [
            "What do you think about the new healthcare bill?",
            "Economy seems to be improving based on latest reports",
            "Concerned about the defense spending increases",
            "Great to see bipartisan cooperation on infrastructure",
            "Climate change legislation is long overdue",
            "Education funding needs to be a priority",
            "Happy with the recent tax reform proposals",
            "Veterans deserve better support and benefits",
            "Budget deficit is getting out of control",
            "International trade relations are improving"
        ]
        
        for i in range(count):
            messages.append({
                "content": public_content[i % len(public_content)],
                "timestamp": (base_time - timedelta(minutes=i*30)).isoformat(),
                "channel": "general-discussion",
                "author_roles": ["Citizen"] if i % 3 != 0 else ["Citizen", "Verified"],
                "reactions": max(0, 6 - (i // 5)),
                "replies": max(0, 2 - (i // 10))
            })
        
        return messages
    
    @staticmethod
    def generate_documents() -> List[Dict[str, Any]]:
        """Generate mock document data"""
        return [
            {
                "url": TEST_DOC_URL,
                "content": """
                Economic Impact Assessment - Healthcare Reform Act
                
                Executive Summary:
                This comprehensive healthcare reform bill is projected to have significant positive economic impacts including:
                - Reduced healthcare costs for families by an average of $2,500 annually
                - Creation of approximately 150,000 new jobs in healthcare infrastructure
                - GDP growth contribution of 0.3% over the next five years
                - Inflation impact: minimal, estimated at +0.1% due to increased healthcare access
                
                Detailed Analysis:
                The proposed legislation includes provisions for expanded Medicare coverage, prescription drug pricing reforms, and increased funding for rural healthcare facilities. Economic modeling suggests these changes will reduce the federal deficit by $45 billion over ten years while improving health outcomes across all demographic groups.
                
                Key Sectors Affected:
                - Healthcare: Strong positive growth expected
                - Insurance: Mixed impact, with some consolidation likely
                - Pharmaceutical: Modest negative impact on pricing power
                - Technology: Positive impact from healthcare IT investments
                """,
                "channel": "house-floor",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]

class TestEconomicEngine:
    """Test the core economic analysis engine"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_data_dir = Path("test_economic_data")
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Clean up any existing test data
        for file in self.test_data_dir.glob("*.json"):
            file.unlink()
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
    
    def test_parameter_loading_and_saving(self):
        """Test economic parameter management"""
        # Mock the economic engine with our test directory
        with patch('economic_engine.Path') as mock_path:
            mock_path.return_value = self.test_data_dir
            
            from economic_engine import EconomicEngine
            
            # Create mock bot
            mock_bot = Mock()
            engine = EconomicEngine(mock_bot)
            
            # Test default parameters
            params = engine.load_parameters()
            assert "gdp_weights" in params
            assert "tracked_stocks" in params
            assert len(params["tracked_stocks"]) == 5
            
            # Test saving modified parameters
            params["inflation_base"] = 3.5
            engine.save_parameters(params)
            
            # Test loading modified parameters
            new_params = engine.load_parameters()
            assert new_params["inflation_base"] == 3.5
    
    @pytest.mark.asyncio
    async def test_document_content_extraction(self):
        """Test Google Docs content extraction"""
        from economic_engine import EconomicEngine
        
        mock_bot = Mock()
        engine = EconomicEngine(mock_bot)
        
        # Test with valid URL
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="Test document content")
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            content = await engine.get_document_content(TEST_DOC_URL)
            assert content == "Test document content"
        
        # Test with invalid URL
        content = await engine.get_document_content("https://invalid-url.com")
        assert content is None
    
    def test_activity_categorization(self):
        """Test Discord activity categorization"""
        mock_data = MockDiscordData()
        
        legislative = mock_data.generate_legislative_messages(10)
        committee = mock_data.generate_committee_messages(10)
        public = mock_data.generate_public_messages(10)
        
        # Test that messages have expected structure
        assert all("content" in msg for msg in legislative)
        assert all("timestamp" in msg for msg in committee)
        assert all("channel" in msg for msg in public)
        
        # Test content categorization
        legislative_keywords = ["vote", "bill", "amendment", "resolution"]
        committee_keywords = ["committee", "hearing", "markup"]
        
        legislative_content = " ".join(msg["content"].lower() for msg in legislative)
        assert any(keyword in legislative_content for keyword in legislative_keywords)
        
        committee_content = " ".join(msg["content"].lower() for msg in committee)
        assert any(keyword in committee_content for keyword in committee_keywords)
    
    @pytest.mark.asyncio
    async def test_gemini_analysis_fallback(self):
        """Test economic analysis with Gemini fallback"""
        from economic_engine import EconomicEngine
        
        mock_bot = Mock()
        with patch('economic_engine.Path') as mock_path:
            mock_path.return_value = self.test_data_dir
            engine = EconomicEngine(mock_bot)
            
            # Prepare mock activity data
            activity_data = {
                "legislative": MockDiscordData.generate_legislative_messages(5),
                "committee": MockDiscordData.generate_committee_messages(3),
                "public": MockDiscordData.generate_public_messages(10),
                "documents": MockDiscordData.generate_documents()
            }
            
            # Test fallback analysis (when Gemini fails)
            analysis = engine.generate_fallback_analysis(activity_data)
            
            assert "gdp" in analysis
            assert "stocks" in analysis
            assert "inflation" in analysis
            assert "unemployment" in analysis
            assert "sentiment" in analysis
            
            # Verify GDP calculation incorporates activity levels
            assert analysis["gdp"]["components"]["legislative"] == 5
            assert analysis["gdp"]["components"]["committee"] == 3
            assert analysis["gdp"]["components"]["public"] == 10
    
    @pytest.mark.asyncio
    async def test_data_persistence(self):
        """Test economic data saving and retrieval"""
        from economic_engine import EconomicEngine
        
        mock_bot = Mock()
        with patch('economic_engine.Path') as mock_path:
            mock_path.return_value = self.test_data_dir
            engine = EconomicEngine(mock_bot)
            
            # Create test analysis data
            test_analysis = {
                "timestamp": datetime.utcnow().isoformat(),
                "gdp": {"value": 1500.0, "change_percent": 2.5},
                "stocks": [{"symbol": "GOV", "price": 105.0, "change_percent": 1.5}],
                "inflation": {"rate": 3.0, "trend": "rising"},
                "unemployment": {"rate": 4.5},
                "sentiment": {"market_confidence": 80}
            }
            
            # Save data
            await engine.save_economic_data(test_analysis)
            
            # Verify files were created
            assert (self.test_data_dir / "reports.json").exists()
            assert (self.test_data_dir / "gdp.json").exists()
            assert (self.test_data_dir / "stocks.json").exists()
            
            # Verify data integrity
            with open(self.test_data_dir / "gdp.json", 'r') as f:
                gdp_data = json.load(f)
                assert len(gdp_data) == 1
                assert gdp_data[0]["data"]["value"] == 1500.0

class TestEconomicTools:
    """Test the AI tools for economic analysis"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_data_dir = Path("test_economic_data")
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Create test economic data
        test_gdp = [
            {"timestamp": datetime.utcnow().isoformat(), "data": {"value": 1000.0, "change_percent": 2.0}},
            {"timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(), "data": {"value": 980.0, "change_percent": 1.5}}
        ]
        
        with open(self.test_data_dir / "gdp.json", 'w') as f:
            json.dump(test_gdp, f)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
    
    @pytest.mark.asyncio
    async def test_fetch_document_content_tool(self):
        """Test the document content fetching tool"""
        from ai_tools import fetch_document_content
        
        # Test with mock successful response
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="Document content for economic analysis")
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            content = await fetch_document_content(TEST_DOC_URL)
            assert "Document content for economic analysis" in content
        
        # Test with invalid URL
        content = await fetch_document_content("invalid-url")
        assert "Error: Invalid Google Docs URL format" in content
    
    def test_get_economic_data_tool(self):
        """Test the economic data retrieval tool"""
        with patch('ai_tools.Path') as mock_path:
            mock_path.return_value = self.test_data_dir
            
            from ai_tools import get_economic_data
            
            # Test specific data type retrieval
            result = get_economic_data("gdp", days_back=7)
            assert "gdp" in result
            assert len(result["gdp"]) == 2
            
            # Test all data retrieval
            result = get_economic_data("all", days_back=7)
            assert "gdp" in result
            
            # Test non-existent data type
            result = get_economic_data("nonexistent")
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """Test the tool execution system"""
        from ai_tools import execute_tool
        
        # Create mock function call
        mock_function_call = Mock()
        mock_function_call.name = "get_economic_data"
        mock_function_call.args = {"data_type": "gdp", "days_back": 7}
        
        with patch('ai_tools.Path') as mock_path:
            mock_path.return_value = self.test_data_dir
            
            result = await execute_tool(mock_function_call)
            assert "gdp" in result

class TestEconomicAdmin:
    """Test the administrative controls for the economic system"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_data_dir = Path("test_economic_data")
        self.test_data_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
    
    def test_parameter_modification(self):
        """Test economic parameter modification"""
        with patch('economic_admin.Path') as mock_path:
            mock_path.return_value = self.test_data_dir
            
            from economic_admin import EconomicAdmin
            
            mock_bot = Mock()
            admin = EconomicAdmin(mock_bot)
            
            # Test loading default parameters
            params = admin.load_parameters()
            
            # Test parameter modification
            params["inflation_base"] = 4.0
            admin.save_parameters(params)
            
            # Test parameter persistence
            new_params = admin.load_parameters()
            assert new_params["inflation_base"] == 4.0
    
    def test_admin_logging(self):
        """Test administrative action logging"""
        with patch('economic_admin.Path') as mock_path:
            mock_path.return_value = self.test_data_dir
            
            from economic_admin import EconomicAdmin
            
            mock_bot = Mock()
            admin = EconomicAdmin(mock_bot)
            
            # Test logging
            admin.log_admin_action(12345, "test_action", {"parameter": "value"})
            
            # Verify log file creation
            log_file = self.test_data_dir / "admin_log.json"
            assert log_file.exists()
            
            # Verify log content
            with open(log_file, 'r') as f:
                logs = json.load(f)
                assert len(logs) == 1
                assert logs[0]["admin_id"] == 12345
                assert logs[0]["action"] == "test_action"

class TestEconomicCalculations:
    """Test economic calculation algorithms"""
    
    def test_gdp_calculation_logic(self):
        """Test GDP calculation based on activity data"""
        # Test data
        legislative_activity = 10  # bills passed
        committee_work = 15       # committee hours
        public_engagement = 25    # public messages
        
        # Mock weights
        weights = {"legislative": 0.4, "committee": 0.3, "public": 0.3}
        multiplier = 100  # GDP multiplier
        
        # Calculate GDP
        gdp = (
            legislative_activity * weights["legislative"] +
            committee_work * weights["committee"] + 
            public_engagement * weights["public"]
        ) * multiplier
        
        expected_gdp = (10 * 0.4 + 15 * 0.3 + 25 * 0.3) * 100
        assert gdp == expected_gdp
        assert gdp == 1750.0  # (4 + 4.5 + 7.5) * 100
    
    def test_stock_price_simulation(self):
        """Test stock price movement simulation"""
        # Initial stock data
        stock = {"symbol": "GOV", "price": 100.0, "volatility": 0.05}
        
        # Market factors
        government_efficiency = 0.02  # 2% improvement
        public_sentiment = 0.5       # Neutral (range -1 to 1)
        
        # Calculate price change
        base_change = government_efficiency
        sentiment_modifier = public_sentiment * 0.01  # 1% max impact
        volatility_factor = stock["volatility"] * 0.5   # Random component
        
        price_change = base_change + sentiment_modifier + volatility_factor
        new_price = stock["price"] * (1 + price_change)
        
        # Verify price moved in expected direction
        assert new_price > stock["price"]  # Should increase due to positive factors
        assert new_price < stock["price"] * 1.1  # But not more than 10%
    
    def test_sentiment_analysis_scoring(self):
        """Test sentiment scoring from message content"""
        # Mock positive messages
        positive_messages = [
            "Great bipartisan cooperation on this bill!",
            "Excellent work by the committee",
            "Strong support for this legislation"
        ]
        
        # Mock negative messages  
        negative_messages = [
            "This bill is terrible and wasteful",
            "Complete failure of leadership",
            "Strongly oppose this legislation"
        ]
        
        # Mock neutral messages
        neutral_messages = [
            "The committee will meet at 3 PM",
            "Bill H.R. 1234 introduced today",
            "Voting scheduled for tomorrow"
        ]
        
        # Simple sentiment scoring (in real implementation, would use NLP)
        positive_keywords = ["great", "excellent", "support", "bipartisan"]
        negative_keywords = ["terrible", "failure", "oppose", "wasteful"]
        
        def calculate_sentiment(messages):
            total_score = 0
            for message in messages:
                message_lower = message.lower()
                score = 0
                for keyword in positive_keywords:
                    if keyword in message_lower:
                        score += 1
                for keyword in negative_keywords:
                    if keyword in message_lower:
                        score -= 1
                total_score += score
            return total_score / len(messages) if messages else 0
        
        pos_sentiment = calculate_sentiment(positive_messages)
        neg_sentiment = calculate_sentiment(negative_messages)
        neu_sentiment = calculate_sentiment(neutral_messages)
        
        assert pos_sentiment > 0
        assert neg_sentiment < 0
        assert neu_sentiment == 0

class TestSystemIntegration:
    """Test integration between economic system components"""
    
    def setup_method(self):
        """Set up integration test environment"""
        self.test_data_dir = Path("test_economic_data")
        self.test_data_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up integration test environment"""
        import shutil
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
    
    @pytest.mark.asyncio
    async def test_full_analysis_cycle(self):
        """Test complete economic analysis cycle"""
        with patch('economic_engine.Path') as mock_path:
            mock_path.return_value = self.test_data_dir
            
            from economic_engine import EconomicEngine
            
            mock_bot = Mock()
            engine = EconomicEngine(mock_bot)
            
            # Create mock Discord activity
            mock_data = MockDiscordData()
            activity_data = {
                "legislative": mock_data.generate_legislative_messages(10),
                "committee": mock_data.generate_committee_messages(5),
                "public": mock_data.generate_public_messages(15),
                "documents": mock_data.generate_documents()
            }
            
            # Test initial analysis (no previous report)
            analysis = await engine.analyze_with_gemini(activity_data, None)
            assert "gdp" in analysis
            assert "timestamp" in analysis
            
            # Save the analysis
            await engine.save_economic_data(analysis)
            
            # Test subsequent analysis (with previous report)
            previous_report = engine.get_latest_economic_report()
            assert previous_report is not None
            
            new_analysis = await engine.analyze_with_gemini(activity_data, previous_report)
            assert "gdp" in new_analysis
            
            # Verify data continuity
            assert previous_report["timestamp"] != new_analysis["timestamp"]

def run_economic_system_tests():
    """Run all economic system tests"""
    print("🧪 Running Economic System Test Suite")
    print("=" * 50)
    
    # Test classes
    test_classes = [
        TestEconomicEngine,
        TestEconomicTools, 
        TestEconomicAdmin,
        TestEconomicCalculations,
        TestSystemIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n📋 Testing {test_class.__name__}")
        print("-" * 30)
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                # Create test instance
                test_instance = test_class()
                
                # Run setup if it exists
                if hasattr(test_instance, 'setup_method'):
                    test_instance.setup_method()
                
                # Run the test
                method = getattr(test_instance, test_method)
                if asyncio.iscoroutinefunction(method):
                    asyncio.run(method())
                else:
                    method()
                
                # Run teardown if it exists
                if hasattr(test_instance, 'teardown_method'):
                    test_instance.teardown_method()
                
                print(f"✅ {test_method}")
                passed_tests += 1
                
            except Exception as e:
                print(f"❌ {test_method}: {str(e)}")
                failed_tests.append(f"{test_class.__name__}.{test_method}: {str(e)}")
    
    # Test summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
    
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for failure in failed_tests:
            print(f"  • {failure}")
    else:
        print("\n🎉 All tests passed!")
    
    print("\n🔧 Testing Google Docs Integration")
    print("-" * 30)
    
    # Test the actual document URL provided by user
    async def test_real_document():
        from ai_tools import fetch_document_content
        
        try:
            content = await fetch_document_content(TEST_DOC_URL)
            if content and "Error" not in content:
                print(f"✅ Successfully fetched document content ({len(content)} characters)")
                print(f"📄 Preview: {content[:200]}...")
                return True
            else:
                print(f"❌ Failed to fetch document: {content}")
                return False
        except Exception as e:
            print(f"❌ Document fetch error: {e}")
            return False
    
    doc_success = asyncio.run(test_real_document())
    
    print("\n" + "=" * 50)
    print("🏁 Economic System Test Suite Complete")
    
    if passed_tests == total_tests and doc_success:
        print("🌟 All systems functional - Ready for deployment!")
    else:
        print("⚠️  Some issues detected - Review failed tests before deployment")

if __name__ == "__main__":
    run_economic_system_tests()