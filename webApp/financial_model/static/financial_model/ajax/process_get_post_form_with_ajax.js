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
    hide_sidebar_construction_months_fields();
    hide_sidebar_mkt_prices_years_fields();
    hide_sidebar_solar_or_wind_fields();

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

    console.log('Starting POST request');
    console.time('POST request total time');

    // Show loader before making the request
    showLoader();

    var formData = $(formElement).serialize();
    
    // Add the current selected scenario to the form data
    formData += '&scenario=' + encodeURIComponent(currentSelectedScenario);

    var postSettings = {
        type: 'POST',
        url: "", // Add your URL here
        data: formData,
        beforeSend: function() {
            console.time('Server POST response time');
        },
        success: function(json) {
            console.timeEnd('Server POST response time');
            // Hide loader on success
            hideLoader();
            handleSuccess(json);
            console.timeEnd('POST request total time');
        },
        error: function(xhr, status, error) {
            console.timeEnd('Server POST response time');
            // Hide loader on error
            hideLoader();
            handleAjaxError(xhr, status, error);
            console.timeEnd('POST request total time');
        }
    };

    $.ajax(postSettings);
}

function makeGetRequest(value) {
    console.log('Starting GET request for scenario:', value);
    console.time('GET request total time');



    var getSettings = {
        url: '', // Add your URL here
        method: 'GET',
        data: {
            'scenario': value 
        },
        beforeSend: function() {
            console.time('Server response time');
        },
        success: function(json) {
            console.timeEnd('Server response time');

            console.log(json);

            // Hide loader on success
            hideLoader();
            handleSuccess(json);
            console.timeEnd('GET request total time');
        },
        error: function(xhr, status, error) {
            console.timeEnd('Server response time');
            // Hide loader on error
            hideLoader();
            handleAjaxError(xhr, status, error);
            console.timeEnd('GET request total time');
        }
    };
    $.ajax(getSettings);
}

function handleSuccess(json) {
    
    // Build dashboard cards first
    console.time('build_dashboard_cards');
    build_dashboard_cards(json);
    console.timeEnd('build_dashboard_cards');

    // build_computation_table(json);
    
    // Build financial statements
    console.time('build_fs_financial_statements');
    build_fs_financial_statements(json);
    console.timeEnd('build_fs_financial_statements');
    
    console.time('build_fs_financing_plan');
    build_fs_financing_plan(json);
    console.timeEnd('build_fs_financing_plan');
    
    console.time('build_fs_balance_sheet');
    build_fs_balance_sheet(json);
    console.timeEnd('build_fs_balance_sheet');

    console.time('build_fs_debt_schedule');
    build_fs_debt_schedule(json);
    console.timeEnd('build_fs_debt_schedule');

    // Update dashboard and sidebar
    console.time('update_dashboard_and_sidebar_cards');
    update_dashboard_and_sidebar_cards(json);
    console.timeEnd('update_dashboard_and_sidebar_cards');

    // BUILD CHARTS - This is the critical section
    console.time('build_charts_total');
    
    // First, build the initial charts (construction phase charts)
    console.time('build_charts');
    build_charts(json);
    console.timeEnd('build_charts');
    
    // Set up the dropdown handler BEFORE triggering it
    function handleDropdownChange() {
        var selectedOption = $("#myDropdown").val();

        if (selectedOption === "annual") {
            updateChartsAnnual(json);
        } else if (selectedOption === "debt_periodicity") {
            updateChartsDebtPeriodicity(json);
        }
    }

    // Remove any existing change handlers to avoid duplicates
    $("#myDropdown").off('change');
    
    // Set up the change event handler
    $("#myDropdown").on('change', handleDropdownChange);
    
    // Trigger the initial update based on current dropdown value
    // Use setTimeout to ensure build_charts completes first
    setTimeout(() => {
        handleDropdownChange();
    }, 0);
    
    console.timeEnd('build_charts_total');

    // Apply highlighting
    console.time('applyHighlightingToScenario');
    applyHighlightingToScenario(currentSelectedScenario);
    console.timeEnd('applyHighlightingToScenario');
    

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
    console.log('Error response:', xhr.responseJSON);
    
    if (xhr.responseJSON) {
        // Check if it's a form validation error with the new clean format
        if (xhr.responseJSON.validation_errors && xhr.responseJSON.validation_errors.length > 0) {
            const errorMessages = xhr.responseJSON.validation_errors;
            alert('Form validation error:\n' + errorMessages.join('\n'));
        } 
        // Check if it's a form validation error with the old HTML format
        else if (xhr.responseJSON.error && xhr.responseJSON.error.includes('Form validation failed:')) {
            // Extract the error message from the HTML
            const errorHtml = xhr.responseJSON.error;
            const parser = new DOMParser();
            const doc = parser.parseFromString(errorHtml, 'text/html');
            
            // Try to find error messages in the HTML
            const errorMessages = [];
            const errorListItems = doc.querySelectorAll('.errorlist li');
            
            errorListItems.forEach(item => {
                // Skip list items that contain nested lists (like __all__)
                if (!item.querySelector('ul')) {
                    const message = item.textContent.trim();
                    if (message && message !== '__all__') {
                        errorMessages.push(message);
                    }
                }
            });
            
            if (errorMessages.length > 0) {
                alert('Form validation error:\n' + errorMessages.join('\n'));
            } else {
                // Fallback to showing the raw error if we can't parse it
                alert('Form validation failed. Please check your input.');
            }
        } 
        // Handle other types of errors
        else if (xhr.responseJSON.error) {
            try {
                const obj = JSON.parse(xhr.responseJSON.error);
                const array = Object.values(obj)[0];
                const firstElement = array[0];
                alert(firstElement.message);
                console.log(obj);
            } catch (e) {
                // Fallback error display
                alert('Error: ' + xhr.responseJSON.error);
            }
        } 
        // Handle structured error responses
        else if (xhr.responseJSON.error_type) {
            const errorParts = [];
            if (xhr.responseJSON.error_type) errorParts.push(xhr.responseJSON.error_type);
            if (xhr.responseJSON.line_number) errorParts.push('Line ' + xhr.responseJSON.line_number);
            if (xhr.responseJSON.message) errorParts.push(xhr.responseJSON.message);
            
            alert(errorParts.join(' - '));
        } 
        else {
            // Generic error with response
            alert('An error occurred: ' + JSON.stringify(xhr.responseJSON));
        }
    } else {
        // Generic error fallback when no response JSON
        alert('An error occurred while processing your request.');
    }
    
    console.log('Full error details:', xhr);
}