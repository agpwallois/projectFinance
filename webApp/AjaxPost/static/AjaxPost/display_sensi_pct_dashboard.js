$(document).ready(function() {

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

});