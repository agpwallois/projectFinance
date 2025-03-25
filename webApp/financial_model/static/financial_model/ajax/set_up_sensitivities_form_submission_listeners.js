function set_up_sensitivities_form_submission_listeners() {
  
    // Select all the input fields that need to trigger the form submission

    // Function to submit the form
    function submitForm() {
        $("#post-form").submit();
    }
    
    // var inputFields = ['#id_sensi_production', '#id_sensi_opex', '#id_sensi_inflation'];

    // Loop through each input field
    // inputFields.forEach(function(inputField) {
        // Add an event listener to the input field
    //    $(inputField).on('input change', submitForm);
   // });

    // Add an event listener to the submit button
    $('#submit-button').on('click', submitForm);


    // Function to handle input change
    function handleInputChange(inputId, outputId) {
        var field = $('#' + inputId).val() + '%';
        $('#' + outputId).text(field);

        // Adding a listener to the input field
        $('#' + inputId).on('input', function() {
            var new_value = $(this).val();
            $('#' + outputId).text(new_value + '%');
        });
    }

    // Call the function for each input field
    handleInputChange('id_sensi_production', 'sensi_production');
    handleInputChange('id_sensi_opex', 'sensi_opex');
    handleInputChange('id_sensi_inflation', 'sensi_inflation');


    handleInputChange('id_sensi_production_sponsor', 'sponsor_sensi_production');
    handleInputChange('id_sensi_opex_sponsor', 'sponsor_sensi_opex');
    handleInputChange('id_sensi_inflation_sponsor', 'sponsor_sensi_inflation');


}