function hide_years_fields() {
    // Get the input fields by ID prefixes
  var fields = {
    startDate: $('#id_start_construction'),
    endDate: $('#id_end_construction'),
    operatingLife: $('#id_operating_life'),
    liquidation: $('#id_liquidation'),
    yearLow: $('[id^="id_price_elec_low"]'),
    yearMed: $('[id^="id_price_elec_med"]'),
    yearHigh: $('[id^="id_price_elec_high"]'),
    yearLabel: $('[id^="elecPriceLabel"]')
  };

  updateYearFieldsVisibility();

  // Attach change event handlers to all relevant fields
  $.each(fields, function(key, field) {
    field.change(updateYearFieldsVisibility);
  });

  function updateYearFieldsVisibility() {
    var endDate = new Date(fields.endDate.val());
    var COD = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate() + 1);
    var yearB = COD.getFullYear();

    var operating_life_val = parseInt(fields.operatingLife.val());
    var liquidationField_val = parseInt(fields.liquidation.val());
    var liquidationField_val_y = Math.ceil(liquidationField_val / 12);
    var latest_date = new Date(COD.getFullYear() + operating_life_val + liquidationField_val_y, COD.getMonth(), COD.getDate());
    var yearE = latest_date.getFullYear();

    // Calculate the number of years
    var numYears = yearE - yearB + 1;

    // Show or hide the year fields based on the number of years
    $.each(fields, function(key, field) {
    if (key.startsWith('year')) {
      field.each(function(index) {
      var yearIndex = index + 1;
      if (yearIndex <= numYears) {
        $(this).show();
      } else {
        $(this).hide();
      }
      });
    }
    });
  }

}