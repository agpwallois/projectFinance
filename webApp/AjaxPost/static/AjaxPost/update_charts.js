
	
$(document).ready(function(){
	setCalculationTypeAndSubmit('none');
	$("#RadioScenario1").prop('checked', true);
});


// Mapping of radio button IDs to their corresponding values
var radioValueMap = {
	'RadioScenario1': 'none',
	'RadioScenario2': 'sensi-p50',
	'RadioScenario3': 'sensi-production',
	'RadioScenario4': 'sensi-inflation',
	'RadioScenario5': 'sensi-opex',

};

// Generic event handler for radio buttons
$("[id^='RadioScenario']").on('change', function() {
	if ($(this).prop('checked')) {
		var value = radioValueMap[this.id];
		setCalculationTypeAndSubmit(value);
	}
});

// Helper function to set the value and submit the form
function setCalculationTypeAndSubmit(value) {
	$("#id_calculation_type").val(value);
	$("#post-form").submit();
}

