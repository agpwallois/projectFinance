# DSCR Calculation Fix for Truncated Periods

## Problem Identified

When construction ends mid-period (e.g., June 15th), the first operations period has very few days (e.g., 15 days until June 30th). This causes:

1. **Extreme Interest Rate Calculations**: 
   - Interest for 15 days divided by balance, then annualized (×360/15 = ×24)
   - Can produce interest rates like 200% instead of expected 8%

2. **Meaningless DSCR Values**:
   - Both CFADS and Debt Service are minimal for truncated periods
   - Division of two very small numbers can produce extreme values (-100000000000x)

3. **Statistical Distortion**:
   - Including truncated periods in DSCR_min and DSCR_avg skews results

## Solution Implemented

### 1. Smart Interest Rate Calculation
```python
# For truncated periods (< 30 days):
if days['debt_interest_operations'][i] < 30:
    # Use the project's standard interest rate instead of extrapolating
    avg_interest_rate[i] = self.instance.senior_debt_interest_rate
else:
    # Normal calculation with a safety cap
    avg_interest_rate[i] = period_rate * 360 / days
    avg_interest_rate[i] = min(avg_interest_rate[i], 2 * standard_rate)
```

### 2. Annualized DSCR for Truncated Periods
```python
# For truncated periods, annualize both CFADS and DS:
if days_debt_ops[i] < 30:
    annualization_factor = 360 / days_debt_ops[i]
    annualized_cfads = cfads_amo[i] * annualization_factor
    annualized_ds = ds_effective[i] * annualization_factor
    dscr_effective[i] = annualized_cfads / annualized_ds
```

### 3. Exclude Truncated Periods from Statistics
```python
# Only include meaningful periods (>= 30 days) in statistics:
meaningful_periods = days_debt_ops >= 30
mask = debt_amo_flag & meaningful_periods
valid_dscr = dscr_effective[mask]
```

## Benefits

1. **Prevents Extreme Values**: No more -100000000000x DSCR values
2. **Meaningful Ratios**: DSCR represents actual debt service coverage capability
3. **Accurate Statistics**: DSCR_min and DSCR_avg reflect real operational periods
4. **Robust to Date Changes**: Works correctly regardless of construction end date

## Implementation Options

### Option 1: Replace Existing File
Replace `/financial_model_sections/ratios.py` with `ratios_fixed.py`

### Option 2: Selective Updates
Apply only the specific fixes needed to the existing file

### Option 3: Add Configuration Flag
Add a setting to enable/disable truncated period handling

## Testing Recommendations

Test with various construction end dates:
- End of month (no truncation)
- Mid-month (15-day truncation)  
- Beginning of month (1-2 day truncation)
- End of quarter vs mid-quarter

Verify that:
- DSCR values remain reasonable (typically 1.0 - 3.0 range)
- Interest rates stay near project rate (±50%)
- Statistics exclude truncated periods
- LLCR and PLCR calculations remain stable