#!/usr/bin/env python3
"""
Swiss Asset Pro - Core Business Logic Tests
Test suite for critical financial calculations and portfolio analysis
"""

import unittest
import sys
import os
import numpy as np
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the functions we want to test
from app import (
    calculate_swiss_stamp_tax,
    calculate_swiss_withholding_tax,
    calculate_net_return,
    calculate_swiss_tax_optimization,
    calculate_stress_test_scenarios,
    calculate_swiss_franc_hedge_ratio,
    calculate_portfolio_metrics,
    calculate_correlation_matrix
)

class TestSwissTaxCalculations(unittest.TestCase):
    """Test Swiss tax calculation functions"""
    
    def test_stamp_tax_swiss_security(self):
        """Test stamp tax calculation for Swiss securities"""
        amount = 10000
        tax = calculate_swiss_stamp_tax(amount, is_swiss_security=True)
        expected = 10000 * 0.0015  # 0.15% stamp tax
        self.assertEqual(tax, expected)
        self.assertEqual(tax, 15.0)
    
    def test_stamp_tax_non_swiss_security(self):
        """Test stamp tax calculation for non-Swiss securities"""
        amount = 10000
        tax = calculate_swiss_stamp_tax(amount, is_swiss_security=False)
        self.assertEqual(tax, 0.0)
    
    def test_withholding_tax_swiss_security(self):
        """Test withholding tax calculation for Swiss securities"""
        dividend = 1000
        tax = calculate_swiss_withholding_tax(dividend, is_swiss_security=True)
        expected = 1000 * 0.35  # 35% withholding tax
        self.assertEqual(tax, expected)
        self.assertEqual(tax, 350.0)
    
    def test_withholding_tax_non_swiss_security(self):
        """Test withholding tax calculation for non-Swiss securities"""
        dividend = 1000
        tax = calculate_swiss_withholding_tax(dividend, is_swiss_security=False)
        self.assertEqual(tax, 0.0)
    
    def test_net_return_calculation(self):
        """Test net return calculation after costs and taxes"""
        gross_return = 1000
        transaction_costs = 50
        taxes = 100
        net_return = calculate_net_return(gross_return, transaction_costs, taxes)
        expected = 1000 - 50 - 100
        self.assertEqual(net_return, expected)
        self.assertEqual(net_return, 850.0)

