function build_fs_financing_plan(json) {
  
  // The data is in the fs_financing_plan_data
  const allData = json.fs_financing_plan_data;
  
  // Get the maximum array length to determine number of columns
  let maxLength = 0;
  Object.values(allData).forEach(section => {
    Object.values(section).forEach(value => {
      if (Array.isArray(value)) {
        maxLength = Math.max(maxLength, value.length);
      }
    });
  });
  
  // Define the sections in the order you want them displayed
  const sections = [
    { key: 'fs_dates', title: 'Dates' },
    { key: 'fs_uses', title: 'Uses' },
    { key: 'fs_sources', title: 'Sources' },
    { key: 'fs_gearing', title: 'Gearing' }
  ];
  
  let tableContent = "<table class='table table-bordered'>";
  
 
  tableContent += "<tbody>";
  
  // Process each section
  sections.forEach(section => {
    const sectionData = allData[section.key];
    
    if (!sectionData) return;
    
    let isFirstRowInSection = true;
    const sectionRowCount = Object.keys(sectionData).filter(key => Array.isArray(sectionData[key])).length;
    
    // Process each item in the section data
    for (const subKey in sectionData) {
      const subValue = sectionData[subKey];
      
      if (Array.isArray(subValue)) {
        // Check if this row is a "Total" row
        const isTotal = subKey.toLowerCase().includes('total');
        tableContent += isTotal ? "<tr class='total-row'>" : "<tr>";
        
        // Add section title only for the first row of each section
        if (isFirstRowInSection) {
          tableContent += `<td rowspan="${sectionRowCount}" style="vertical-align: middle; font-weight: bold;">${section.title}</td>`;
          isFirstRowInSection = false;
        }
        
        tableContent += "<td>" + convertToTitleCase(subKey) + "</td>";
        
        // Determine unit based on section
        let unit = "";
        if (section.key === 'fs_uses' || section.key === 'fs_sources') {
          unit = "kEUR";
        } else if (section.key === 'fs_dates') {
          unit = "";
        } else if (section.key === 'fs_gearing') {
          // Check the specific key within fs_gearing
          if (subKey === 'cumulative_project_costs') {
            unit = "kEUR";
          } else if (subKey === 'gearing') {
            unit = "%";
          }
        }
        
        tableContent += "<td>" + unit + "</td>";
        
        // Add values for each period
        for (let i = 0; i < maxLength; i++) {
          if (i < subValue.length) {
            const value = subValue[i];
            let formattedValue;
            
            // Format based on data type and section
            if (section.key === 'fs_dates') {
              formattedValue = value === 'Total' ? 'Total' : 
                (value.includes('T') ? value.substring(5, 7) + '/' + value.substring(0, 4) : value);
            } else if (section.key === 'fs_gearing' && subKey === 'gearing') {
              // Format gearing as percentage
              formattedValue = typeof value === 'number' ? formatAsPercent(value) : (value || "-");
            } else if (typeof value === 'number') {
              // Format all other numeric values as integers
              formattedValue = formatAsInt(value);
            } else {
              formattedValue = value || "-";
            }
            
            tableContent += "<td>" + formattedValue + "</td>";
          } else {
            tableContent += "<td>-</td>";
          }
        }
        
        tableContent += "</tr>";
      }
    }
  });
  
  tableContent += "</tbody></table>";
  
  // Use the single selector for the combined table
  const element = $("#fs_financing_plan");
  if (element.length > 0) {
    element.html(tableContent);
  } else {
    console.warn("Element with selector #fs_financing_plan not found");
  }
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

function formatAsPercent(num) {
  return new Intl.NumberFormat("default", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

