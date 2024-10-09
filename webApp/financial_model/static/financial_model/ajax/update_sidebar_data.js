function update_sidebar_data(json) {

        var dict_sidebar = {
                COD:"#dateCOD",
                installed_capacity:"#installed_capacity",
                end_of_operations:"#dateRetirement",
                sum_seasonality:"#sumSeasonality",
                sum_construction_costs:"#sumConstructionCosts",
                liquidation:"#dateLiquidation",
                date_debt_maturity:"#debtMaturity",

        };

        for (var i = 0; i < Object.keys(dict_sidebar).length; i++) {
                var key = Object.keys(dict_sidebar)[i];
                $(Object.values(dict_sidebar)[i]).html(json.sidebar_data[key]);
        }

        for (var i = 0; i < 42; i++) {
                $("#elecPriceLabel"+i).html(json.sidebar_data['price_elec_dict'][i]);
        }
}