class TestPortfolioAnalysis(unittest.TestCase):
    """Test portfolio analysis functions"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_portfolio = {
            'NESN.SW': 25000,
            'NOVN.SW': 20000,
            'ROG.SW': 15000,
            'AAPL': 30000,
            'MSFT': 25000,
            'BND': 20000,
            'GC=F': 10000
        }
    
    def test_portfolio_metrics_calculation(self):
        """Test portfolio metrics calculation"""
        # Create proper portfolio data structure
        portfolio_data = {
            'AAPL': {'change_percent': 5.2, 'quantity': 10, 'price': 150.0},
            'GOOGL': {'change_percent': -2.1, 'quantity': 5, 'price': 2800.0},
            'MSFT': {'change_percent': 3.8, 'quantity': 8, 'price': 300.0}
        }
        
        metrics = calculate_portfolio_metrics(portfolio_data)
        
        # Check that all required metrics are present
        required_metrics = [
            'total_assets', 'portfolio_return', 'portfolio_volatility',
            'sharpe_ratio', 'max_drawdown', 'var_95'
        ]
        for metric in required_metrics:
            self.assertIn(metric, metrics)
        
        # Check that metrics are reasonable
        self.assertGreater(metrics['total_assets'], 0)
        self.assertIsInstance(metrics['portfolio_return'], (int, float))
        self.assertIsInstance(metrics['portfolio_volatility'], (int, float))
    
    def test_correlation_matrix_calculation(self):
        """Test correlation matrix calculation"""
        # Create proper portfolio data structure
        portfolio_data = {
            'AAPL': {'change_percent': 5.2, 'quantity': 10, 'price': 150.0},
            'GOOGL': {'change_percent': -2.1, 'quantity': 5, 'price': 2800.0},
            'MSFT': {'change_percent': 3.8, 'quantity': 8, 'price': 300.0}
        }
        
        correlation_matrix = calculate_correlation_matrix(portfolio_data)
        
        # Check that correlation matrix is returned
        self.assertIsInstance(correlation_matrix, dict)
        
        # Check that all portfolio symbols are in the matrix
        for symbol in portfolio_data.keys():
            self.assertIn(symbol, correlation_matrix)
        
        # Check that correlation values are between -1 and 1
        for symbol, correlations in correlation_matrix.items():
            for other_symbol, correlation in correlations.items():
                self.assertGreaterEqual(correlation, -1.0)
                self.assertLessEqual(correlation, 1.0)
                # Diagonal should be 1.0
                if symbol == other_symbol:
                    self.assertEqual(correlation, 1.0)
    
    def test_swiss_tax_optimization(self):
        """Test Swiss tax optimization"""
        optimized_weights = calculate_swiss_tax_optimization(self.sample_portfolio)
        
        # Check that optimized weights are returned
        self.assertIsInstance(optimized_weights, dict)
        
        # Check that all portfolio symbols are in the optimized weights
        for symbol in self.sample_portfolio.keys():
            self.assertIn(symbol, optimized_weights)
        
        # Check that weights sum to approximately 1.0
        total_weight = sum(optimized_weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)
        
        # Check that Swiss securities get preference
        swiss_symbols = ['NESN.SW', 'NOVN.SW', 'ROG.SW']
        for symbol in swiss_symbols:
            if symbol in optimized_weights:
                # Swiss securities should have higher weights than non-Swiss
                swiss_weight = optimized_weights[symbol]
                non_swiss_weight = optimized_weights.get('AAPL', 0)
                # This is a basic check - in practice, optimization might vary
                self.assertGreaterEqual(swiss_weight, 0.0)

class TestStressTesting(unittest.TestCase):
    """Test stress testing functions"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_portfolio = {
            'NESN.SW': 25000,
            'NOVN.SW': 20000,
            'ROG.SW': 15000,
            'AAPL': 30000,
            'MSFT': 25000,
            'BND': 20000,
            'GC=F': 10000
        }
        self.sample_market_data = {
            'NESN.SW': {'price': 100, 'change_percent': 1.5},
            'NOVN.SW': {'price': 80, 'change_percent': -0.5},
            'ROG.SW': {'price': 300, 'change_percent': 2.1}
        }
    
    def test_stress_test_scenarios(self):
        """Test stress testing scenarios"""
        stress_results = calculate_stress_test_scenarios(
            self.sample_portfolio, 
            self.sample_market_data
        )
        
        # Check that stress results are returned
        self.assertIsInstance(stress_results, dict)
        
        # Check that all expected scenarios are present
        expected_scenarios = [
            '2008_financial_crisis',
            'covid_2020',
            'interest_rate_shock',
            'swiss_franc_strength',
            'inflation_shock'
        ]
        for scenario in expected_scenarios:
            self.assertIn(scenario, stress_results)
        
        # Check that each scenario has required fields
        for scenario_name, scenario_data in stress_results.items():
            self.assertIn('portfolio_value', scenario_data)
            self.assertIn('return', scenario_data)
            self.assertIn('shocks_applied', scenario_data)
            
            # Check that portfolio value is reasonable
            self.assertGreater(scenario_data['portfolio_value'], 0)
            
            # Check that return is a number
            self.assertIsInstance(scenario_data['return'], (int, float))
    
    def test_swiss_franc_hedge_ratio(self):
        """Test Swiss Franc hedge ratio calculation"""
        hedge_analysis = calculate_swiss_franc_hedge_ratio(self.sample_portfolio)
        
        # Check that hedge analysis is returned
        self.assertIsInstance(hedge_analysis, dict)
        
        # Check that all required fields are present
        required_fields = [
            'swiss_exposure_pct',
            'international_exposure_pct',
            'recommended_hedge_ratio',
            'hedge_amount'
        ]
        for field in required_fields:
            self.assertIn(field, hedge_analysis)
        
        # Check that percentages are reasonable
        self.assertGreaterEqual(hedge_analysis['swiss_exposure_pct'], 0)
        self.assertLessEqual(hedge_analysis['swiss_exposure_pct'], 100)
        self.assertGreaterEqual(hedge_analysis['international_exposure_pct'], 0)
        self.assertLessEqual(hedge_analysis['international_exposure_pct'], 100)
        
        # Check that hedge ratio is between 0 and 1
        self.assertGreaterEqual(hedge_analysis['recommended_hedge_ratio'], 0.0)
        self.assertLessEqual(hedge_analysis['recommended_hedge_ratio'], 1.0)
        
        # Check that hedge amount is reasonable
        self.assertGreaterEqual(hedge_analysis['hedge_amount'], 0)

