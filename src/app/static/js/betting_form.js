// Betting Form Driver Selection Logic
// Prevents duplicate driver selection in podium positions

document.addEventListener('DOMContentLoaded', function() {
  // Get all select elements
  const selects = document.querySelectorAll('.driver-select');
  const originalOptions = {};
  const podiumSelects = ['position_1', 'position_2', 'position_3'];

  // Store original options for each select
  selects.forEach((select) => {
    originalOptions[select.id] = Array.from(select.options).map(
      (option) => option.value
    );
  });

  // Add event listeners to each select
  selects.forEach((select) => {
    select.addEventListener('change', function() {
      const selectedValue = this.value;

      // Disable selected driver in other dropdowns
      selects.forEach((otherSelect) => {
        if (otherSelect.id !== this.id) {
          const optionToDisable = otherSelect.querySelector(
            `option[value="${selectedValue}"]`
          );
          if (optionToDisable) {
            // Fastest lap can be the same as podium drivers
            if (this.id === 'fastest_lap' || otherSelect.id === 'fastest_lap') {
              optionToDisable.disabled = false;
            } else {
              optionToDisable.disabled = true;
            }
          }

          // Re-enable other options that were previously disabled
          originalOptions[otherSelect.id].forEach((value) => {
            const option = otherSelect.querySelector(
              `option[value="${value}"]`
            );
            if (option && value !== selectedValue) {
              // Only enable if not selected in any other dropdown
              const isSelectedElsewhere = Array.from(selects).some(
                (s) => s.id !== otherSelect.id && s.value === value
              );
              if (!isSelectedElsewhere) {
                option.disabled = false;
              }
            }
          });
        }
      });
    });
  });
});