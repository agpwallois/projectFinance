
	
    $(document).ready(function() {
        // Initialize the application
        initializeApplication();

        


        // Event listener for radio button changes
        $("[id^='RadioScenario']").on('change', function() {
            var value = this.id;
            makeGetRequest(value);
        });

        $('#RadioScenario1').prop('checked', true).trigger('change');
        
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


        var scenarioValue = $("[name='flexRadioDefault']:checked").val();

        var formData = $(formElement).serialize();
        formData += '&scenario=' + encodeURIComponent(scenarioValue);

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
                'scenario': value
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
        console.log(json.charts_data_constr);
        console.log(json.df_eoy);
        console.log(json.df_annual);

        build_computation_table(json);
        build_dashboard_tables(json);
        build_charts(json);
        update_sidebar_data(json);

        function handleDropdownChange() {
            var selectedOption = $("#myDropdown").val();
            console.log("Dropdown changed:", selectedOption);

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


