function build_dashboard_tables(json) {
  
  const columnLabel_summary = {
    "Project IRR (pre-tax)": "%",
    "Project IRR (post-tax)": "%",
    "Share capital IRR": "%",
    "Shareholder loan IRR": "%",
    "Equity IRR": "%",

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
    "Debt IRR": "%",
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
    { data: json.tables['Uses'], selector: "#summary_financing_plan_uses" },
    { data: json.tables['Sources'], selector: "#summary_financing_plan_sources" },
    { data: json.tables['Sensi'], selector: "#summary_sensi" },
    { data: json.tables['Valuation'], selector: "#summary_valuation" },

  ];


  tables.forEach((table) => build_dashboard_table(table.data, table.selector));


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
        if (cellData === "False") {
          table_result += "<td class='red-cell'>" + cellData + "</td>";
        } else {
          table_result += "<td>" + cellData + "</td>";
        }
      });
      table_result += "</tr>";
    
  });

  table_result += "</table>";
  $(div_output).html(table_result);
}

}