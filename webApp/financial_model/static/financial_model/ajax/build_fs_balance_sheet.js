function build_fs_balance_sheet(json) {
  
  // The data is in the fs_balance_sheet_data
  const allData = json.fs_balance_sheet;
  
  // Get all unique years across all sections
  let allYears = new Set();
  Object.values(allData).forEach(section => {
    Object.values(section).forEach(yearData => {
      if (typeof yearData === 'object' && !Array.isArray(yearData)) {
        Object.keys(yearData).forEach(year => allYears.add(year));
      }
    });
  });
  
  // Convert to array and sort
  const years = Array.from(allYears).sort((a, b) => parseInt(a) - parseInt(b));
  
  // Define the sections in the order you want them displayed
  const sections = [
    { key: 'annual_assets', title: 'Assets' },
    { key: 'annual_liabilities', title: 'Liabilities' },
  ];
  
  let tableContent = "<table class='table table-bordered'>";
  
  // Build header row with years
  tableContent += "<thead><tr>";
  tableContent += "<th></th>"; // Item column
  tableContent += "<th></th>"; // Unit column
  
  // Add year columns
  years.forEach(year => {
    tableContent += `<th>${year}</th>`;
  });
  
  tableContent += "</tr></thead>";
  tableContent += "<tbody>";
  
  // Process each section
  sections.forEach((section, sectionIndex) => {
    const sectionData = allData[section.key];
    
    if (!sectionData) return;
    
    // Add section header row
    if (sectionIndex > 0) {
      // Add some spacing between sections
      tableContent += "<tr class='section-spacer'><td colspan='" + (years.length + 2) + "'>&nbsp;</td></tr>";
    }
    
    tableContent += "<tr class='section-header'>";
    tableContent += `<td colspan="${years.length + 2}" style="font-weight: bold; background-color: #e0e0e0; text-align: center;">${section.title}</td>`;
    tableContent += "</tr>";
    
    // Process each item in the section data
    for (const subKey in sectionData) {
      const yearValues = sectionData[subKey];
      
      if (typeof yearValues === 'object' && !Array.isArray(yearValues)) {
        // Check if this row is a "Total" row
        const isTotal = subKey.toLowerCase().includes('total');
        tableContent += isTotal ? "<tr class='total-row'>" : "<tr>";
        
        tableContent += "<td>" + convertToTitleCase(subKey) + "</td>";
        tableContent += "<td>kEUR</td>";
        
        // Add values for each year
        years.forEach(year => {
          const value = yearValues[year];
          if (value !== undefined && value !== null) {
            // Check if value is 0
            const formattedValue = (value === 0) ? "-" : formatAsFloat(value);
            tableContent += "<td>" + formattedValue + "</td>";
          } else {
            tableContent += "<td>-</td>";
          }
        });
        
        tableContent += "</tr>";
      }
    }
  });
  
  tableContent += "</tbody></table>";
  
  // Use the single selector for the combined table
  const element = $("#annual_balance_sheet");
  if (element.length > 0) {
    element.html(tableContent);
  } else {
    console.warn("Element with selector #annual_balance_sheet not found");
  }
}

function convertToTitleCase(snakeCaseStr) {
  if (!snakeCaseStr) return "";
  const words = snakeCaseStr.split('_');
  const titleCaseStr = words
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
  return titleCaseStr;
}

function formatAsFloat(dataValue) {
  const formattedValue = dataValue.toLocaleString("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return formattedValue;
}