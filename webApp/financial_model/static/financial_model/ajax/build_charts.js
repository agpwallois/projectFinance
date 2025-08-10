// Function to format dates from "2032-06-30T00:00:00" to "06-2032"
function formatDateForChart(dateStr) {
    if (!dateStr) return dateStr;
    
    // Handle both ISO format (2032-06-30T00:00:00) and DD/MM/YYYY format
    let date;
    if (dateStr.includes('T')) {
        // ISO format
        date = new Date(dateStr);
    } else if (dateStr.includes('/')) {
        // DD/MM/YYYY format - convert to Date
        const parts = dateStr.split('/');
        date = new Date(parts[2], parts[1] - 1, parts[0]);
    } else {
        return dateStr; // Return as-is if format not recognized
    }
    
    if (isNaN(date.getTime())) return dateStr;
    
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${month}-${year}`;
}

function build_charts(json) {
    // Cache frequently accessed data
    const constrData = json.charts_data_constr;
    const dashboardCards = json.dashboard_cards;
    
    // Pre-compute all values at once
    const dates = Object.values(constrData['dates_model_end']).map(formatDateForChart);
    const constrCostsTotal = Object.values(constrData['construction_costs_total']);
    const usesTotalCumul = Object.values(constrData['uses_total_cumul']);
    const seniorDebtIdc = Object.values(constrData['uses_senior_debt_idc_and_fees']);
    const dsraFunding = Object.values(constrData['DSRA_initial_funding']);
    const shareCapitalInj = Object.values(constrData['charts_share_capital_inj_neg']);
    const shlDraw = Object.values(constrData['charts_shl_draw_neg']);
    const seniorDebtDraw = Object.values(constrData['charts_senior_debt_draw_neg']);
    const usesTotal = Object.values(constrData['uses_total']);
    const gearing = Object.values(constrData['gearing_during_finplan']);
    
    // Batch update chartProjectCosts
    const projectCostsData = chartProjectCosts.data;
    projectCostsData.labels = dates;
    projectCostsData.datasets[0].data = constrCostsTotal;
    projectCostsData.datasets[1].data = usesTotalCumul;
    projectCostsData.datasets[2].data = constrCostsTotal;
    projectCostsData.datasets[3].data = seniorDebtIdc;
    projectCostsData.datasets[4].data = dsraFunding;
    projectCostsData.datasets[5].data = constrCostsTotal;
    
    // Batch update chartFinPlan
    const finPlanData = chartFinPlan.data;
    finPlanData.labels = dates;
    finPlanData.datasets[0].data = shareCapitalInj;
    finPlanData.datasets[1].data = shlDraw;
    finPlanData.datasets[2].data = seniorDebtDraw;
    finPlanData.datasets[3].data = usesTotal;
    finPlanData.datasets[4].data = gearing;
    
    // Process Uses data
    const usesData = dashboardCards['Uses'];
    const usesLabels = Object.keys(usesData).filter(key => key !== 'Total');
    const usesValues = usesLabels.map(key => parseFloat(usesData[key][0]));
    const maxValue = Math.max(...usesValues) * 1.1;
    const backgroundData = usesValues.map(value => maxValue - value);
    
    // Batch update chartUses
    const chartUsesData = chartUses.data;
    chartUsesData.labels = usesLabels;
    chartUsesData.datasets[0].data = usesValues;
    chartUsesData.datasets[1].data = backgroundData;
    chartUses.options.scales.x.max = maxValue;
    
    // Ensure enough colors for chartUses
    if (usesLabels.length > chartUsesData.datasets[0].backgroundColor.length) {
        const defaultColors = ['#CE65FF', '#FF6630', '#FECD32', '#34CB98'];
        const bgColors = chartUsesData.datasets[0].backgroundColor;
        while (bgColors.length < usesLabels.length) {
            bgColors.push(defaultColors[bgColors.length % defaultColors.length]);
        }
    }
    
    // Process Sources data
    const sourcesData = dashboardCards['Sources'];
    const excludedKeys = ['Total', 'Equity'];
    const sourcesLabels = Object.keys(sourcesData).filter(key => !excludedKeys.includes(key));
    const sourcesValues = sourcesLabels.map(key => parseFloat(sourcesData[key][0]));
    
    // Batch update chartSources
    chartSources.data.labels = sourcesLabels;
    chartSources.data.datasets[0].data = sourcesValues;
    
    // Single update call for all charts
    chartProjectCosts.update();
    chartFinPlan.update();
    chartUses.update();
    chartSources.update();
}

function updateChartsAnnual(json) {
    // Cache frequently accessed data
    const annual = json.df_annual;
    const eoy = json.df_eoy;
    
    // Pre-compute common labels (all charts use the same)
    const labels = Object.keys(annual['opex']['total']);
    
    // Pre-compute all data arrays
    const opexTotal = Object.values(annual['opex']['total']);
    const leaseCosts = Object.values(annual['opex']['lease_costs']);
    const contractRev = Object.values(annual['revenues']['contract']);
    const merchantRev = Object.values(annual['revenues']['merchant']);
    const dsEffective = Object.values(annual['senior_debt']['DS_effective']);
    const shareCapital = Object.values(annual['charts']['share_capital_inj_and_repay']);
    const shlInj = Object.values(annual['charts']['shl_inj_and_repay']);
    const dividends = Object.values(annual['distr_account']['dividends_paid']).map(value => value * -1);
    const irrCurve = Object.values(eoy['IRR']['irr_curve']);
    const interests = Object.values(annual['senior_debt']['interests_operations']);
    const repayments = Object.values(annual['senior_debt']['repayments']);
    const dscrEffective = Object.values(eoy['ratios']['DSCR_effective']);
    const seniorDebt = Object.values(annual['sources']['senior_debt']);
    const balanceEop = Object.values(eoy['senior_debt']['balance_eop']);
    const llcr = Object.values(eoy['ratios']['LLCR']);
    const plcr = Object.values(eoy['ratios']['PLCR']);
    const dsraBop = Object.values(eoy['DSRA']['dsra_bop']);
    const retainedEarnings = Object.values(eoy['IS']['retained_earnings_bop']);
    const distrBalance = Object.values(eoy['distr_account']['balance_eop']);
    const shareRepayments = Object.values(annual['share_capital']['repayments']);
    const production = Object.values(annual['production']['total']);
    const degradation = Object.values(eoy['capacity']['degradation_factor']);
    
    // Batch update all charts
    const charts = [
        {
            chart: chartCashFlow,
            datasets: [opexTotal, leaseCosts, contractRev, merchantRev, dsEffective]
        },
        {
            chart: chartEqtFlow,
            datasets: [shareCapital, shlInj, dividends, irrCurve]
        },
        {
            chart: chartDebtS,
            datasets: [repayments, interests, dscrEffective]
        },
        {
            chart: chartDebtOut,
            datasets: [seniorDebt, repayments, balanceEop]
        },
        {
            chart: chartDSCR,
            datasets: [dscrEffective, llcr, plcr]
        },
        {
            chart: chartDSRA,
            datasets: [dsEffective, dsraBop]
        },
        {
            chart: chartCash,
            datasets: [retainedEarnings, distrBalance, dividends, shareRepayments]
        },
        {
            chart: chartProduction,
            datasets: [production, degradation]
        }
    ];
    
    // Update all charts in a single loop
    charts.forEach(({ chart, datasets }) => {
        chart.data.labels = labels;
        datasets.forEach((data, index) => {
            chart.data.datasets[index].data = data;
        });
        chart.update();
    });
}

function updateChartsDebtPeriodicity(json) {
    // Cache frequently accessed data
    const df = json.df;
    
    // Pre-compute common labels
    const labels = Object.values(df['dates']['model']['end']).map(formatDateForChart);
    
    // Pre-compute all data arrays
    const dataArrays = {
        opexTotal: Object.values(df['opex']['total']),
        leaseCosts: Object.values(df['opex']['lease_costs']),
        contractRev: Object.values(df['revenues']['contract']),
        merchantRev: Object.values(df['revenues']['merchant']),
        dsEffective: Object.values(df['senior_debt']['DS_effective']),
        shareCapital: Object.values(df['charts']['share_capital_inj_and_repay']),
        shlInj: Object.values(df['charts']['shl_inj_and_repay']),
        dividends: Object.values(df['distr_account']['dividends_paid']),
        irrCurve: Object.values(df['IRR']['irr_curve']),
        interests: Object.values(df['senior_debt']['interests_operations']),
        repayments: Object.values(df['senior_debt']['repayments']),
        dscrEffective: Object.values(df['ratios']['DSCR_effective']),
        seniorDebt: Object.values(df['sources']['senior_debt']),
        balanceEop: Object.values(df['senior_debt']['balance_eop']),
        llcr: Object.values(df['ratios']['LLCR']),
        plcr: Object.values(df['ratios']['PLCR']),
        dsraBop: Object.values(df['DSRA']['dsra_bop']),
        retainedEarnings: Object.values(df['IS']['retained_earnings_bop']),
        distrBalance: Object.values(df['distr_account']['balance_eop']),
        shareRepayments: Object.values(df['share_capital']['repayments']),
        production: Object.values(df['production']['total']),
        degradation: Object.values(df['capacity']['degradation_factor'])
    };
    
    // Define chart configurations
    const chartConfigs = [
        {
            chart: chartCashFlow,
            data: [dataArrays.opexTotal, dataArrays.leaseCosts, dataArrays.contractRev, 
                   dataArrays.merchantRev, dataArrays.dsEffective]
        },
        {
            chart: chartEqtFlow,
            data: [dataArrays.shareCapital, dataArrays.shlInj, dataArrays.dividends, 
                   dataArrays.irrCurve]
        },
        {
            chart: chartDebtS,
            data: [dataArrays.interests, dataArrays.repayments, dataArrays.dscrEffective]
        },
        {
            chart: chartDebtOut,
            data: [dataArrays.seniorDebt, dataArrays.repayments, dataArrays.balanceEop]
        },
        {
            chart: chartDSCR,
            data: [dataArrays.dscrEffective, dataArrays.llcr, dataArrays.plcr]
        },
        {
            chart: chartDSRA,
            data: [dataArrays.dsEffective, dataArrays.dsraBop]
        },
        {
            chart: chartCash,
            data: [dataArrays.retainedEarnings, dataArrays.distrBalance, 
                   dataArrays.dividends, dataArrays.shareRepayments]
        },
        {
            chart: chartProduction,
            data: [dataArrays.production, dataArrays.degradation]
        }
    ];
    
    // Update all charts efficiently
    chartConfigs.forEach(({ chart, data }) => {
        chart.data.labels = labels;
        data.forEach((dataset, index) => {
            chart.data.datasets[index].data = dataset;
        });
        chart.update();
    });
}

// Additional optimization: Batch all chart updates if multiple functions are called sequentially
function batchUpdateCharts(updateFunctions, json) {
    // Disable chart animations temporarily for faster updates
    const charts = [chartProjectCosts, chartFinPlan, chartUses, chartSources, 
                   chartCashFlow, chartEqtFlow, chartDebtS, chartDebtOut, 
                   chartDSCR, chartDSRA, chartCash, chartProduction];
    
    // Store original animation settings
    const originalAnimations = charts.map(chart => ({
        chart: chart,
        animation: chart.options.animation
    }));
    
    // Disable animations
    charts.forEach(chart => {
        if (chart.options) {
            chart.options.animation = false;
        }
    });
    
    // Execute all update functions
    updateFunctions.forEach(fn => fn(json));
    
    // Restore animations
    originalAnimations.forEach(({ chart, animation }) => {
        if (chart.options) {
            chart.options.animation = animation;
        }
    });
}