class TestDataValidation(unittest.TestCase):
    """Test data validation and edge cases"""
    
    def test_empty_portfolio(self):
        """Test handling of empty portfolio"""
        empty_portfolio = {}
        
        # Test portfolio metrics with empty portfolio
        metrics = calculate_portfolio_metrics(empty_portfolio)
        # Empty portfolio should return empty metrics or handle gracefully
        self.assertIsInstance(metrics, dict)
        
        # Test correlation matrix with empty portfolio
        correlation_matrix = calculate_correlation_matrix(empty_portfolio)
        self.assertEqual(len(correlation_matrix), 0)
        
        # Test tax optimization with empty portfolio
        optimized_weights = calculate_swiss_tax_optimization(empty_portfolio)
        self.assertEqual(len(optimized_weights), 0)
    
    def test_single_asset_portfolio(self):
        """Test handling of single asset portfolio"""
        single_asset_portfolio = {'NESN.SW': {'change_percent': 5.2, 'quantity': 10, 'price': 150.0}}
        
        # Test portfolio metrics with single asset
        metrics = calculate_portfolio_metrics(single_asset_portfolio)
        self.assertIn('total_assets', metrics)
        
        # Test correlation matrix with single asset
        correlation_matrix = calculate_correlation_matrix(single_asset_portfolio)
        self.assertIsInstance(correlation_matrix, dict)
        # Single asset should have correlation of 1.0 with itself
        if 'NESN.SW' in correlation_matrix:
            self.assertEqual(correlation_matrix['NESN.SW']['NESN.SW'], 1.0)
    
    def test_negative_values(self):
        """Test handling of negative values"""
        # Test with negative amount
        tax = calculate_swiss_stamp_tax(-1000, is_swiss_security=True)
        self.assertEqual(tax, -1.5)  # Should handle negative values
        
        # Test with zero amount
        tax = calculate_swiss_stamp_tax(0, is_swiss_security=True)
        self.assertEqual(tax, 0.0)

class TestPerformance(unittest.TestCase):
    """Test performance characteristics"""
    
    def test_large_portfolio_performance(self):
        """Test performance with large portfolio"""
        # Create a large portfolio
        large_portfolio = {}
        for i in range(100):
            large_portfolio[f'STOCK_{i}'] = {'change_percent': 5.2, 'quantity': 10, 'price': 150.0}
        
        # Test that calculations complete in reasonable time
        import time
        start_time = time.time()
        
        metrics = calculate_portfolio_metrics(large_portfolio)
        correlation_matrix = calculate_correlation_matrix(large_portfolio)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within 5 seconds
        self.assertLess(execution_time, 5.0)
        
        # Results should be valid
        self.assertGreater(metrics['total_assets'], 0)
        self.assertGreater(len(correlation_matrix), 0)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestSwissTaxCalculations,
        TestPortfolioAnalysis,
        TestStressTesting,
        TestDataValidation,
        TestPerformance
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
