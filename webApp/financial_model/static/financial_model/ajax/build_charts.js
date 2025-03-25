function build_charts(json) {

        chartProjectCosts.data.labels = Object.values(json.charts_data_constr['dates_model_end']);
        chartProjectCosts.data.datasets[0].data = Object.values(json.charts_data_constr['construction_costs_total']);
        chartProjectCosts.data.datasets[1].data = Object.values(json.charts_data_constr['uses_total_cumul']);
        chartProjectCosts.data.datasets[2].data = Object.values(json.charts_data_constr['construction_costs_total']);
        chartProjectCosts.data.datasets[3].data = Object.values(json.charts_data_constr['uses_senior_debt_idc_and_fees']);
        chartProjectCosts.data.datasets[4].data = Object.values(json.charts_data_constr['DSRA_initial_funding']);
        chartProjectCosts.data.datasets[5].data = Object.values(json.charts_data_constr['construction_costs_total']);
        chartProjectCosts.update();

        chartFinPlan.data.labels = Object.values(json.charts_data_constr['dates_model_end']);
        chartFinPlan.data.datasets[0].data = Object.values(json.charts_data_constr['charts_share_capital_inj_neg']);
        chartFinPlan.data.datasets[1].data = Object.values(json.charts_data_constr['charts_shl_draw_neg']);
        chartFinPlan.data.datasets[2].data = Object.values(json.charts_data_constr['charts_senior_debt_draw_neg']);
        chartFinPlan.data.datasets[3].data = Object.values(json.charts_data_constr['uses_total']);
        chartFinPlan.data.datasets[4].data = Object.values(json.charts_data_constr['gearing_during_finplan']);
        chartFinPlan.update();  



// Extract data from json
    const usesData = json.tables['Uses'];
    const labels = Object.keys(usesData).filter(key => key !== 'Total');  // Exclude "Total"
    const dataValues = labels.map(key => parseFloat(usesData[key][0]));
    
    // Calculate max value with padding for better visualization
    const maxValue = Math.max(...dataValues) * 1.1; // Add 20% padding
    
    // Calculate background data (difference between max and each value)
    const backgroundData = dataValues.map(value => maxValue - value);
    
    // Update chart data
    chartUses.data.labels = labels;
    chartUses.data.datasets[0].data = dataValues;      // Actual data bars (now dataset 0)
    chartUses.data.datasets[1].data = backgroundData;  // Background (gray) bars (now dataset 1)
    
    // Update max scale to ensure bars fill the right amount of space
    chartUses.options.scales.x.max = maxValue;
    
    // Make sure we have enough colors if there are many data points
    if (labels.length > chartUses.data.datasets[0].backgroundColor.length) {
        const defaultColors = ['#CE65FF', '#FF6630', '#FECD32', '#34CB98'];
        while (chartUses.data.datasets[0].backgroundColor.length < labels.length) {
            chartUses.data.datasets[0].backgroundColor.push(
                defaultColors[chartUses.data.datasets[0].backgroundColor.length % defaultColors.length]
            );
        }
    }
    
    // Update the chart
    chartUses.update();

        const sourcesData = json.tables['Sources'];
        const excludedKeys = ['Total', 'Equity'];
        const sourcesLabels = Object.keys(sourcesData).filter(key => !excludedKeys.includes(key));
        const sourcesValues = sourcesLabels.map(key => parseFloat(sourcesData[key][0]));

        chartSources.data.labels = sourcesLabels;
        chartSources.data.datasets[0].data = sourcesValues;
        chartSources.update();


}

