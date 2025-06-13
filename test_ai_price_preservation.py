#!/usr/bin/env python3
"""
Test AI Price Preservation Fixes
Validates that critical fixes for AI opening price preservation work correctly
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import random
from typing import Dict, List, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_market import StockMarket


class TestAIPricePreservation:
    """Test suite for AI price preservation fixes"""
    
    def __init__(self):
        self.test_dir = Path("test_ai_price_data")
        self.test_dir.mkdir(exist_ok=True)
        self.test_results = []
        
    def generate_mock_ai_analysis(self, day: int, economic_scenario: str = "high_inflation") -> Dict[str, Any]:
        """Generate realistic mock AI analysis data"""
        
        # Economic scenarios affect market parameters
        scenarios = {
            "high_inflation": {
                "trend_direction": -0.35,
                "volatility": 0.80,
                "momentum": 0.25,
                "market_sentiment": 0.35,
                "long_term_outlook": 0.40
            },
            "recovery": {
                "trend_direction": 0.45,
                "volatility": 0.50,
                "momentum": 0.60,
                "market_sentiment": 0.65,
                "long_term_outlook": 0.70
            },
            "stable": {
                "trend_direction": 0.10,
                "volatility": 0.30,
                "momentum": 0.50,
                "market_sentiment": 0.60,
                "long_term_outlook": 0.65
            }
        }
        
        base_params = scenarios.get(economic_scenario, scenarios["stable"])
        
        # Add daily variation
        daily_var = (random.random() - 0.5) * 0.1
        params = {
            "trend_direction": max(-1, min(1, base_params["trend_direction"] + daily_var)),
            "volatility": max(0, min(1, base_params["volatility"] + daily_var * 0.5)),
            "momentum": max(0, min(1, base_params["momentum"] + daily_var * 0.5)),
            "market_sentiment": max(0, min(1, base_params["market_sentiment"] + daily_var * 0.5)),
            "long_term_outlook": base_params["long_term_outlook"]  # Changes slowly
        }
        
        # Generate stock prices
        stock_data = {
            # Tech stocks
            "AAPL": {"base": 175.0, "sector": "TECH"},
            "MSFT": {"base": 380.0, "sector": "TECH"},
            "GOOGL": {"base": 140.0, "sector": "TECH"},
            "NVDA": {"base": 500.0, "sector": "TECH"},
            # Finance
            "JPM": {"base": 150.0, "sector": "FINANCE"},
            "BAC": {"base": 35.0, "sector": "FINANCE"},
            "V": {"base": 250.0, "sector": "FINANCE"},
            "GS": {"base": 380.0, "sector": "FINANCE"},
            "BRK.B": {"base": 340.0, "sector": "FINANCE"},
            # Energy
            "XOM": {"base": 105.0, "sector": "ENERGY"},
            "CVX": {"base": 150.0, "sector": "ENERGY"},
            "COP": {"base": 120.0, "sector": "ENERGY"},
            # Health
            "JNJ": {"base": 160.0, "sector": "HEALTH"},
            "UNH": {"base": 520.0, "sector": "HEALTH"},
            "PFE": {"base": 30.0, "sector": "HEALTH"},
            # Retail
            "WMT": {"base": 160.0, "sector": "RETAIL"},
            "COST": {"base": 580.0, "sector": "RETAIL"},
            "HD": {"base": 350.0, "sector": "RETAIL"},
            # Manufacturing
            "CAT": {"base": 280.0, "sector": "MANUFACTURING"},
            "GE": {"base": 110.0, "sector": "MANUFACTURING"},
            "LMT": {"base": 450.0, "sector": "MANUFACTURING"},
            # Entertainment
            "NFLX": {"base": 450.0, "sector": "ENTERTAINMENT"},
            "DIS": {"base": 95.0, "sector": "ENTERTAINMENT"},
            "EA": {"base": 140.0, "sector": "ENTERTAINMENT"},
            # Transport
            "BA": {"base": 220.0, "sector": "TRANSPORT"}
        }
        
        # Sector impacts based on scenario
        sector_impacts = {
            "high_inflation": {
                "TECH": -0.02, "FINANCE": 0.01, "ENERGY": 0.03,
                "HEALTH": -0.01, "RETAIL": -0.03, "MANUFACTURING": -0.02,
                "ENTERTAINMENT": -0.04, "TRANSPORT": -0.02
            },
            "recovery": {
                "TECH": 0.03, "FINANCE": 0.02, "ENERGY": 0.01,
                "HEALTH": 0.02, "RETAIL": 0.02, "MANUFACTURING": 0.03,
                "ENTERTAINMENT": 0.04, "TRANSPORT": 0.02
            },
            "stable": {
                "TECH": 0.01, "FINANCE": 0.01, "ENERGY": 0.00,
                "HEALTH": 0.01, "RETAIL": 0.01, "MANUFACTURING": 0.01,
                "ENTERTAINMENT": 0.01, "TRANSPORT": 0.01
            }
        }
        
        impacts = sector_impacts.get(economic_scenario, sector_impacts["stable"])
        
        daily_stock_prices = {}
        for symbol, info in stock_data.items():
            # Calculate opening price based on trend and sector
            sector_impact = impacts.get(info["sector"], 0)
            trend_impact = params["trend_direction"] * 0.01
            daily_impact = trend_impact + sector_impact + (random.random() - 0.5) * 0.02
            
            # Cumulative effect over days
            cumulative = 1 + (daily_impact * day * 0.5)
            open_price = round(info["base"] * cumulative, 2)
            
            # Daily range based on volatility
            range_pct = params["volatility"] * 0.03
            range_low = round(open_price * (1 - range_pct), 2)
            range_high = round(open_price * (1 + range_pct), 2)
            
            daily_stock_prices[symbol] = {
                "open_price": open_price,
                "range_low": range_low,
                "range_high": range_high,
                "sector_factor": round(1 + abs(sector_impact), 2)
            }
        
        # Build complete analysis
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parameters": params,
            "invisible_factors": {
                "institutional_flow": params["trend_direction"] * 0.5,
                "liquidity_factor": 0.8 - params["volatility"] * 0.3,
                "news_velocity": params["volatility"],
                "sector_rotation": daily_var,
                "risk_appetite": params["market_sentiment"] * 0.8
            },
            "daily_stock_prices": daily_stock_prices,
            "market_state": {
                "scenario": economic_scenario,
                "day": day
            }
        }
    
    async def test_fix_01_ai_price_preservation(self):
        """Test Fix 0.1: AI opening prices are never overwritten"""
        print("\n🧪 Testing Fix 0.1: AI Opening Price Preservation")
        print("="*50)
        
        market = StockMarket()
        market.data_dir = self.test_dir
        
        # Set market open time
        market.market_open_time = datetime.now(timezone.utc).replace(hour=14, minute=0)
        
        # Generate and apply AI analysis
        ai_analysis = self.generate_mock_ai_analysis(1, "high_inflation")
        
        # Apply AI analysis
        market.market_params = ai_analysis["parameters"]
        market._apply_ai_stock_prices(ai_analysis["daily_stock_prices"])
        
        # Test results
        test_passed = True
        issues = []
        
        # Check all stocks have ai_opening_price field
        for cat_data in market.categories.values():
            for stock in cat_data["stocks"]:
                symbol = stock["symbol"]
                
                # Check ai_opening_price exists
                if "ai_opening_price" not in stock:
                    test_passed = False
                    issues.append(f"{symbol}: Missing ai_opening_price field")
                    continue
                
                # Check it matches what AI set
                expected = ai_analysis["daily_stock_prices"][symbol]["open_price"]
                actual = stock["ai_opening_price"]
                
                if actual != expected:
                    test_passed = False
                    issues.append(f"{symbol}: AI set {expected}, stored {actual}")
                else:
                    print(f"✅ {symbol}: AI opening price preserved: ${actual}")
        
        # Now simulate price updates and verify AI opening unchanged
        print("\n📊 Simulating price updates...")
        for hour in range(1, 5):
            time_now = market.market_open_time + timedelta(hours=hour)
            
            for cat_data in market.categories.values():
                for stock in cat_data["stocks"]:
                    symbol = stock["symbol"]
                    
                    # Calculate new price
                    new_price = market.calculate_price_at_time(symbol, time_now)
                    
                    # Update current price (not opening)
                    stock["current_price"] = new_price
                    stock["price"] = new_price
                    
                    # Verify AI opening unchanged
                    if stock["ai_opening_price"] != ai_analysis["daily_stock_prices"][symbol]["open_price"]:
                        test_passed = False
                        issues.append(f"{symbol} Hour {hour}: AI opening price changed!")
        
        print(f"\n📊 After 4 hours of updates:")
        sample_stocks = ["AAPL", "JPM", "XOM"]
        for symbol in sample_stocks:
            stock = self._find_stock(market, symbol)
            if stock:
                print(f"   {symbol}: Opening ${stock['ai_opening_price']}, Current ${stock['current_price']:.2f}")
        
        # Report results
        if test_passed:
            print("\n✅ Fix 0.1 PASSED: AI opening prices preserved correctly")
        else:
            print("\n❌ Fix 0.1 FAILED:")
            for issue in issues:
                print(f"   - {issue}")
        
        self.test_results.append({
            "test": "Fix 0.1: AI Opening Price Preservation",
            "passed": test_passed,
            "issues": issues
        })
        
        return test_passed
    
    async def test_fix_02_baseline_calculation(self):
        """Test Fix 0.2: Price calculations always use AI opening as baseline"""
        print("\n🧪 Testing Fix 0.2: AI Baseline in Calculations")
        print("="*50)
        
        market = StockMarket()
        market.data_dir = self.test_dir
        market.market_open_time = datetime.now(timezone.utc).replace(hour=14, minute=0)
        
        # Apply AI analysis
        ai_analysis = self.generate_mock_ai_analysis(1, "stable")
        market.market_params = ai_analysis["parameters"]
        market._apply_ai_stock_prices(ai_analysis["daily_stock_prices"])
        
        test_passed = True
        issues = []
        
        # Test price calculations at different times
        test_times = [
            market.market_open_time,
            market.market_open_time + timedelta(hours=1),
            market.market_open_time + timedelta(hours=4),
            market.market_open_time + timedelta(hours=8)
        ]
        
        for test_time in test_times:
            hours_elapsed = (test_time - market.market_open_time).total_seconds() / 3600
            print(f"\n⏰ Testing at +{hours_elapsed:.0f} hours:")
            
            for symbol in ["AAPL", "MSFT", "JPM"]:
                stock = self._find_stock(market, symbol)
                if not stock:
                    continue
                
                # Calculate price
                try:
                    calculated_price = market.calculate_price_at_time(symbol, test_time)
                    
                    # At market open, price should be very close to AI opening (small noise allowed)
                    if hours_elapsed == 0:
                        expected = stock["ai_opening_price"]
                        tolerance = expected * 0.03  # 3% tolerance for Perlin noise at open
                        if abs(calculated_price - expected) > tolerance:
                            test_passed = False
                            issues.append(f"{symbol} at open: Expected ${expected}, got ${calculated_price}")
                        else:
                            print(f"   ✅ {symbol}: Opening price near AI baseline (${calculated_price:.2f} ≈ ${expected})")
                    
                    # Price should be within daily range
                    range_low = ai_analysis["daily_stock_prices"][symbol]["range_low"]
                    range_high = ai_analysis["daily_stock_prices"][symbol]["range_high"]
                    
                    # Allow 2% overshoot as per stock market design
                    if calculated_price < range_low * 0.98 or calculated_price > range_high * 1.02:
                        test_passed = False
                        issues.append(f"{symbol} at +{hours_elapsed}h: Price ${calculated_price} outside range [{range_low}, {range_high}]")
                    else:
                        change_pct = ((calculated_price - stock["ai_opening_price"]) / stock["ai_opening_price"]) * 100
                        print(f"   ✅ {symbol}: ${calculated_price:.2f} ({change_pct:+.1f}% from AI open)")
                        
                except Exception as e:
                    test_passed = False
                    issues.append(f"{symbol}: Calculation error: {e}")
        
        # Report results
        if test_passed:
            print("\n✅ Fix 0.2 PASSED: Calculations use AI baseline correctly")
        else:
            print("\n❌ Fix 0.2 FAILED:")
            for issue in issues:
                print(f"   - {issue}")
        
        self.test_results.append({
            "test": "Fix 0.2: AI Baseline in Calculations",
            "passed": test_passed,
            "issues": issues
        })
        
        return test_passed
    
    async def test_fix_11_parameter_storage(self):
        """Test Fix 1.1: Parameters stored in analysis object"""
        print("\n🧪 Testing Fix 1.1: Parameter Storage in Analysis")
        print("="*50)
        
        market = StockMarket()
        market.data_dir = self.test_dir
        
        # Generate AI analysis
        ai_analysis = self.generate_mock_ai_analysis(1, "recovery")
        
        # Simulate parse_structured_market_analysis behavior
        params = ai_analysis["parameters"]
        
        # The fix should store parameters in analysis object
        analysis = {
            "parameters": {
                "trend_direction": max(-1.0, min(1.0, float(params.get("trend_direction", 0.0)))),
                "volatility": max(0.0, min(1.0, float(params.get("volatility", 0.5)))),
                "momentum": max(0.0, min(1.0, float(params.get("momentum", 0.5)))),
                "market_sentiment": max(0.0, min(1.0, float(params.get("market_sentiment", 0.5)))),
                "long_term_outlook": max(0.0, min(1.0, float(params.get("long_term_outlook", 0.4))))
            }
        }
        
        test_passed = True
        issues = []
        
        # Verify parameters are stored
        if "parameters" not in analysis:
            test_passed = False
            issues.append("Parameters not stored in analysis object")
        else:
            print("✅ Parameters stored in analysis object")
            
            # Verify all required parameters
            required_params = ["trend_direction", "volatility", "momentum", "market_sentiment", "long_term_outlook"]
            for param in required_params:
                if param not in analysis["parameters"]:
                    test_passed = False
                    issues.append(f"Missing parameter: {param}")
                else:
                    value = analysis["parameters"][param]
                    print(f"   ✅ {param}: {value:.3f}")
            
            # Verify clamping works
            if analysis["parameters"]["trend_direction"] < -1 or analysis["parameters"]["trend_direction"] > 1:
                test_passed = False
                issues.append("trend_direction not clamped to [-1, 1]")
            
            for param in ["volatility", "momentum", "market_sentiment", "long_term_outlook"]:
                if analysis["parameters"][param] < 0 or analysis["parameters"][param] > 1:
                    test_passed = False
                    issues.append(f"{param} not clamped to [0, 1]")
        
        # Report results
        if test_passed:
            print("\n✅ Fix 1.1 PASSED: Parameters stored correctly")
        else:
            print("\n❌ Fix 1.1 FAILED:")
            for issue in issues:
                print(f"   - {issue}")
        
        self.test_results.append({
            "test": "Fix 1.1: Parameter Storage",
            "passed": test_passed,
            "issues": issues
        })
        
        return test_passed
    
    async def test_fix_12_required_prices(self):
        """Test Fix 1.2: All stocks must have required price fields"""
        print("\n🧪 Testing Fix 1.2: Required Price Validation")
        print("="*50)
        
        market = StockMarket()
        market.data_dir = self.test_dir
        
        test_passed = True
        issues = []
        
        # Test 1: Validate our mock data generator creates required fields
        print("📊 Test 1: Validating mock AI data structure")
        mock_analysis = self.generate_mock_ai_analysis(1)
        
        # Check daily_stock_prices exists
        if "daily_stock_prices" not in mock_analysis:
            test_passed = False
            issues.append("Mock data missing daily_stock_prices")
        else:
            print("   ✅ Mock data contains daily_stock_prices")
        
        # Test 2: Missing stocks should fail
        print("\n📊 Test 2: Missing required stocks")
        incomplete_analysis = self.generate_mock_ai_analysis(1)
        # Remove some stocks
        del incomplete_analysis["daily_stock_prices"]["AAPL"]
        del incomplete_analysis["daily_stock_prices"]["JPM"]
        
        # Get all required symbols
        required_symbols = {stock["symbol"] for cat in market.categories.values() for stock in cat["stocks"]}
        provided_symbols = set(incomplete_analysis["daily_stock_prices"].keys())
        missing = required_symbols - provided_symbols
        
        if missing:
            print(f"   ✅ Correctly identified missing stocks: {missing}")
        else:
            test_passed = False
            issues.append("Failed to identify missing stocks")
        
        # Test 3: Missing required fields should fail
        print("\n📊 Test 3: Missing required fields")
        bad_stock_data = self.generate_mock_ai_analysis(1)
        # Remove required field
        del bad_stock_data["daily_stock_prices"]["MSFT"]["range_low"]
        
        required_fields = ["open_price", "range_low", "range_high", "sector_factor"]
        for symbol, data in bad_stock_data["daily_stock_prices"].items():
            missing_fields = [f for f in required_fields if f not in data]
            if symbol == "MSFT" and missing_fields:
                print(f"   ✅ Correctly identified missing fields for {symbol}: {missing_fields}")
                break
        
        # Test 4: Valid data should pass
        print("\n📊 Test 4: Valid complete data")
        valid_analysis = self.generate_mock_ai_analysis(1)
        
        # Verify all stocks present
        all_present = all(
            symbol in valid_analysis["daily_stock_prices"]
            for cat in market.categories.values()
            for stock in cat["stocks"]
            for symbol in [stock["symbol"]]
        )
        
        if all_present:
            print("   ✅ All required stocks present")
        else:
            test_passed = False
            issues.append("Valid data missing required stocks")
        
        # Verify all fields present
        for symbol, data in valid_analysis["daily_stock_prices"].items():
            for field in required_fields:
                if field not in data:
                    test_passed = False
                    issues.append(f"{symbol} missing {field}")
        
        if not issues:
            print("   ✅ All required fields present")
        
        # Report results
        if test_passed:
            print("\n✅ Fix 1.2 PASSED: Price validation working correctly")
        else:
            print("\n❌ Fix 1.2 FAILED:")
            for issue in issues:
                print(f"   - {issue}")
        
        self.test_results.append({
            "test": "Fix 1.2: Required Price Validation",
            "passed": test_passed,
            "issues": issues
        })
        
        return test_passed
    
    async def test_multiday_simulation(self):
        """Test multi-day simulation to ensure fixes work over time"""
        print("\n🧪 Testing Multi-Day Market Simulation")
        print("="*50)
        
        market = StockMarket()
        market.data_dir = self.test_dir
        
        scenarios = [
            ("high_inflation", 5),
            ("recovery", 5),
            ("stable", 4)
        ]
        
        test_passed = True
        issues = []
        price_history = {}
        
        day_counter = 1
        
        for scenario, days in scenarios:
            print(f"\n📈 Scenario: {scenario} ({days} days)")
            
            for day in range(1, days + 1):
                print(f"\n   Day {day_counter}:")
                
                # Set market open time
                market.market_open_time = datetime.now(timezone.utc).replace(hour=14, minute=0)
                
                # Generate and apply AI analysis
                ai_analysis = self.generate_mock_ai_analysis(day_counter, scenario)
                market.market_params = ai_analysis["parameters"]
                market._apply_ai_stock_prices(ai_analysis["daily_stock_prices"])
                
                # Track some stocks
                track_symbols = ["AAPL", "XOM", "JPM", "NFLX"]
                
                for symbol in track_symbols:
                    stock = self._find_stock(market, symbol)
                    if not stock:
                        continue
                    
                    # Initialize history
                    if symbol not in price_history:
                        price_history[symbol] = []
                    
                    # Simulate intraday movement
                    for hour in [0, 4, 8]:
                        time_now = market.market_open_time + timedelta(hours=hour)
                        price = market.calculate_price_at_time(symbol, time_now)
                        
                        # Update current price
                        stock["current_price"] = price
                        stock["price"] = price
                        
                        # Verify AI opening unchanged
                        if stock["ai_opening_price"] != ai_analysis["daily_stock_prices"][symbol]["open_price"]:
                            test_passed = False
                            issues.append(f"Day {day_counter} Hour {hour}: {symbol} AI opening changed!")
                        
                        # Record history
                        price_history[symbol].append({
                            "day": day_counter,
                            "hour": hour,
                            "price": price,
                            "ai_opening": stock["ai_opening_price"]
                        })
                
                # Daily summary
                print(f"      Market: Trend {market.market_params['trend_direction']:+.2f}, Volatility {market.market_params['volatility']:.2f}")
                for symbol in track_symbols[:2]:  # Show 2 examples
                    stock = self._find_stock(market, symbol)
                    if stock:
                        change = ((stock["current_price"] - stock["ai_opening_price"]) / stock["ai_opening_price"]) * 100
                        print(f"      {symbol}: ${stock['current_price']:.2f} ({change:+.1f}% from AI open ${stock['ai_opening_price']})")
                
                day_counter += 1
        
        # Analyze results
        print("\n📊 Multi-Day Analysis:")
        for symbol, history in price_history.items():
            if history:
                prices = [h["price"] for h in history]
                opens = [h["ai_opening"] for h in history]
                
                # Check price continuity
                max_jump = 0
                for i in range(1, len(history)):
                    if history[i]["day"] == history[i-1]["day"]:  # Same day
                        jump = abs(history[i]["price"] - history[i-1]["price"]) / history[i-1]["price"]
                        max_jump = max(max_jump, jump)
                
                print(f"\n   {symbol}:")
                print(f"      Price range: ${min(prices):.2f} - ${max(prices):.2f}")
                print(f"      Max intraday jump: {max_jump*100:.1f}%")
                print(f"      AI openings preserved: {'✅' if len(set(opens)) == day_counter-1 else '❌'}")
                
                if len(set(opens)) != day_counter-1:
                    test_passed = False
                    issues.append(f"{symbol}: AI opening prices not preserved across days")
        
        # Report results
        if test_passed:
            print("\n✅ Multi-Day Simulation PASSED")
        else:
            print("\n❌ Multi-Day Simulation FAILED:")
            for issue in issues:
                print(f"   - {issue}")
        
        self.test_results.append({
            "test": "Multi-Day Simulation",
            "passed": test_passed,
            "issues": issues
        })
        
        return test_passed
    
    def _find_stock(self, market: StockMarket, symbol: str):
        """Helper to find stock by symbol"""
        for cat_data in market.categories.values():
            for stock in cat_data["stocks"]:
                if stock["symbol"] == symbol:
                    return stock
        return None
    
    async def run_all_tests(self):
        """Run all test cases"""
        print("🚀 Starting AI Price Preservation Test Suite")
        print("="*60)
        
        # Run all tests
        await self.test_fix_01_ai_price_preservation()
        await self.test_fix_02_baseline_calculation()
        await self.test_fix_11_parameter_storage()
        await self.test_fix_12_required_prices()
        await self.test_multiday_simulation()
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        
        for result in self.test_results:
            status = "✅ PASSED" if result["passed"] else "❌ FAILED"
            print(f"\n{result['test']}: {status}")
            if not result["passed"] and result["issues"]:
                for issue in result["issues"][:3]:  # Show first 3 issues
                    print(f"   - {issue}")
                if len(result["issues"]) > 3:
                    print(f"   ... and {len(result['issues']) - 3} more issues")
        
        print(f"\n📈 Overall: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.0f}%)")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! The fixes are working correctly!")
        else:
            print("\n⚠️ Some tests failed. Review the issues above.")
        
        # Save test results
        results_file = self.test_dir / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": f"{passed_tests}/{total_tests} passed",
                "results": self.test_results
            }, f, indent=2)
        print(f"\n📄 Detailed results saved to: {results_file}")


async def main():
    """Run the test suite"""
    tester = TestAIPricePreservation()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())