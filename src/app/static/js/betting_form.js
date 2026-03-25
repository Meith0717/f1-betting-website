// Betting Form JavaScript
// Prevent duplicate driver selections in podium positions
document.addEventListener('DOMContentLoaded', function() {
  const positionSelects = [
    document.getElementById('position_1'),
    document.getElementById('position_2'),
    document.getElementById('position_3')
  ];
  
  const fastestLapSelect = document.getElementById('fastest_lap');

  // Prevent duplicate selections in podium positions (1st, 2nd, 3rd)
  positionSelects.forEach((select, index) => {
    if (select) {
      select.addEventListener('change', function() {
        const selectedValue = this.value;
        
        // Disable this option in other podium position selects
        positionSelects.forEach((otherSelect, otherIndex) => {
          if (otherIndex !== index && otherSelect) {
            const option = otherSelect.querySelector(`option[value="${selectedValue}"]`);
            if (option) {
              option.disabled = true;
            }
            
            // Re-enable previously selected option if it was changed
            if (otherSelect.value === selectedValue) {
              otherSelect.value = '';
            }
          }
        });
        
        // Re-enable previously selected options when changing selection
        const previousValue = this.dataset.previousValue;
        if (previousValue) {
          positionSelects.forEach((otherSelect, otherIndex) => {
            if (otherIndex !== index && otherSelect) {
              const option = otherSelect.querySelector(`option[value="${previousValue}"]`);
              if (option) {
                option.disabled = false;
              }
            }
          });
        }
        
        // Store current value for next change
        this.dataset.previousValue = selectedValue;
      });
    }
  });
  
  // Fastest lap can be any driver (including podium drivers)
  // No restrictions applied to fastest lap selection
});