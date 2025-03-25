$(document).ready(function() {
    // Initialize the application
    initializeApplication();
    makeGetRequest('Lender_base_case');  // Always use RadioScenario1

});


function initializeApplication() {

    set_up_sensitivities_form_submission_listeners();
    hide_construction_months_fields();
    hide_years_fields();

    $(document).on('submit', '#post-form', function(e) {
        handleFormSubmission(e, this);
    });
}

function handleFormSubmission(e, formElement) {
    e.preventDefault();

    var formData = $(formElement).serialize();

    var postSettings = {
        type: 'POST',
        url: "", // Add your URL here
        data: formData,
        success: handleSuccess,
        error: handleAjaxError
    };

    $.ajax(postSettings);
}

function makeGetRequest(value) {
    var getSettings = {
        url: '', // Add your URL here
        method: 'GET',
        data: {
            'scenario': value  // Always pass 'RadioScenario1'
        },
        success: function(json) {
            console.log(value);

            handleSuccess(json);
        },
        error: handleAjaxError
    };
    $.ajax(getSettings);
}

function handleSuccess(json) {
    console.log(json.df);
    console.log(json.tables);
    console.log(json.table_sensi_diff);


    build_computation_table(json);
    build_dashboard_tables(json);
    build_charts(json);
    update_sidebar_data(json);

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