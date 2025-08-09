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
    
    // Date Start column
    const startDateCell = row.insertCell(0);
    startDateCell.textContent = allData.model_start_dates[i];
    
    // Date End column
    const endDateCell = row.insertCell(1);
    endDateCell.textContent = allData.model_end_dates[i];
    
    // Repayment column
    const repaymentCell = row.insertCell(2);
    repaymentCell.textContent = formatNumber(allData.senior_debt_repayments[i]);
    repaymentCell.style.textAlign = 'right';
    
    // Interests column
    const interestCell = row.insertCell(3);
    interestCell.textContent = formatNumber(allData.senior_debt_interests[i]);
    interestCell.style.textAlign = 'right';
    
    // Debt Service column
    const debtServiceCell = row.insertCell(4);
    debtServiceCell.textContent = formatNumber(allData.debt_service_total[i]);
    debtServiceCell.style.textAlign = 'right';
  }
}

// Helper function to format numbers
function formatNumber(value) {
  if (value === null || value === undefined || value === '') {
    return '0';
  }
  return parseFloat(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  });
}