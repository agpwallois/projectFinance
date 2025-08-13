"""
Debug script to understand debt maturity timing issue
"""
import datetime
from dateutil.relativedelta import relativedelta
import calendar

def analyze_debt_maturity_issue():
    """
    Analyze the debt maturity calculation when construction ends on 30/06
    """
    
    # Example scenario
    construction_start = datetime.date(2024, 1, 1)
    construction_end = datetime.date(2024, 6, 30)
    debt_tenor_years = 10  # Example: 10 year debt
    periodicity = 6  # Semi-annual
    
    print("=== Debt Maturity Analysis ===")
    print(f"Construction Start: {construction_start}")
    print(f"Construction End: {construction_end}")
    print(f"Debt Tenor: {debt_tenor_years} years")
    print(f"Periodicity: {periodicity} months (semi-annual)")
    print()
    
    # Current calculation method (from assumptions.py line 66)
    debt_maturity_raw = construction_start + relativedelta(months=int(debt_tenor_years * 12) - 1)
    debt_maturity_current = debt_maturity_raw.replace(
        day=calendar.monthrange(debt_maturity_raw.year, debt_maturity_raw.month)[1]
    )
    
    print("Current Method:")
    print(f"  Raw calculation: {construction_start} + {debt_tenor_years*12-1} months = {debt_maturity_raw}")
    print(f"  Adjusted to month end: {debt_maturity_current}")
    print()
    
    # COD and operations dates
    COD = construction_end + datetime.timedelta(days=1)
    print(f"COD (Construction + 1 day): {COD}")
    print()
    
    # Operations periods (semi-annual from COD)
    print("Operations Periods (Semi-annual):")
    current_period_start = COD
    period_num = 1
    
    while current_period_start <= debt_maturity_current:
        # Determine period end based on semi-annual schedule
        if current_period_start.month <= 6:
            period_end = datetime.date(current_period_start.year, 12, 31)
        else:
            period_end = datetime.date(current_period_start.year + 1, 6, 30)
        
        # Check if this period contains the debt maturity
        contains_maturity = current_period_start <= debt_maturity_current <= period_end
        
        print(f"  Period {period_num}: {current_period_start} to {period_end}", end="")
        if contains_maturity:
            print(f" <- CONTAINS MATURITY DATE ({debt_maturity_current})")
        else:
            print()
        
        # Move to next period
        current_period_start = period_end + datetime.timedelta(days=1)
        period_num += 1
        
        if period_num > 25:  # Safety limit
            break
    
    print()
    print("=== Issue Analysis ===")
    
    # The issue is that debt_maturity is calculated from construction START
    # But debt service starts from COD (construction END + 1)
    debt_service_duration = debt_maturity_current - COD
    print(f"Debt service period: {COD} to {debt_maturity_current}")
    print(f"Debt service duration: {debt_service_duration.days} days = {debt_service_duration.days/365.25:.2f} years")
    
    # This is less than the intended tenor
    intended_duration_days = debt_tenor_years * 365.25
    difference_days = intended_duration_days - debt_service_duration.days
    print(f"Intended debt service duration: {debt_tenor_years} years = {intended_duration_days:.0f} days")
    print(f"Difference: {difference_days:.0f} days = {difference_days/365.25:.2f} years")
    
    print()
    print("=== Proposed Fix ===")
    
    # The debt maturity should be calculated from COD, not construction start
    # Option 1: Calculate from COD
    debt_maturity_from_cod = COD + relativedelta(years=debt_tenor_years)
    debt_maturity_from_cod_adjusted = debt_maturity_from_cod.replace(
        day=calendar.monthrange(debt_maturity_from_cod.year, debt_maturity_from_cod.month)[1]
    )
    
    print(f"Option 1 - Calculate from COD:")
    print(f"  {COD} + {debt_tenor_years} years = {debt_maturity_from_cod}")
    print(f"  Adjusted to month end: {debt_maturity_from_cod_adjusted}")
    
    # Option 2: Align with period ends
    # Find the period end that is closest to COD + tenor years
    target_date = COD + relativedelta(years=debt_tenor_years)
    
    # Find the semi-annual period end on or after target date
    if target_date.month <= 6:
        aligned_maturity = datetime.date(target_date.year, 6, 30)
        if aligned_maturity < target_date:
            aligned_maturity = datetime.date(target_date.year, 12, 31)
    else:
        aligned_maturity = datetime.date(target_date.year, 12, 31)
        if aligned_maturity < target_date:
            aligned_maturity = datetime.date(target_date.year + 1, 6, 30)
    
    print(f"\nOption 2 - Align with semi-annual period ends:")
    print(f"  Target: {target_date}")
    print(f"  Aligned to period end: {aligned_maturity}")
    
    # Construction duration for context
    construction_duration = construction_end - construction_start
    print(f"\nConstruction Duration: {construction_duration.days} days = {construction_duration.days/30:.1f} months")
    
    return {
        'current_maturity': debt_maturity_current,
        'proposed_maturity_from_cod': debt_maturity_from_cod_adjusted,
        'proposed_maturity_aligned': aligned_maturity,
        'issue_description': f"Debt is maturing {difference_days/30:.1f} months early because maturity is calculated from construction start instead of COD"
    }

if __name__ == "__main__":
    result = analyze_debt_maturity_issue()
    print(f"\n=== Summary ===")
    print(f"Issue: {result['issue_description']}")
    print(f"Current maturity: {result['current_maturity']}")
    print(f"Proposed (from COD): {result['proposed_maturity_from_cod']}")
    print(f"Proposed (aligned): {result['proposed_maturity_aligned']}")