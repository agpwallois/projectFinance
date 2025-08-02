function hide_sidebar_solar_or_wind_fields() {
  // Get the technology field value
  var technology = $('#id_technology').val();
  
  // Define the fields to hide for each project type
  var solarFields = ['#solar_panels_capacity', '#solar_panels_degradation'];
  var windFields = ['#wind_turbine_number', '#wind_turbine_capacity', '#wind_project_capacity'];
  
  // First, show all fields (reset state)
  solarFields.forEach(function(field) {
    $(field).show();
  });
  windFields.forEach(function(field) {
    $(field).show();
  });
  
  // Hide fields based on project type
  if (technology) {
    if (technology.toLowerCase().includes('solar')) {
      // If it's a solar project, hide wind fields
      windFields.forEach(function(field) {
        $(field).hide();
      });
    } else if (technology.toLowerCase().includes('wind')) {
      // If it's a wind project, hide solar fields
      solarFields.forEach(function(field) {
        $(field).hide();
      });
    }
  }
}