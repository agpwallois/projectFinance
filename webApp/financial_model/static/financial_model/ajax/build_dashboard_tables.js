function build_dashboard_tables(json) {
  
  const columnLabel_summary = {
    "Project IRR (pre-tax)": "%",
    "Project IRR (post-tax)": "%",
    "Share capital IRR": "%",
    "Shareholder loan IRR": "%",
    "Equity IRR": "%",
    "Effective gearing": "%",

    "Payback date": "date",
    "Payback time": "years from FC",

    "Constraint": "text",
    "Average life": "years from FC",
    "Average DSCR": "x", // Ensure this key is unique or logic combined
    
    "Balance sheet": "true/false",
    "Financing plan": "true/false",

    "": "",
    "Date of final repayment": "date",
    "Tenor (door-to-door)": "years",
    "Average life (from Financial Close)": "years",
    "Maximum gearing": "%",
    "Minimum DSCR": "x",
    "Equity injection": "text",
    "Subgearing": "%",
    "Senior Debt IRR": "%",
    "Production": "x",
    "Operating costs": "x",
    "Debt maturity": "true/false",
    "Discount factor": "%",
    "Unit": "",
    "Total Uses": "",
    "Total Sources": "",
  };



  const tables = [
    { data: json.tables['Debt metrics'], selector: "#summary_debt" },
    { data: json.tables['Project IRR'], selector: "#summary_project" },
    { data: json.tables['Equity metrics'], selector: "#summary_equity" },
    { data: json.tables['Audit'], selector: "#summary_audit" },
    { data: json.tables['Valuation'], selector: "#summary_valuation" },

  ];


  tables.forEach((table) => {
    build_dashboard_table(table.data, table.selector); // Pass optional arg
  });

function build_dashboard_table(json_input, div_output) {
  let table_result = "<table>";

  // Check if the first key is an empty string (assuming it contains headers)
  if (json_input.hasOwnProperty("")) {
    const headers = json_input[""];

    table_result += "<tr>";
    $.each(headers, function (_, header) {
      table_result += "<th>" + header + "</th>";
    });
    table_result += "</tr>";

    delete json_input[""];
  }

  $.each(json_input, function (key, data) {

    if (json_input != json.tables['Sensi']) {
      table_result += "<tr>";

      table_result += "<td>" + key + "</td>";

      if (columnLabel_summary.hasOwnProperty(key)) {
        table_result += "<td>" + columnLabel_summary[key] + "</td>";
      } else {
        table_result += "<td>" + "kEUR" + "</td>";
      }
      }

      $.each(data, function (_, cellData) {
        if (cellData === "false" || cellData === "False") {
          table_result += "<td><span class='red-dot'></span>" + cellData + "</td>";
        } else {
          table_result += "<td>" + cellData + "</td>";
        }
      });
      table_result += "</tr>";
    
  });

  table_result += "</table>";
  $(div_output).html(table_result);
}

  build_dashboard_table_sensi(json)





function build_dashboard_table_sensi(json) {
    function createTable(tableData, diffData) {
        let table_result = "<table class='sensi-table'>";

        // Get headers
        const headers = tableData[""];
        table_result += "<thead><tr>";
        $.each(headers, function (_, header) {
            table_result += "<th>" + header + "</th>";
        });
        table_result += "</tr></thead><tbody>";
        


        // Process all scenarios (except the headers row)
        Object.keys(tableData).forEach(function(scenario) {
            if (scenario === "") return; // Skip headers row

            const values = tableData[scenario];
            table_result += "<tr>";

            // Loop through each value in this scenario
            $.each(values, function (index, cellData) {
                let headerName = headers[index];
                let diffValue = "";

                // Try to get the diff value from the appropriate diff data
                try {
                    diffValue = diffData[scenario][headerName] || "";
                } catch (e) {
                    diffValue = "";
                }

                // Is this the last column?
                const isLastColumn = index === values.length - 1;

                // Handle valid data
                if (cellData !== "-" && cellData !== "nanx" && cellData !== "nan%") {
       
                    
                    // Check if this is a false value - also check trimmed version and boolean
                    const cellDataStr = String(cellData).trim();
                    const isFalse = (cellDataStr === "false" || cellDataStr === "False" || cellData === false);

                    
                    if (diffValue && diffValue !== "-" && diffValue !== "nanx" && diffValue !== "nan%" && !isLastColumn) {
                        // Parse the diff value
                        let numericDiff = 0;
                        let diffStr = String(diffValue);
                        
                        if (diffStr.includes('%')) {
                            numericDiff = parseFloat(diffStr.replace('%', '')) || 0;
                        } else if (diffStr.includes('x')) {
                            numericDiff = parseFloat(diffStr.replace('x', '')) || 0;
                        } else {
                            numericDiff = parseFloat(diffStr) || 0;
                        }

                        // Determine impact class
                        let impactClass = numericDiff > 0 ? "impact-positive" : 
                                         (numericDiff < 0 ? "impact-negative" : "impact-neutral");

                        // Cell with diff value
                        table_result += "<td class='value-cell'>";
                        table_result += "<div class='value-container'>";
                        table_result += "<div class='main-value'>";
                        
                        if (isFalse) {
                            table_result += "<span class='red-dot'></span>";
                        }
                        table_result += cellData;
                        
                        table_result += "</div>";
                        table_result += "<div class='impact-indicator " + impactClass + "'>" + diffValue + "</div>";
                        table_result += "</div>";
                        table_result += "</td>";
                    } else {
                        // Cell without diff value
                        table_result += "<td class='value-cell'>";
                        if (isFalse) {
                            table_result += "<span class='red-dot'></span>";
                        }
                        table_result += cellData + "</td>";
                    }
                } else {
                    // Empty cell for invalid data
                    table_result += "<td></td>";
                }
            });

            table_result += "</tr>";
        });

        table_result += "</tbody></table>";
        return table_result;
    }


    // Build and display tables with different diff data
    const tableSensi = createTable(json.tables['Sensi'], json.table_sensi_diff);
    $("#summary_sensi").html(tableSensi);

    const tableSensiIRR = createTable(json.tables['Sensi_IRR'], json.table_sensi_diff_IRR);
    $("#sponsor_summary_sensi").html(tableSensiIRR);
}

}