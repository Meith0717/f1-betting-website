// Betting Form JavaScript
// Prevent duplicate driver selections in podium positions and improve form validation
document.addEventListener('DOMContentLoaded', function() {
  const positionSelects = [
    document.getElementById('position_1'),
    document.getElementById('position_2'),
    document.getElementById('position_3')
  ];
  
  const fastestLapSelect = document.getElementById('fastest_lap');
  const form = document.querySelector('.bet-form-inner');

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
        
        // Update form validation
        validateForm();
      });
    }
  });
  
  // Fastest lap selection
  if (fastestLapSelect) {
    fastestLapSelect.addEventListener('change', validateForm);
  }
  
  // Form validation function
  function validateForm() {
    let isValid = true;
    
    // Check if all required fields are filled
    positionSelects.forEach(select => {
      if (select && !select.value) {
        isValid = false;
        select.classList.add('invalid');
      } else if (select) {
        select.classList.remove('invalid');
      }
    });
    
    if (fastestLapSelect && !fastestLapSelect.value) {
      isValid = false;
      fastestLapSelect.classList.add('invalid');
    } else if (fastestLapSelect) {
      fastestLapSelect.classList.remove('invalid');
    }
    
    // Update submit button state
    const submitButton = form ? form.querySelector('button[type="submit"]') : null;
    if (submitButton) {
      submitButton.disabled = !isValid;
      if (isValid) {
        submitButton.classList.remove('disabled');
      } else {
        submitButton.classList.add('disabled');
      }
    }
    
    return isValid;
  }
  
  // Initial validation
  if (form) {
    validateForm();
    
    // Add form submission handler
    form.addEventListener('submit', function(e) {
      if (!validateForm()) {
        e.preventDefault();
        // Show error message
        const errorMessage = document.createElement('div');
        errorMessage.className = 'flash-message flash-error';
        errorMessage.textContent = 'Please select all drivers before submitting.';
        
        // Insert error message at the top of the form
        if (form.parentNode) {
          form.parentNode.insertBefore(errorMessage, form);
          
          // Remove error message after 3 seconds
          setTimeout(() => {
            errorMessage.remove();
          }, 3000);
        }
      }
    });
  }
  
  // Add visual feedback for invalid fields
  const style = document.createElement('style');
  style.textContent = `
    .invalid {
      border-color: var(--primary) !important;
      box-shadow: 0 0 0 2px rgba(225, 6, 0, 0.3) !important;
    }
    
    .disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  `;
  document.head.appendChild(style);
});