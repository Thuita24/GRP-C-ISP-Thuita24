// ============================================================================
// static/js/geographic.js - JavaScript for Geographic Model
// ============================================================================

// ============================================================================
// Geographic Model JavaScript
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    
    // Update rainfall zone dynamically
    const annualRainInput = document.querySelector('input[name="annual_rain"]');
    if (annualRainInput) {
        annualRainInput.addEventListener('input', function() {
            updateRainfallZone(this.value);
        });
        
        // Initialize on load
        if (annualRainInput.value) {
            updateRainfallZone(annualRainInput.value);
        }
    }
    
    // Update irrigation slider display
    const irrigationSlider = document.querySelector('input[name="irrigation"]');
    if (irrigationSlider) {
        irrigationSlider.addEventListener('input', function() {
            const output = document.getElementById('irrigation-value');
            if (output) {
                output.textContent = this.value + '%';
            }
        });
    }
    
    // Form validation
    const predictionForm = document.querySelector('.prediction-form');
    if (predictionForm) {
        predictionForm.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
            }
        });
    }
    
    // Animate results on load
    animateResults();
});

function updateRainfallZone(rainfall) {
    const zone = document.getElementById('rainfall-zone');
    if (!zone) return;
    
    const value = parseFloat(rainfall);
    
    if (isNaN(value)) {
        zone.textContent = '';
        return;
    }
    
    if (value < 500) {
        zone.textContent = '🏜️ Arid Zone';
        zone.className = 'text-danger fw-bold';
    } else if (value < 750) {
        zone.textContent = '🌾 Semi-arid Zone';
        zone.className = 'text-warning fw-bold';
    } else if (value < 1200) {
        zone.textContent = '🌱 Sub-humid Zone';
        zone.className = 'text-info fw-bold';
    } else {
        zone.textContent = '🌳 Humid Zone';
        zone.className = 'text-success fw-bold';
    }
}

function validateForm() {
    let isValid = true;
    const errors = [];
    
    // Temperature validation
    const temp = parseFloat(document.querySelector('input[name="temp_c"]')?.value);
    if (temp < -10 || temp > 50) {
        errors.push('Temperature must be between -10°C and 50°C');
        isValid = false;
    }
    
    // Dewpoint validation
    const dewpoint = parseFloat(document.querySelector('input[name="dewpoint_c"]')?.value);
    if (dewpoint < -20 || dewpoint > 40) {
        errors.push('Dewpoint must be between -20°C and 40°C');
        isValid = false;
    }
    
    // Precipitation validation
    const precip = parseFloat(document.querySelector('input[name="precip_mm"]')?.value);
    if (precip < 0 || precip > 500) {
        errors.push('Precipitation must be between 0 and 500 mm');
        isValid = false;
    }
    
    // Solar radiation validation
    const solar = parseFloat(document.querySelector('input[name="solar_rad"]')?.value);
    if (solar < 0 || solar > 35) {
        errors.push('Solar radiation must be between 0 and 35 MJ/m²');
        isValid = false;
    }
    
    // Annual rainfall validation
    const rainfall = parseFloat(document.querySelector('input[name="annual_rain"]')?.value);
    if (rainfall < 100 || rainfall > 5000) {
        errors.push('Annual rainfall must be between 100 and 5000 mm');
        isValid = false;
    }
    
    if (!isValid) {
        alert('Please fix the following errors:\\n\\n' + errors.join('\\n'));
    }
    
    return isValid;
}

function animateResults() {
    // Animate recommendation items
    const recommendations = document.querySelectorAll('.recommendation-item');
    recommendations.forEach((item, index) => {
        setTimeout(() => {
            item.style.opacity = '0';
            item.style.transform = 'translateX(-20px)';
            
            setTimeout(() => {
                item.style.transition = 'all 0.5s ease-out';
                item.style.opacity = '1';
                item.style.transform = 'translateX(0)';
            }, 50);
        }, index * 100);
    });
}

// Tooltip enhancement (Bootstrap not required)
document.querySelectorAll('.tooltip-icon').forEach(icon => {
    icon.addEventListener('mouseenter', function() {
        this.style.transform = 'scale(1.2)';
    });
    
    icon.addEventListener('mouseleave', function() {
        this.style.transform = 'scale(1)';
    });
});

// Print functionality
function printResults() {
    window.print();
}

// Export functionality (if needed)
function exportResults() {
    // Can be implemented to export as PDF or CSV
    alert('Export functionality coming soon!');
}

// (The following Python code should be removed from the JavaScript file)