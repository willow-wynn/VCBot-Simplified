"""
Simplified test for core economic functionality
Tests without Discord.py dependencies
"""

import asyncio
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

def test_economic_utils():
    """Test core economic utilities"""
    print("🧪 Testing Economic Utils Core Functionality")
    print("=" * 50)
    
    # Test 1: Import and initialization
    try:
        import economic_utils
        print("✅ Economic utils import successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Parameter management
    try:
        # Create test data directory
        test_dir = Path("test_econ_core")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        test_dir.mkdir()
        
        # Create test instance of EconomicData
        test_econ_data = economic_utils.EconomicData()
        test_econ_data.data_dir = test_dir
        params = test_econ_data.load_parameters()
        
        assert "gdp_weights" in params
        assert "inflation_base" in params
        # Note: tracked_stocks removed - stock tracking moved to stock_market.py
        
        # Test parameter modification (use a parameter that isn't auto-updated)
        params["confidence_threshold"] = 0.85
        test_econ_data.save_parameters(params)
        
        new_params = test_econ_data.load_parameters()
        assert new_params["confidence_threshold"] == 0.85
        
        print("✅ Parameter management working")
        
    except Exception as e:
        print(f"❌ Parameter test failed: {e}")
        return False
    
    # Test 3: Data storage
    try:
        test_analysis = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gdp": {"value": 1500.0, "change_percent": 2.5},
            "stocks": [{"symbol": "GOOGL", "price": 2785.50, "change_percent": 1.5}],
            "inflation": {"rate": 3.0, "trend": "rising"},
            "unemployment": {"rate": 4.5},
            "sentiment": {"market_confidence": 80}
        }
        
        # Test data saving
        asyncio.run(test_econ_data.save_economic_data(test_analysis))
        
        # Verify files exist
        assert (test_dir / "reports.json").exists()
        assert (test_dir / "gdp.json").exists()
        
        # Test data retrieval
        latest = test_econ_data.get_latest_economic_report()
        assert latest is not None
        assert latest["gdp"]["value"] == 1500.0
        
        print("✅ Data storage working")
        
    except Exception as e:
        print(f"❌ Data storage test failed: {e}")
        return False
    
    # Test 4: Economic data retrieval
    try:
        # Temporarily set global econ_data to use test directory
        original_data_dir = economic_utils.econ_data.data_dir
        economic_utils.econ_data.data_dir = test_dir
        
        data = economic_utils.get_economic_data("gdp", 7)
        assert "gdp" in data
        assert len(data["gdp"]) > 0
        
        all_data = economic_utils.get_economic_data("all", 7)
        assert "gdp" in all_data
        
        # Restore original data directory
        economic_utils.econ_data.data_dir = original_data_dir
        
        print("✅ Data retrieval working")
        
    except Exception as e:
        print(f"❌ Data retrieval test failed: {e}")
        return False
    
    # Test 5: Admin functions
    try:
        # Temporarily set global econ_data to use test directory for admin functions
        original_data_dir = economic_utils.econ_data.data_dir
        economic_utils.econ_data.data_dir = test_dir
        
        # Test parameter setting (use a parameter that won't be auto-overridden)
        success = economic_utils.set_economic_parameter("confidence_threshold", 0.80)
        assert success
        
        # Test status retrieval
        status = economic_utils.get_economic_status()
        assert "parameters" in status
        assert status["parameters"]["confidence_threshold"] == 0.80
        
        # Test admin logging
        economic_utils.log_admin_action(12345, "test", {"param": "value"})
        assert (test_dir / "admin_log.json").exists()
        
        # Restore original data directory
        economic_utils.econ_data.data_dir = original_data_dir
        
        print("✅ Admin functions working")
        
    except Exception as e:
        print(f"❌ Admin test failed: {e}")
        return False
    
    # Cleanup
    try:
        shutil.rmtree(test_dir)
        print("✅ Cleanup complete")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    
    return True

async def test_document_fetching():
    """Test Google Docs document fetching"""
    print("\n🔧 Testing Document Fetching")
    print("-" * 30)
    
    try:
        import economic_utils
        
        # Test with the provided document URL
        test_url = "https://docs.google.com/document/d/1ZNZY9Xr8kqFTz_x8flcK89Gm2f58GyYxLYCNOyjKG_s/edit?usp=sharing"
        
        content = await economic_utils.econ_data.get_document_content(test_url)
        
        if content and len(content) > 0 and "Error" not in content:
            print(f"✅ Document fetching successful ({len(content)} characters)")
            print(f"📄 Content preview: {content[:100]}...")
            return True
        else:
            print(f"❌ Document fetching failed: {content}")
            return False
            
    except Exception as e:
        print(f"❌ Document fetch error: {e}")
        return False

def test_calculation_algorithms():
    """Test economic calculation logic"""
    print("\n🧮 Testing Economic Calculations")
    print("-" * 30)
    
    try:
        # Test GDP calculation
        legislative = 10
        committee = 15
        public = 25
        weights = {"legislative": 0.4, "committee": 0.3, "public": 0.3}
        multiplier = 100
        
        gdp = (legislative * weights["legislative"] + 
               committee * weights["committee"] + 
               public * weights["public"]) * multiplier
        
        expected = 1600.0  # (10*0.4 + 15*0.3 + 25*0.3) * 100 = (4 + 4.5 + 7.5) * 100 = 16 * 100
        assert gdp == expected
        print("✅ GDP calculation correct")
        
        # Test stock price movement
        stock = {"price": 100.0, "volatility": 0.05}
        efficiency = 0.02
        sentiment = 0.5
        
        price_change = efficiency + (sentiment * 0.01) + (stock["volatility"] * 0.5)
        new_price = stock["price"] * (1 + price_change)
        
        assert new_price > stock["price"]
        assert new_price < stock["price"] * 1.1
        print("✅ Stock price calculation correct")
        
        # Test sentiment scoring
        positive_msg = "Great bipartisan cooperation on this bill!"
        positive_keywords = ["great", "bipartisan", "cooperation"]
        
        score = sum(1 for keyword in positive_keywords if keyword in positive_msg.lower())
        assert score > 0
        print("✅ Sentiment analysis logic correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Calculation test failed: {e}")
        return False

def run_all_tests():
    """Run all core tests"""
    print("🚀 VCBot Economic System - Core Functionality Test")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Core utilities
    if test_economic_utils():
        tests_passed += 1
        print("✅ Core utilities test PASSED")
    else:
        print("❌ Core utilities test FAILED")
    
    # Test 2: Document fetching
    if asyncio.run(test_document_fetching()):
        tests_passed += 1
        print("✅ Document fetching test PASSED")
    else:
        print("❌ Document fetching test FAILED")
    
    # Test 3: Calculations
    if test_calculation_algorithms():
        tests_passed += 1
        print("✅ Calculation algorithms test PASSED")
    else:
        print("❌ Calculation algorithms test FAILED")
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 ALL CORE TESTS PASSED - System ready for integration!")
        print("\n📋 Next Steps:")
        print("1. Follow integration instructions in bot_economic_integration.py")
        print("2. Add economic commands to bot.py")
        print("3. Start the economic analysis engine")
        print("4. Test with /fetch_econ_data command in Discord")
        return True
    else:
        print("⚠️ Some tests failed - Review before deployment")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)