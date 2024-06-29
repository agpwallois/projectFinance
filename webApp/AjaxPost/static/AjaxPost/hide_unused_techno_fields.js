    const myField = document.getElementById("project_name");

    // Grouping related elements by their IDs
    const windElements = ['wind_turbine_capacity', 'wind_turbine_number', 'wind_project_capacity', 'wind_devtax_cost', 'rotor_diameter'];
    const solarElements = ['solar_panels_capacity', 'solar_panels_degradation', 'solar_panels_surface', 'solar_devtax_cost', 'solar_arctax_base', 'solar_arctax_cost', 'solar_arctax_title'];

    function toggleDivVisibility() {
        // Helper function to change visibility
        const setVisibility = (ids, visible) => ids.forEach(id => {
            const elem = document.getElementById(id);
            if (visible) {
                elem.style.visibility = 'visible';
                elem.style.position = 'static';
            } else {
                elem.style.visibility = 'hidden';
                elem.style.position = 'absolute';
            }
        });

        const isSolar = myField.textContent.startsWith("Solar");
        setVisibility(windElements, !isSolar);
        setVisibility(solarElements, isSolar);
    }

    toggleDivVisibility();

    myField.addEventListener('change', toggleDivVisibility);