// Simple toggle function for race cards
function toggleRaceCard(raceId) {
    const raceCard = document.querySelector(`.race-card[data-race-id="${raceId}"]`);
    if (raceCard) {
        // Check if race is canceled - prevent expansion
        if (raceCard.getAttribute('data-canceled') === 'true') {
            return; // Don't allow expansion for canceled races
        }
        
        raceCard.classList.toggle('expanded');
        const icon = raceCard.querySelector('.expand-icon');
        if (icon) {
            icon.textContent = raceCard.classList.contains('expanded') ? '▲' : '▼';
        }
    }
}

// Add click handlers when page loads
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.race-header, .expand-icon').forEach(element => {
        element.addEventListener('click', function() {
            const raceCard = this.closest('.race-card');
            if (raceCard) {
                const raceId = raceCard.getAttribute('data-race-id');
                toggleRaceCard(raceId);
            }
        });
    });
});