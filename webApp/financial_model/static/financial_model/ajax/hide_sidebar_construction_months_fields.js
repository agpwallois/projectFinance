function hide_sidebar_construction_months_fields() {
  // Get the start and end date fields
  var startDateField = $('#id_start_construction');
  var endDateField = $('#id_end_construction');
  // Get the form fields for each month (e.g., costs_m1, costs_m2, costs_m3, etc.)
  var monthFields = $('div[id^="costs_m"]');

  monthFields.hide();

  updateMonthFieldsVisibility()
   
   // Show or hide the month fields based on the selected start and end dates
  startDateField.change(function() {
    updateMonthFieldsVisibility();
  });

  endDateField.change(function() {
    updateMonthFieldsVisibility();
  });

  function updateMonthFieldsVisibility() {
    var startDate = new Date(startDateField.val());
    var endDate = new Date(endDateField.val());

    numMonths = (endDate.getFullYear() - startDate.getFullYear()) * 12;
    numMonths -= startDate.getMonth();
    numMonths += endDate.getMonth();


    // Show or hide the month fields based on the number of months
    monthFields.each(function(index) {
    var monthIndex = index;
    if (monthIndex <= numMonths) {
      $(this).show();
    } else {
      $(this).hide();
    }
    });
  }

}