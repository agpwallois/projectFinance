import unittest
from unittest.mock import Mock, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, date

from financial_model.financial_model_sections.times import Times, get_quarters, calc_years_from_base_dates


class TestTimes(unittest.TestCase):
    """Test cases for the Times class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_instance = Mock()
        
        # Create realistic test data: monthly during construction, then semi-annual during operations
        # Construction: Jan-Dec 2023 (12 monthly periods)
        # Operations: 2024-2025 (4 semi-annual periods)
        construction_dates = [
            datetime(2023, 1, 31), datetime(2023, 2, 28), datetime(2023, 3, 31),
            datetime(2023, 4, 30), datetime(2023, 5, 31), datetime(2023, 6, 30),
            datetime(2023, 7, 31), datetime(2023, 8, 31), datetime(2023, 9, 30),
            datetime(2023, 10, 31), datetime(2023, 11, 30), datetime(2023, 12, 31)
        ]
        operations_dates = [
            datetime(2024, 6, 30),   # H1 2024
            datetime(2024, 12, 31),  # H2 2024
            datetime(2025, 6, 30),   # H1 2025
            datetime(2025, 12, 31),  # H2 2025
        ]
        
        all_dates = construction_dates + operations_dates
        
        # Calculate days for each period
        construction_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        operations_days = [182, 184, 181, 184]
        all_days = construction_days + operations_days
        
        # Operations flag: 0 during construction, 1 during operations
        operations_flag = [0] * 12 + [1] * 4
        
        # Days in operations: 0 during construction, actual days during operations
        days_operations = [0] * 12 + operations_days
        
        # Cumulative days for indexation
        cumulative_days = list(np.cumsum(all_days))
        
        self.mock_instance.financial_model = {
            'dates': {
                'model': {
                    'end': pd.Series(all_dates)
                }
            },
            'days': {
                'model': pd.Series(all_days),
                'operations': pd.Series(days_operations),
                'contract': pd.Series(days_operations),
                'contract_indexation': pd.Series(cumulative_days),
                'merchant_indexation': pd.Series(cumulative_days),
                'opex_indexation': pd.Series(cumulative_days),
                'lease_indexation': pd.Series(cumulative_days)
            },
            'flags': {
                'operations': pd.Series(operations_flag)
            }
        }
        
        self.times = Times(self.mock_instance)
    
    def test_init(self):
        """Test Times initialization."""
        self.assertEqual(self.times.instance, self.mock_instance)
        self.assertEqual(self.times.financial_model, self.mock_instance.financial_model)
    
    def test_initialize_time_series_creates_section(self):
        """Test _initialize_time_series creates section when missing."""
        if 'time_series' in self.times.financial_model:
            del self.times.financial_model['time_series']
        
        self.times._initialize_time_series()
        
        self.assertIn('time_series', self.times.financial_model)
        self.assertEqual(self.times.financial_model['time_series'], {})
    
    def test_initialize_time_series_preserves_existing(self):
        """Test _initialize_time_series preserves existing section."""
        self.times.financial_model['time_series'] = {'existing': 'data'}
        
        self.times._initialize_time_series()
        
        self.assertEqual(self.times.financial_model['time_series'], {'existing': 'data'})
    
    def test_calculate_days_in_year(self):
        """Test _calculate_days_in_year with leap and non-leap years."""
        self.times._initialize_time_series()
        self.times._calculate_days_in_year()
        
        days_in_year = self.times.financial_model['time_series']['days_in_year']
        
        # 2023 (construction): all 365
        for i in range(12):
            self.assertEqual(days_in_year[i], 365)
        
        # 2024 (operations): all 366 (leap year)
        for i in range(12, 14):
            self.assertEqual(days_in_year[i], 366)
        
        # 2025 (operations): all 365
        for i in range(14, 16):
            self.assertEqual(days_in_year[i], 365)
    
    def test_calculate_years_in_period(self):
        """Test _calculate_years_in_period calculation."""
        self.times._initialize_time_series()
        self.times._calculate_days_in_year()
        self.times._calculate_years_in_period()
        
        result = self.times.financial_model['time_series']['years_in_period']
        
        # Construction months (2023)
        construction_expected = [31/365, 28/365, 31/365, 30/365, 31/365, 30/365, 
                               31/365, 31/365, 30/365, 31/365, 30/365, 31/365]
        
        for i in range(12):
            self.assertAlmostEqual(result[i], construction_expected[i], places=6)
        
        # Operations semi-annual (2024-2025)
        operations_expected = [
            182/366,  # H1 2024 (leap year)
            184/366,  # H2 2024 (leap year)
            181/365,  # H1 2025
            184/365   # H2 2025
        ]
        
        for i, expected in enumerate(operations_expected):
            self.assertAlmostEqual(result[12 + i], expected, places=6)
    
    def test_calculate_years_during_operations(self):
        """Test _calculate_years_during_operations calculation."""
        self.times._initialize_time_series()
        self.times._calculate_days_in_year()
        self.times._calculate_years_in_period()
        self.times._calculate_years_during_operations()
        
        result = self.times.financial_model['time_series']['years_during_operations']
        
        # First 12 periods (construction) should be 0
        for i in range(12):
            self.assertEqual(result[i], 0)
        
        # Operations periods should match years_in_period
        years_in_period = self.times.financial_model['time_series']['years_in_period']
        for i in range(12, 16):
            self.assertEqual(result[i], years_in_period[i])
    
    def test_calculate_quarters(self):
        """Test _calculate_quarters returns correct quarters."""
        self.times._initialize_time_series()
        self.times._calculate_quarters()
        
        result = self.times.financial_model['time_series']['quarters']
        
        # Construction: Jan=Q1, Feb=Q1, Mar=Q1, Apr=Q2, etc.
        construction_quarters = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]
        # Operations: Jun=Q2, Dec=Q4
        operations_quarters = [2, 4, 2, 4]
        
        expected = pd.Series(construction_quarters + operations_quarters)
        pd.testing.assert_series_equal(pd.Series(result), expected, check_dtype=False)
    
    def test_calculate_years_from_cod(self):
        """Test _calculate_years_from_cod calculations."""
        self.times._initialize_time_series()
        self.times._calculate_days_in_year()
        self.times._calculate_years_in_period()
        self.times._calculate_years_during_operations()
        self.times._calculate_years_from_cod()
        
        # Check end of period calculations
        years_from_cod_eop = self.times.financial_model['time_series']['years_from_COD_eop']
        
        # Should be cumulative sum of years_during_operations
        expected_eop = self.times.financial_model['time_series']['years_during_operations'].cumsum()
        pd.testing.assert_series_equal(
            pd.Series(years_from_cod_eop),
            pd.Series(expected_eop),
            check_exact=False,
            rtol=1e-6
        )
        
        # Check beginning of period calculations
        years_from_cod_bop = self.times.financial_model['time_series']['years_from_COD_bop']
        expected_bop = expected_eop - self.times.financial_model['time_series']['years_during_operations']
        pd.testing.assert_series_equal(
            pd.Series(years_from_cod_bop),
            pd.Series(expected_bop),
            check_exact=False,
            rtol=1e-6
        )
        
        # Check average calculations
        years_from_cod_avg = self.times.financial_model['time_series']['years_from_COD_avg']
        expected_avg = (years_from_cod_eop + years_from_cod_bop) / 2
        pd.testing.assert_series_equal(
            pd.Series(years_from_cod_avg),
            pd.Series(expected_avg),
            check_exact=False,
            rtol=1e-6
        )
    
    def test_calculate_series_end_period_year(self):
        """Test _calculate_series_end_period_year extracts years correctly."""
        self.times._initialize_time_series()
        self.times._calculate_series_end_period_year()
        
        result = self.times.financial_model['time_series']['series_end_period_year']
        
        # All 2023 for construction, then 2024 and 2025 for operations
        expected = pd.Series([2023] * 12 + [2024, 2024, 2025, 2025])
        
        pd.testing.assert_series_equal(pd.Series(result), expected, check_dtype=False)
    
    def test_calculate_pct_in_operations_period(self):
        """Test _calculate_pct_in_operations_period calculation."""
        self.times._initialize_time_series()
        self.times._calculate_pct_in_operations_period()
        
        result = self.times.financial_model['time_series']['pct_in_operations_period']
        
        # First 12 periods (construction): all 0
        for i in range(12):
            self.assertEqual(result[i], 0)
        
        # Operations periods: should be 1.0 (100%)
        for i in range(12, 16):
            self.assertEqual(result[i], 1.0)
    
    def test_calculate_years_from_base_dates(self):
        """Test _calculate_years_from_base_dates calculation."""
        self.times._initialize_time_series()
        self.times._calculate_days_in_year()
        self.times._calculate_years_from_base_dates()
        
        result = self.times.financial_model['time_series']['years_from_base_dates']
        
        # Check all indexation keys are present
        expected_keys = ['contract_indexation', 'merchant_indexation', 'opex_indexation', 'lease_indexation']
        for key in expected_keys:
            self.assertIn(key, result)
        
        # Check merchant indexation values (as an example)
        merchant = result['merchant_indexation']
        
        # After 12 months (end of 2023): should be exactly 1.0
        self.assertAlmostEqual(merchant[11], 365/365, places=6)
        self.assertEqual(merchant[11], 1.0)
        
        # After 24 months (end of 2024): should be exactly 2.0
        # 365 (2023) + 366 (2024) = 731 days
        # But we need to account for leap year in calculation
        cumulative_at_end_2024 = merchant[13]  # Index 13 is end of 2024
        self.assertAlmostEqual(cumulative_at_end_2024, 2.0, places=2)
    
    def test_calculate_pct_in_contract_period(self):
        """Test _calculate_pct_in_contract_period calculation."""
        self.times._initialize_time_series()
        self.times._calculate_pct_in_contract_period()
        
        result = self.times.financial_model['time_series']['pct_in_contract_period']
        
        # First 12 periods (construction): operations days = 0, so result = 0
        for i in range(12):
            self.assertEqual(result[i], 0)
        
        # Operations periods: contract days = operations days, so result = 1.0
        for i in range(12, 16):
            self.assertEqual(result[i], 1.0)
    
    def test_calculate_pct_in_contract_period_partial(self):
        """Test _calculate_pct_in_contract_period with partial contract periods."""
        # Modify contract days to be partial - need to match the length of operations days
        # First 12 periods are construction (0), then 4 operations periods
        contract_days = [0] * 12 + [91, 184, 181, 92]
        self.times.financial_model['days']['contract'] = pd.Series(contract_days)
        
        self.times._initialize_time_series()
        self.times._calculate_pct_in_contract_period()
        
        result = self.times.financial_model['time_series']['pct_in_contract_period']
        
        # First 12 periods should be 0 (construction)
        for i in range(12):
            self.assertEqual(result[i], 0)
        
        # Period 12: 91/182 = 0.5
        self.assertAlmostEqual(result[12], 91/182, places=6)
        
        # Period 13: 184/184 = 1.0
        self.assertEqual(result[13], 1.0)
        
        # Period 14: 181/181 = 1.0
        self.assertEqual(result[14], 1.0)
        
        # Period 15: 92/184 = 0.5
        self.assertAlmostEqual(result[15], 92/184, places=6)
    
    def test_initialize_full_flow(self):
        """Test complete initialization flow."""
        # Remove any existing time_series section
        if 'time_series' in self.times.financial_model:
            del self.times.financial_model['time_series']
        
        self.times.initialize()
        
        # Verify all expected keys are present
        time_series = self.times.financial_model['time_series']
        expected_keys = [
            'days_in_year',
            'years_in_period',
            'years_during_operations',
            'quarters',
            'years_from_COD_eop',
            'years_from_COD_bop',
            'years_from_COD_avg',
            'series_end_period_year',
            'pct_in_operations_period',
            'years_from_base_dates',
            'pct_in_contract_period'
        ]
        
        for key in expected_keys:
            self.assertIn(key, time_series, f"Missing key: {key}")
    
    def test_annual_periodicity(self):
        """Test Times with annual periodicity."""
        # Set up annual periods
        self.times.financial_model['dates']['model']['end'] = pd.Series([
            datetime(2023, 12, 31),
            datetime(2024, 12, 31),
            datetime(2025, 12, 31)
        ])
        self.times.financial_model['days']['model'] = pd.Series([365, 366, 365])
        self.times.financial_model['days']['operations'] = pd.Series([0, 366, 365])
        self.times.financial_model['flags']['operations'] = pd.Series([0, 1, 1])
        
        self.times._initialize_time_series()
        self.times._calculate_days_in_year()
        self.times._calculate_years_in_period()
        
        result = self.times.financial_model['time_series']['years_in_period']
        
        # Annual periods should be exactly 1.0
        self.assertEqual(result[0], 1.0)
        self.assertEqual(result[1], 1.0)
        self.assertEqual(result[2], 1.0)
    
    def test_quarterly_periodicity(self):
        """Test Times with quarterly periodicity."""
        # Set up quarterly periods for 2024 (leap year)
        self.times.financial_model['dates']['model']['end'] = pd.Series([
            datetime(2024, 3, 31),   # Q1
            datetime(2024, 6, 30),   # Q2
            datetime(2024, 9, 30),   # Q3
            datetime(2024, 12, 31)   # Q4
        ])
        self.times.financial_model['days']['model'] = pd.Series([91, 91, 92, 92])
        
        self.times._initialize_time_series()
        self.times._calculate_days_in_year()
        self.times._calculate_years_in_period()
        self.times._calculate_quarters()
        
        # Check quarters
        quarters = self.times.financial_model['time_series']['quarters']
        expected_quarters = pd.Series([1, 2, 3, 4])
        pd.testing.assert_series_equal(pd.Series(quarters), expected_quarters, check_dtype=False)
        
        # Check years in period
        years_in_period = self.times.financial_model['time_series']['years_in_period']
        
        # Sum should be exactly 1.0 for the full year
        self.assertAlmostEqual(sum(years_in_period), 1.0, places=6)
    
    def test_leap_year_handling(self):
        """Test correct handling of leap years."""
        # Test dates spanning leap year boundary
        self.times.financial_model['dates']['model']['end'] = pd.Series([
            datetime(2023, 12, 31),  # Non-leap
            datetime(2024, 12, 31),  # Leap
            datetime(2025, 12, 31)   # Non-leap
        ])
        
        self.times._initialize_time_series()
        self.times._calculate_days_in_year()
        
        days_in_year = self.times.financial_model['time_series']['days_in_year']
        expected = pd.Series([365, 366, 365])
        
        pd.testing.assert_series_equal(pd.Series(days_in_year), expected)
    
    def test_zero_operations_days(self):
        """Test handling when all operations days are zero."""
        # Need to set operations days to all zeros with correct length (16 periods)
        self.times.financial_model['days']['operations'] = pd.Series([0] * 16)
        # Also update contract days to match
        self.times.financial_model['days']['contract'] = pd.Series([0] * 16)
        
        self.times._initialize_time_series()
        self.times._calculate_pct_in_operations_period()
        self.times._calculate_pct_in_contract_period()
        
        # All percentages should be 0
        pct_operations = self.times.financial_model['time_series']['pct_in_operations_period']
        pct_contract = self.times.financial_model['time_series']['pct_in_contract_period']
        
        self.assertTrue(all(pct == 0 for pct in pct_operations))
        self.assertTrue(all(pct == 0 for pct in pct_contract))


class TestGetQuarters(unittest.TestCase):
    """Test cases for the get_quarters function."""
    
    def test_get_quarters_basic(self):
        """Test get_quarters with various dates."""
        date_list = [
            datetime(2023, 1, 15),   # Q1
            datetime(2023, 4, 30),   # Q2
            datetime(2023, 7, 1),    # Q3
            datetime(2023, 10, 31),  # Q4
            datetime(2023, 12, 25)   # Q4
        ]
        
        result = get_quarters(date_list)
        expected = pd.Series([1, 2, 3, 4, 4])
        
        pd.testing.assert_series_equal(result, expected, check_dtype=False)
    
    def test_get_quarters_string_dates(self):
        """Test get_quarters with string dates."""
        date_list = ['2023-03-31', '2023-06-30', '2023-09-30', '2023-12-31']
        
        result = get_quarters(date_list)
        expected = pd.Series([1, 2, 3, 4])
        
        pd.testing.assert_series_equal(result, expected, check_dtype=False)
    
    def test_get_quarters_empty_list(self):
        """Test get_quarters with empty list."""
        result = get_quarters([])
        expected = pd.Series([], dtype='int64')
        
        pd.testing.assert_series_equal(result, expected, check_dtype=False)


class TestCalcYearsFromBaseDates(unittest.TestCase):
    """Test cases for the calc_years_from_base_dates function."""
    
    def test_calc_years_from_base_dates_basic(self):
        """Test basic functionality of calc_years_from_base_dates."""
        days_series = {
            'contract_indexation': pd.Series([181, 365, 546, 730]),  # Cumulative days
            'merchant_indexation': pd.Series([181, 365, 546, 730]),
            'opex_indexation': pd.Series([181, 365, 546, 730]),
            'lease_indexation': pd.Series([181, 365, 546, 730]),
            'other_key': pd.Series([100, 200, 300, 400])  # Should be ignored
        }
        days_in_year = pd.Series([365, 365, 365, 366])
        
        result = calc_years_from_base_dates(days_series, days_in_year)
        
        # Check all expected keys are present
        expected_keys = ['contract_indexation', 'merchant_indexation', 'opex_indexation', 'lease_indexation']
        for key in expected_keys:
            self.assertIn(key, result)
        
        # Check 'other_key' is not included
        self.assertNotIn('other_key', result)
        
        # Check calculations for merchant_indexation
        merchant = result['merchant_indexation']
        # Since days_series values are cumulative, divide by days_in_year
        expected = pd.Series([
            181/365,   # 181 cumulative days / 365 days in year
            365/365,   # 365 cumulative days / 365 days in year = 1.0
            546/365,   # 546 cumulative days / 365 days in year
            730/366    # 730 cumulative days / 366 days in year (leap)
        ])
        
        # The second value should be exactly 1.0 (one year)
        self.assertAlmostEqual(merchant[1], 1.0, places=6)
        
        # Compare all values
        pd.testing.assert_series_equal(merchant, expected, check_dtype=False)
    
    def test_calc_years_from_base_dates_exact_years(self):
        """Test calc_years_from_base_dates produces exact years at boundaries."""
        # Semi-annual periods designed to sum to exact years
        days_series = {
            'contract_indexation': pd.Series([181, 184, 182, 184]),  # Cumulative: 181, 365, 547, 731
            'merchant_indexation': pd.Series([181, 184, 182, 184]),
            'opex_indexation': pd.Series([181, 184, 182, 184]),
            'lease_indexation': pd.Series([181, 184, 182, 184])
        }
        days_in_year = pd.Series([365, 365, 366, 366])
        
        # Need to make cumulative
        for key in days_series:
            days_series[key] = days_series[key].cumsum()
        
        result = calc_years_from_base_dates(days_series, days_in_year)
        
        # Check merchant_indexation
        merchant = result['merchant_indexation']
        
        # After 2 semi-annual periods (365 days), should be exactly 1.0
        self.assertAlmostEqual(merchant[1], 365/365, places=10)
        self.assertEqual(merchant[1], 1.0)
        
        # After 4 semi-annual periods (731 days in leap year), should be exactly 2.0
        self.assertAlmostEqual(merchant[3], 731/366, places=6)
    
    def test_calc_years_from_base_dates_all_zero(self):
        """Test calc_years_from_base_dates with all zero days."""
        days_series = {
            'contract_indexation': pd.Series([0, 0, 0, 0]),
            'merchant_indexation': pd.Series([0, 0, 0, 0]),
            'opex_indexation': pd.Series([0, 0, 0, 0]),
            'lease_indexation': pd.Series([0, 0, 0, 0])
        }
        days_in_year = pd.Series([365, 365, 365, 365])
        
        result = calc_years_from_base_dates(days_series, days_in_year)
        
        # All values should be 0
        for key in result:
            self.assertTrue(all(result[key] == 0))


class TestTimesEdgeCases(unittest.TestCase):
    """Edge case tests for Times class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_instance = Mock()
        self.mock_instance.financial_model = {}
        self.times = Times(self.mock_instance)
    
    def test_single_period(self):
        """Test Times with only one period."""
        financial_model_data = {
            'dates': {
                'model': {
                    'end': pd.Series([datetime(2023, 12, 31)])
                }
            },
            'days': {
                'model': pd.Series([365]),
                'operations': pd.Series([365]),
                'contract': pd.Series([365]),
                'contract_indexation': pd.Series([365]),
                'merchant_indexation': pd.Series([365]),
                'opex_indexation': pd.Series([365]),
                'lease_indexation': pd.Series([365])
            },
            'flags': {
                'operations': pd.Series([1])
            }
        }
        self.mock_instance.financial_model = financial_model_data
        self.times = Times(self.mock_instance)
        
        self.times.initialize()
        
        # Verify single period calculations
        time_series = self.times.financial_model['time_series']
        self.assertEqual(len(time_series['days_in_year']), 1)
        self.assertEqual(time_series['days_in_year'][0], 365)
        self.assertEqual(time_series['years_in_period'][0], 1.0)
    
    def test_very_long_time_series(self):
        """Test Times with 100+ periods."""
        num_periods = 120  # 60 years of semi-annual periods
        
        # Generate dates for 60 years
        dates = []
        for year in range(2023, 2083):
            dates.extend([
                datetime(year, 6, 30),
                datetime(year, 12, 31)
            ])
        
        financial_model_data = {
            'dates': {
                'model': {
                    'end': pd.Series(dates[:num_periods])
                }
            },
            'days': {
                'model': pd.Series([182] * num_periods),
                'operations': pd.Series([182] * num_periods),
                'contract': pd.Series([182] * num_periods),
                'contract_indexation': pd.Series(range(182, 182 * (num_periods + 1), 182)),
                'merchant_indexation': pd.Series(range(182, 182 * (num_periods + 1), 182)),
                'opex_indexation': pd.Series(range(182, 182 * (num_periods + 1), 182)),
                'lease_indexation': pd.Series(range(182, 182 * (num_periods + 1), 182))
            },
            'flags': {
                'operations': pd.Series([1] * num_periods)
            }
        }
        self.mock_instance.financial_model = financial_model_data
        self.times = Times(self.mock_instance)
        
        self.times.initialize()
        
        # Verify calculations completed
        time_series = self.times.financial_model['time_series']
        self.assertEqual(len(time_series['days_in_year']), num_periods)
        self.assertEqual(len(time_series['years_in_period']), num_periods)
        
        # Check years_from_COD_eop increases monotonically
        years_from_cod = time_series['years_from_COD_eop']
        for i in range(1, len(years_from_cod)):
            self.assertGreater(years_from_cod[i], years_from_cod[i-1])
    
    def test_monthly_to_quarterly_transition(self):
        """Test Times with monthly construction transitioning to quarterly operations."""
        # 6 months construction + 8 quarters operations (2 years)
        construction_dates = [
            datetime(2023, 1, 31), datetime(2023, 2, 28), datetime(2023, 3, 31),
            datetime(2023, 4, 30), datetime(2023, 5, 31), datetime(2023, 6, 30)
        ]
        operations_dates = [
            datetime(2023, 9, 30),   # Q3 2023
            datetime(2023, 12, 31),  # Q4 2023
            datetime(2024, 3, 31),   # Q1 2024
            datetime(2024, 6, 30),   # Q2 2024
            datetime(2024, 9, 30),   # Q3 2024
            datetime(2024, 12, 31),  # Q4 2024
            datetime(2025, 3, 31),   # Q1 2025
            datetime(2025, 6, 30)    # Q2 2025
        ]
        
        all_dates = construction_dates + operations_dates
        
        # Calculate days
        construction_days = [31, 28, 31, 30, 31, 30]
        operations_days = [92, 92, 91, 91, 92, 92, 90, 91]
        all_days = construction_days + operations_days
        
        # Flags
        operations_flag = [0] * 6 + [1] * 8
        days_operations = [0] * 6 + operations_days
        
        financial_model_data = {
            'dates': {'model': {'end': pd.Series(all_dates)}},
            'days': {
                'model': pd.Series(all_days),
                'operations': pd.Series(days_operations),
                'contract': pd.Series(days_operations),
                'contract_indexation': pd.Series(np.cumsum(all_days)),
                'merchant_indexation': pd.Series(np.cumsum(all_days)),
                'opex_indexation': pd.Series(np.cumsum(all_days)),
                'lease_indexation': pd.Series(np.cumsum(all_days))
            },
            'flags': {'operations': pd.Series(operations_flag)}
        }
        self.mock_instance.financial_model = financial_model_data
        self.times = Times(self.mock_instance)
        
        self.times.initialize()
        time_series = self.times.financial_model['time_series']
        
        # Verify quarterly structure during operations
        quarters = time_series['quarters']
        operations_quarters = quarters[6:]  # Skip construction
        expected_quarters = pd.Series([3, 4, 1, 2, 3, 4, 1, 2])
        # Reset index to match for comparison
        pd.testing.assert_series_equal(
            pd.Series(operations_quarters).reset_index(drop=True), 
            expected_quarters, 
            check_dtype=False
        )


if __name__ == '__main__':
    unittest.main()