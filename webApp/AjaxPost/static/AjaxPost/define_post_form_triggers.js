    $(document).ready(function() {
        // Select all the input fields that need to trigger the form submission
        var inputFields = ['#id_sensi_production', '#id_sensi_opex', '#id_sensi_inflation'];

        // Function to submit the form
        function submitForm() {
            $("#post-form").submit();
        }

        // Loop through each input field
        inputFields.forEach(function(inputField) {
            // Add an event listener to the input field
            $(inputField).on('input change', submitForm);
        });

        // Add an event listener to the submit button
        $('#submit-button').on('click', submitForm);
    });