// Global variable to track the currently selected scenario
let currentSelectedScenario = 'sponsor_base_case';

$(document).ready(function() {
    // Initialize the application
    initializeApplication();
    makeGetRequest('sponsor_base_case');
    
    // Set up a one-time event listener for when the first AJAX request completes
    $(document).one('ajaxComplete', function() {
        // Apply initial highlighting
        applyHighlightingToScenario(currentSelectedScenario);
    });
});

function initializeApplication() {
    setupRadioButtonHandlers()
    set_up_sensitivities_form_submission_listeners();
    hide_construction_months_fields();
    hide_sidebar_years_fields();

    $(document).on('submit', '#post-form', function(e) {
        handleFormSubmission(e, this);
    });
}

function setupRadioButtonHandlers() {
    // Handle radio button changes for scenario selection
    $(document).on('change', 'input[name="scenarios"]', function() {
        if (this.checked) {
            const selectedScenario = $(this).val();
            
            // Store the selected scenario
            currentSelectedScenario = selectedScenario;
            
            // Highlight the selected row
            highlightSelectedRow(this);
            
            console.log(selectedScenario)
            // Make GET request with the selected scenario
            makeGetRequest(selectedScenario);
        }
    });
}

function highlightSelectedRow(radioElement) {
    // Remove 'selected' class from all rows in both left and right tables
    $('.dashboard-sensi-table tr').removeClass('selected');
    
    // Find the parent row of the clicked radio button
    const $selectedRow = $(radioElement).closest('tr');
    
    // Add 'selected' class to the clicked row
    $selectedRow.addClass('selected');
    
    // Find the corresponding row in the right table and highlight it
    if ($selectedRow.closest('.summary-scenario-left').length > 0) {
        // Get the value of the radio button to determine which scenario
        const radioValue = $(radioElement).val();
        
        // Get all radio buttons in order to find the index
        const $allRadios = $selectedRow.closest('.summary-scenario-left').find('input[name="scenarios"]');
        const selectedIndex = $allRadios.index(radioElement);
        
        // Find the right table container
        const $rightTable = $selectedRow.closest('.summary-container').find('.summary-scenario-right table');
        
        // Check if there's a header row in the right table
        const $rightTableHeader = $rightTable.find('thead tr');
        const hasHeader = $rightTableHeader.length > 0;
        
        // Find all data rows in the right table (excluding header if present)
        const $rightTableRows = $rightTable.find('tbody tr');
        
        // If the right table has more rows than we have radios, it might have a header row in tbody
        // Let's check the first row to see if it contains th elements
        const firstRowHasHeaders = $rightTableRows.first().find('th').length > 0;
        
        // Calculate the correct index
        let adjustedIndex = selectedIndex;
        if (firstRowHasHeaders && $rightTableRows.length > $allRadios.length) {
            // Skip the first row if it's a header row in tbody
            adjustedIndex = selectedIndex + 1;
        }
        
        // Use the adjusted index to select the corresponding row
        const $rightRow = $rightTableRows.eq(adjustedIndex);
        
        if ($rightRow.length > 0) {
            $rightRow.addClass('selected');
        }
    }
}

function showLoader() {
    // Show the loading modal
    $("#loading-modal").show();
    // Alternative: if you prefer to use display style directly
    // document.getElementById("loading-modal").style.display = "block";
}

function hideLoader() {
    // Hide the loading modal
    $("#loading-modal").hide();
    // Alternative: if you prefer to use display style directly
    // document.getElementById("loading-modal").style.display = "none";
}

function handleFormSubmission(e, formElement) {
    e.preventDefault();

    // Show loader before making the request
    showLoader();

    var formData = $(formElement).serialize();

    var postSettings = {
        type: 'POST',
        url: "", // Add your URL here
        data: formData,
        success: function(json) {
            // Hide loader on success
            hideLoader();
            handleSuccess(json);
        },
        error: function(xhr, status, error) {
            // Hide loader on error
            hideLoader();
            handleAjaxError(xhr, status, error);
        }
    };

    $.ajax(postSettings);
}

function makeGetRequest(value) {


    var getSettings = {
        url: '', // Add your URL here
        method: 'GET',
        data: {
            'scenario': value 
        },
        success: function(json) {
            // Hide loader on success
            hideLoader();
            handleSuccess(json);
        },
        error: function(xhr, status, error) {
            // Hide loader on error
            hideLoader();
            handleAjaxError(xhr, status, error);
        }
    };
    $.ajax(getSettings);
}

function handleSuccess(json) {
    console.log(json.df);
    console.log(json.dashboard_cards);
    console.log(json.sidebar_data);
    console.log(json.table_sensi_diff);
    console.log(json.table_sensi_diff_IRR);
    console.log(json.fs_financial_statements);
    console.log(json.fs_financing_plan);
    console.log(json.fs_balance_sheet);

    build_computation_table(json);
    build_dashboard_cards(json);
    
    build_fs_financial_statements(json);
    build_fs_financing_plan(json);
    build_fs_balance_sheet(json);

    build_charts(json);
    update_sidebar_data(json);

    // Apply highlighting based on the stored selected scenario
    applyHighlightingToScenario(currentSelectedScenario);

    function handleDropdownChange() {
        var selectedOption = $("#myDropdown").val();

        if (selectedOption === "annual") {
            updateChartsAnnual(json);
        } else if (selectedOption === "debt_periodicity") {
            updateChartsDebtPeriodicity(json);
        }
    }

    // Trigger on document ready
    handleDropdownChange();

    // Trigger on change event
    $("#myDropdown").change(handleDropdownChange);
}

// New function to apply highlighting based on scenario value
function applyHighlightingToScenario(scenarioValue) {
    // Find the radio button with the matching value
    const radioToHighlight = $(`input[name="scenarios"][value="${scenarioValue}"]`);
    
    if (radioToHighlight.length > 0) {
        // Apply highlighting to the row containing this radio button
        highlightSelectedRow(radioToHighlight[0]);
    }
}

function handleAjaxError(xhr, status, error) {
    try {
        const obj = JSON.parse(xhr.responseJSON.error);
        const array = Object.values(obj)[0];
        const firstElement = array[0];
        alert(firstElement.message);
        console.log(obj);
    } catch (e) {
        alert(xhr.responseJSON.error_type + " " + xhr.responseJSON.line_number + " " + xhr.responseJSON.message);
        console.log(xhr);
    }
}