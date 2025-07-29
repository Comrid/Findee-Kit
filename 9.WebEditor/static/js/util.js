// Toast notification function
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {toast.remove();}, 3000);
}

// Show welcome toast
function showWelcomeToast() {
    setTimeout(() => {showToast('Welcome to Findee Python Web Editor!', 'success');}, 100);
}

// Export functions for global use
window.showToast = showToast;
window.showWelcomeToast = showWelcomeToast;