function updateChartsAnnual(json) {

        chartCashFlow.data.labels = Object.keys(json.df_annual['opex']['total']);
        chartCashFlow.data.datasets[0].data = Object.values(json.df_annual['opex']['total']);
        chartCashFlow.data.datasets[1].data = Object.values(json.df_annual['opex']['lease_costs']);
        chartCashFlow.data.datasets[2].data = Object.values(json.df_annual['revenues']['contract']);
        chartCashFlow.data.datasets[3].data = Object.values(json.df_annual['revenues']['merchant']);
        chartCashFlow.data.datasets[4].data = Object.values(json.df_annual['senior_debt']['DS_effective']);
        chartCashFlow.update();  

        chartEqtFlow.data.labels = Object.keys(json.df_annual['opex']['total']);
        chartEqtFlow.data.datasets[0].data = Object.values(json.df_annual['charts']['share_capital_inj_and_repay']);
        chartEqtFlow.data.datasets[1].data = Object.values(json.df_annual['charts']['shl_inj_and_repay']);
        chartEqtFlow.data.datasets[2].data = Object.values(json.df_annual['distr_account']['dividends_paid']);
        chartEqtFlow.data.datasets[3].data = Object.values(json.df_eoy['IRR']['irr_curve']);
        chartEqtFlow.update();  

        chartDebtS.data.labels = Object.keys(json.df_annual['opex']['total']);
        chartDebtS.data.datasets[1].data = Object.values(json.df_annual['senior_debt']['interests_operations']);
        chartDebtS.data.datasets[0].data = Object.values(json.df_annual['senior_debt']['repayments']);
        chartDebtS.data.datasets[2].data = Object.values(json.df_eoy['ratios']['DSCR_effective']);
        chartDebtS.update();  

        chartDebtOut.data.labels = Object.keys(json.df_annual['opex']['total']);
        chartDebtOut.data.datasets[0].data = Object.values(json.df_annual['injections']['senior_debt']);
        chartDebtOut.data.datasets[1].data = Object.values(json.df_annual['senior_debt']['repayments']);
        chartDebtOut.data.datasets[2].data = Object.values(json.df_eoy['senior_debt']['balance_eop']);
        chartDebtOut.update();  

        chartDSCR.data.labels = Object.keys(json.df_annual['opex']['total']);
        chartDSCR.data.datasets[0].data = Object.values(json.df_eoy['ratios']['DSCR_effective']);
        chartDSCR.data.datasets[1].data = Object.values(json.df_eoy['ratios']['LLCR']);
        chartDSCR.data.datasets[2].data = Object.values(json.df_eoy['ratios']['PLCR']);
        chartDSCR.update();  

        chartDSRA.data.labels = Object.keys(json.df_annual['opex']['total']);
        chartDSRA.data.datasets[0].data = Object.values(json.df_annual['senior_debt']['DS_effective']);
        chartDSRA.data.datasets[1].data = Object.values(json.df_eoy['DSRA']['dsra_bop']);
        chartDSRA.update();  

        chartCash.data.labels = Object.keys(json.df_annual['opex']['total']);
        chartCash.data.datasets[0].data = Object.values(json.df_eoy['IS']['retained_earnings_bop']);
        chartCash.data.datasets[1].data = Object.values(json.df_eoy['distr_account']['balance_eop']);
        chartCash.data.datasets[2].data = Object.values(json.df_annual['distr_account']['dividends_paid']);
        chartCash.data.datasets[3].data = Object.values(json.df_annual['share_capital']['repayments']);
        chartCash.update();  
}

function updateChartsDebtPeriodicity(json) {

        chartCashFlow.data.labels = Object.values(json.df['dates']['model']['end']);
        chartCashFlow.data.datasets[0].data = Object.values(json.df['opex']['total']);
        chartCashFlow.data.datasets[1].data = Object.values(json.df['opex']['lease_costs']);
        chartCashFlow.data.datasets[2].data = Object.values(json.df['revenues']['contract']);
        chartCashFlow.data.datasets[3].data = Object.values(json.df['revenues']['merchant']);
        chartCashFlow.data.datasets[4].data = Object.values(json.df['senior_debt']['DS_effective']);
        chartCashFlow.update();  

        chartEqtFlow.data.labels = Object.values(json.df['dates']['model']['end']);
        chartEqtFlow.data.datasets[0].data = Object.values(json.df['charts']['share_capital_inj_and_repay']);
        chartEqtFlow.data.datasets[1].data = Object.values(json.df['charts']['shl_inj_and_repay']);
        chartEqtFlow.data.datasets[2].data = Object.values(json.df['distr_account']['dividends_paid']);
        chartEqtFlow.data.datasets[3].data = Object.values(json.df['IRR']['irr_curve']);
        chartEqtFlow.update();  

        chartDebtS.data.labels = Object.values(json.df['dates']['model']['end']);
        chartDebtS.data.datasets[0].data = Object.values(json.df['senior_debt']['interests_operations']);
        chartDebtS.data.datasets[1].data = Object.values(json.df['senior_debt']['repayments']);
        chartDebtS.data.datasets[2].data = Object.values(json.df['ratios']['DSCR_effective']);
        chartDebtS.update();  

        chartDebtOut.data.labels = Object.values(json.df['dates']['model']['end']);
        chartDebtOut.data.datasets[0].data = Object.values(json.df['injections']['senior_debt']);
        chartDebtOut.data.datasets[1].data = Object.values(json.df['senior_debt']['repayments']);
        chartDebtOut.data.datasets[2].data = Object.values(json.df['senior_debt']['balance_eop']);
        chartDebtOut.update();  

        chartDSCR.data.labels = Object.values(json.df['dates']['model']['end']);
        chartDSCR.data.datasets[0].data = Object.values(json.df['ratios']['DSCR_effective']);
        chartDSCR.data.datasets[1].data = Object.values(json.df['ratios']['LLCR']);
        chartDSCR.data.datasets[2].data = Object.values(json.df['ratios']['PLCR']);
        chartDSCR.update();  

        chartDSRA.data.labels = Object.values(json.df['dates']['model']['end']);
        chartDSRA.data.datasets[0].data = Object.values(json.df['senior_debt']['DS_effective']);
        chartDSRA.data.datasets[1].data = Object.values(json.df['DSRA']['dsra_bop']);
        chartDSRA.update();  

        chartCash.data.labels = Object.values(json.df['dates']['model']['end']);
        chartCash.data.datasets[0].data = Object.values(json.df['IS']['retained_earnings_bop']);
        chartCash.data.datasets[1].data = Object.values(json.df['distr_account']['balance_eop']);
        chartCash.data.datasets[2].data = Object.values(json.df['distr_account']['dividends_paid']);
        chartCash.data.datasets[3].data = Object.values(json.df['share_capital']['repayments']);
        chartCash.update();  
}