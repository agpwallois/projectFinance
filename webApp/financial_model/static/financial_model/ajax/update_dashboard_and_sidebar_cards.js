function update_dashboard_and_sidebar_cards(json) {

        var dict_sidebar = {
                COD:"#dateCOD",
                installed_capacity:"#installed_capacity",
                end_of_operations:"#dateRetirement",
                sum_seasonality:"#sumSeasonality",
                sum_construction_costs:"#sumConstructionCosts",
                liquidation:"#dateLiquidation",
                date_debt_maturity:"#debtMaturity",
                sponsor_IRR:"#sponsor_IRR", 
                lender_DSCR:"#lender_DSCR",
                total_uses:"#total_uses",
                sponsor_prod_choice:"#sponsor_prod_choice",
                lender_prod_choice:"#lender_prod_choice",
                lender_mkt_price_choice:"#lender_mkt_price_choice",
                sponsor_mkt_price_choice:"#sponsor_mkt_price_choice",
                gearing:"#gearing",
                capacity:"#capacity",

        };

        for (var i = 0; i < Object.keys(dict_sidebar).length; i++) {
                var key = Object.keys(dict_sidebar)[i];
                $(Object.values(dict_sidebar)[i]).html(json.sidebar_data[key]);
        }
        
        // Also update #capacity with installed_capacity data
        $("#capacity").html(json.sidebar_data["installed_capacity"]);

        for (var i = 0; i < 42; i++) {
                $("#elecPriceLabel"+i).html(json.sidebar_data['price_elec_dict'][i]);
        }
}