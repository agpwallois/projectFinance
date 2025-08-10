function build_fs_financial_statements(json) {
  
  // The data is in the first (and only) element of the array
  const allData = json.fs_financial_statements;
  
  // Get the keys (which are the table IDs)
  const keys = Object.keys(allData);
  
  // Process each key
  keys.forEach(key => {
    const selector = "#" + key;
    
    // Get the data for this specific key
    const data = allData[key];
    
    let tableContent = "<table class='table table-bordered table_annual excel-navigable'>";
    
    // First, we need to collect all unique columns (years + Total)
    let allColumns = new Set();
    
    // Collect columns from all items
    for (const subKey in data) {
      const subValue = data[subKey];
      if (typeof subValue === 'object' && !Array.isArray(subValue)) {
        Object.keys(subValue).forEach(col => allColumns.add(col));
      }
    }
    
    // Separate 'Total' from years
    let columns = [];
    let years = [];
    
    allColumns.forEach(col => {
      if (col === 'Total') {
        // Total will be added first
      } else {
        years.push(col);
      }
    });
    
    // Sort years numerically
    years.sort((a, b) => parseInt(a) - parseInt(b));
    
    // Build final column order: Total first, then sorted years
    if (allColumns.has('Total')) {
      columns.push('Total');
    }
    columns = columns.concat(years);
    
    // Build header row with columns
    tableContent += "<thead><tr>";
    tableContent += "<th></th>";
    tableContent += "<th></th>";
    
    // Add column headers
    columns.forEach(col => {
      let headerClass = "";
      
      // Add special styling for Total column header
      if (col === 'Total') {
        headerClass = " class='total-column'";
      }
      
      tableContent += `<th${headerClass}>${col}</th>`;
    });
    
    tableContent += "</tr></thead>";
    tableContent += "<tbody>";
    
    // Process each item in the data
    for (const subKey in data) {
      const subValue = data[subKey];
      
      // Check if subValue is an object with columns as keys
      if (typeof subValue === 'object' && !Array.isArray(subValue)) {
        tableContent += "<tr data-original-key='" + subKey + "'>";
        tableContent += "<td>" + convertToTitleCase(subKey) + "</td>";
        tableContent += "<td>kEUR</td>";
        
        // Add values for each column (Total first, then years)
        columns.forEach(col => {
          const value = subValue[col];
          let cellClass = "";
          
          // Add special styling for Total column
          if (col === 'Total') {
            cellClass = " class='total-column'";
          }
          
          // Check if this is a balance row and we're in the Total column
          const isBalanceRow = subKey.toLowerCase().includes('balance');
          const isTotalColumn = col === 'Total';
          
          if (isBalanceRow && isTotalColumn) {
            // Don't show sum for balance rows in Total column
            tableContent += "<td" + cellClass + ">-</td>";
          } else if (value !== undefined && value !== null) {
            // Check if value is 0
            const formattedValue = (value === 0) ? "-" : formatAsFloat(value);
            tableContent += "<td" + cellClass + ">" + formattedValue + "</td>";
          } else {
            tableContent += "<td" + cellClass + ">-</td>";
          }
        });
        
        tableContent += "</tr>";
      } else if (Array.isArray(subValue)) {
        // If it's still an array (legacy format), handle it
        tableContent += "<tr data-original-key='" + subKey + "'>";
        tableContent += "<td>" + convertToTitleCase(subKey) + "</td>";
        tableContent += "<td>kEUR</td>";
        
        for (let i = 0; i < subValue.length && i < columns.length; i++) {
          const value = subValue[i];
          // Check if value is 0
          const formattedValue = (value === 0) ? "-" : formatAsFloat(value);
          tableContent += "<td>" + formattedValue + "</td>";
        }
        
        tableContent += "</tr>";
      }
    }
    
    tableContent += "</tbody></table>";
    
    // Set the HTML
    $(selector).html(tableContent);
    
    // Apply financial total styling after table is created
    applyFinancialTotalStyling(selector);
  });
}

// Function to apply styling to financial total rows
function applyFinancialTotalStyling(tableSelector) {
  // Define the financial terms to highlight (using original snake_case format)
  const financialTotalTerms = [
    'total_revenues',
    'total_opex',
    'ebitda',
    'ebit',
    'ebt',
    'net_income', 
    'cash_flows_operating',
    'cash_flows_investing',
    'cash_flows_financing',
    'cfads',
    'balance_bop',   
    'balance_eop',   
   
  ];
  
  // Find and style the relevant rows
  $(tableSelector + ' tr').each(function() {
    // Get the original key from the data attribute
    const originalKey = $(this).data('original-key');
    
    // Skip if no original key (like header rows)
    if (!originalKey) {
      return;
    }
    
    // Check if the original key matches any of our financial total terms
    const isFinancialTotal = financialTotalTerms.some(term => 
      originalKey.toLowerCase() === term.toLowerCase()
    );
    
    if (isFinancialTotal) {
      $(this).addClass('financial-total');
    }
  });
}

// Keep your existing helper functions
function convertToTitleCase(snakeCaseStr) {
  if (!snakeCaseStr) return "";
  const words = snakeCaseStr.split('_');
  const titleCaseStr = words
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
  return titleCaseStr;
}

function formatAsInt(dataValue) {
  return Math.floor(dataValue).toString();
}

function formatAsFloat(dataValue) {
  const formattedValue = dataValue.toLocaleString("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return formattedValue;
}