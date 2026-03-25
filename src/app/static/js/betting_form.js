// Betting Form JavaScript
// Prevent duplicate driver selections
document.addEventListener('DOMContentLoaded', function() {
  const positionSelects = [
    document.getElementById('position_1'),
    document.getElementById('position_2'),
    document.getElementById('position_3'),
    document.getElementById('fastest_lap')
  ];

  positionSelects.forEach((select, index) => {
    if (select) {
      select.addEventListener('change', function() {
        const selectedValue = this.value;
        
        // Disable this option in other selects
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
});