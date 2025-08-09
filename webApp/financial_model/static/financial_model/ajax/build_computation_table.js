function build_computation_table(json) {

  const columnLabel = {
    "dates": "date",
    "flags": "flag",
  };

  const columnFormatting = {
    "Target DSCR": formatDSCR,
    "Average interest rate": formatAsPercent,
    "Seasonality": formatAsPercent,
    "Year": formatAsInt,
    "Days in period": formatAsInt,
    "Days in year": formatAsInt,
    "Years in period": formatAsPercent,
    "Construction": formatAsInt,
    "Percentage in contract period": formatAsPercent,
    "Percentage in operations period": formatAsPercent,
    "Indexation": formatAsPercent,
    "Discount factor": formatAsPercent,
    "Cumulative discount factor": formatAsPercent,
    "Capacity degradation factor": formatAsPercent,
    "Capacity factor": formatAsPercent,
    "Years from indexation start date": formatAsFloat,
    "Cash available for dividends": formatOther,
    "Dividends declared": formatOther,
    "Dividends paid": formatOther,
  };

  const excludedColumns = [
    "Period",
    "Year",
    "year",
    "Days",
    "Seasonality",
    "Percentage",
    "Distributable profit",
    "Discount factor",
    "Cumulative discount factor",
    "Assets",
    "Total assets",
    "Retained earnings",
    "Total liabilities",
    "balance",
    "Balance",
    "Cash",
    "price",
    "capacity",
    "date",
    "DSCR",
    "BoP",
    "EoP",
    "Cash available",
    "indexation",
    "Property, Plant",
    "liquidity",
    "Accounts",
  ];

  var dict = {};

$.each(json.df, function (key, value) {
  dict[key] = { selector: "#" + key };
});

for (const key in dict) {
  const { selector } = dict[key];
  let tableContent = "<table>";

  for (const subKey in json.df[key]) {
    const subValue = json.df[key][subKey];

    // Check if subValue is a nested dictionary
    if (typeof subValue === 'object' && !Array.isArray(subValue)) {
      // Handle nested dictionary
      for (const nestedKey in subValue) {
        tableContent += "<tr>";
        tableContent += "<td>" + convertToTitleCase(subKey) + " - " + convertToTitleCase(nestedKey) + "</td>";

        // Determine the label for the column
        if (columnLabel.hasOwnProperty(key)) {
          tableContent += "<td>" + columnLabel[key] + "</td>";
        } else {
          tableContent += "<td>kEUR</td>";
        }

        // Adding the values from the JSON data array in separate columns
        const valuesArray = subValue[nestedKey];
        // Add null/undefined check here
        if (valuesArray && Array.isArray(valuesArray)) {
          for (let i = 0; i < valuesArray.length; i++) {
            const value = valuesArray[i];
            let formattedValue;

            if (isDate(value)) {
              // Format as date if it's a date object
              formattedValue = formatDate(value);
            } else if (columnFormatting[subKey]) {
              // Use specified formatting function if available
              formattedValue = columnFormatting[subKey](value);
            } else {
              // Default to formatting as integer
              formattedValue = formatAsFloat(value);
            }

            tableContent += "<td>" + formattedValue + "</td>";
          }
        }

        tableContent += "</tr>";
      }
    } else {
      // Handle regular case where subValue is not a nested dictionary
      tableContent += "<tr>";
      tableContent += "<td>" + convertToTitleCase(subKey) + "</td>";

      // Determine the label for the column
      if (columnLabel.hasOwnProperty(key)) {
        tableContent += "<td>" + columnLabel[key] + "</td>";
      } else {
        tableContent += "<td>kEUR</td>";
      }

      // Adding the values from the JSON data array in separate columns
      const valuesArray = subValue;
      // Add null/undefined check here
      if (valuesArray && Array.isArray(valuesArray)) {
        for (let i = 0; i < valuesArray.length; i++) {
          const value = valuesArray[i];
          let formattedValue;

          if (isDate(value)) {
            // Format as date if it's a date object
            formattedValue = formatDate(value);
          } else if (columnFormatting[subKey]) {
            // Use specified formatting function if available
            formattedValue = columnFormatting[subKey](value);
          } else {
            // Default to formatting as integer
            formattedValue = formatAsFloat(value);
          }

          tableContent += "<td>" + formattedValue + "</td>";
        }
      }

      tableContent += "</tr>";
    }
  }

  tableContent += "</table>";
  $(selector).html(tableContent);
}

// Function to convert a snake_case string to Title Case
function convertToTitleCase(snakeCaseStr) {
  // Split the string by underscores
  const words = snakeCaseStr.split('_');

  // Capitalize the first letter of each word and join them with spaces
  const titleCaseStr = words
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return titleCaseStr;
}

// Function to check if a value is a date
function isDate(value) {
  // Consider values as date strings in format DD/MM/YYYY
  if (typeof value === "string" && /^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
    return true;
  }

  return false;
}

// Function to format a Date object or string as dd/mm/yyyy
function formatDate(value) {
  if (isDate(value)) {
    // Manually split the date to DD/MM/YYYY format
    const [day, month, year] = value.split('/');
    return `${day}/${month}/${year}`;
  } else {
    const date = new Date(value);
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0"); // Months are zero-based
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
  }
}

function formatDSCR(dataValue) {
  // Check for zero value first
  if (dataValue === 0) {
    return "-";
  }
  const formattedValue = dataValue.toFixed(2) + "x";
  return formattedValue;
}

function formatOther(dataValue) {
  // Check for zero value first
  if (dataValue === 0) {
    return "-";
  }
  const roundedValue = Math.round(Math.abs(dataValue) * 10) / 10;
  const formattedValue = roundedValue.toLocaleString("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return dataValue < 0 ? `(${formattedValue})` : formattedValue;
}

function formatAsInt(dataValue) {
  // Check for zero value first
  if (dataValue === 0) {
    return "-";
  }
  return Math.floor(dataValue).toString();
}

function formatAsFloat(dataValue) {
  // Check for zero value first
  if (dataValue === 0) {
    return "-";
  }
  const formattedValue = dataValue.toLocaleString("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return formattedValue;
}

function containsExcludedWords(pd_column_name) {
  const excludedWords = ["date", "end", "start"];
  for (const word of excludedWords) {
    if (pd_column_name.toLowerCase().includes(word)) {
      return true;
    }
  }
  return false;
}

function formatAsPercent(num) {
  // Check for zero value first
  if (num === 0) {
    return "-";
  }
  return new Intl.NumberFormat("default", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}
}