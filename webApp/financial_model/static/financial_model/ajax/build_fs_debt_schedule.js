function build_fs_debt_schedule(json) {
  
  // The data is in the fs_debt_schedule
  const allData = json.fs_debt_schedule;
  
  // Get the table body element
  const tableBody = document.querySelector('#debt-schedule tbody');
  
  // Clear existing table content
  tableBody.innerHTML = '';
  
  // Check if data exists
  if (!allData || !allData.model_start_dates || allData.model_start_dates.length === 0) {
    const row = tableBody.insertRow();
    const cell = row.insertCell(0);
    cell.colSpan = 5;
    cell.textContent = 'No debt schedule data available';
    cell.style.textAlign = 'center';
    return;
  }
  
  // Build table rows
  for (let i = 0; i < allData.model_start_dates.length; i++) {
    const row = tableBody.insertRow();
    
    // Add CSS class to first row (total row)
    if (i === 0) {
      row.classList.add('debt-schedule-total-row');
    }
    
    // Date Start column - centered
    const startDateCell = row.insertCell(0);
    startDateCell.textContent = allData.model_start_dates[i];
    startDateCell.style.textAlign = 'center';
    
    // Date End column - centered
    const endDateCell = row.insertCell(1);
    endDateCell.textContent = allData.model_end_dates[i];
    endDateCell.style.textAlign = 'center';
    
    // Repayment column - centered
    const repaymentCell = row.insertCell(2);
    repaymentCell.textContent = formatNumber(allData.senior_debt_repayments[i]);
    repaymentCell.style.textAlign = 'center';
    
    // Interests column - centered
    const interestCell = row.insertCell(3);
    interestCell.textContent = formatNumber(allData.senior_debt_interests[i]);
    interestCell.style.textAlign = 'center';
    
    // Debt Service column - centered
    const debtServiceCell = row.insertCell(4);
    debtServiceCell.textContent = formatNumber(allData.debt_service_total[i]);
    debtServiceCell.style.textAlign = 'center';
  }
}

// Helper function to format numbers with zero as dash
function formatNumber(value) {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  
  // Check if value is 0
  if (parseFloat(value) === 0) {
    return '-';
  }
  
  return parseFloat(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  });
}