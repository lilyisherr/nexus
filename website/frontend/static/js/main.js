

const API = {
    async get(endpoint) {
        const response = await fetch(endpoint);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    },

    async post(endpoint, data) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    },

    async delete(endpoint) {
        const response = await fetch(endpoint, { method: 'DELETE' });
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return response.json();
    },
};


const Utils = {
    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    },

    formatDate(dateStr) {
        if (!dateStr) return 'Never';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    formatTime(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    },

    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    },
};


const UI = {
    showAlert(message, type = 'info', duration = 5000) {
        const mainContent = document.querySelector('.main-content') || document.body;
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `<strong>${message}</strong>`;
        alert.style.position = 'fixed';
        alert.style.top = '100px';
        alert.style.right = '20px';
        alert.style.maxWidth = '400px';
        alert.style.animation = 'slideUp 0.3s ease';
        alert.style.zIndex = '999';
        
        document.body.appendChild(alert);
        
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.3s ease';
            setTimeout(() => alert.remove(), 300);
        }, duration);
    },

    showSuccess(message) {
        this.showAlert(message, 'success');
    },

    showError(message) {
        this.showAlert(message, 'error');
    },

    showWarning(message) {
        this.showAlert(message, 'warning');
    },

    showInfo(message) {
        this.showAlert(message, 'info');
    },

    showLoading() {
        const spinner = document.createElement('div');
        spinner.id = 'loading-spinner';
        spinner.className = 'spinner';
        spinner.style.position = 'fixed';
        spinner.style.top = '50%';
        spinner.style.left = '50%';
        spinner.style.transform = 'translate(-50%, -50%)';
        spinner.style.zIndex = '9999';
        document.body.appendChild(spinner);
    },

    hideLoading() {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) spinner.remove();
    },
};


const Modal = {
    open(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add('active');
    },

    close(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('active');
    },

    closeAll() {
        document.querySelectorAll('.modal.active').forEach(m => m.classList.remove('active'));
    },
};


document.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
});


document.addEventListener('DOMContentLoaded', function() {
    
    setupSidebarMenu();
    setupResponsiveMenu();
});

function setupSidebarMenu() {
    const menuLinks = document.querySelectorAll('.sidebar-menu a');
    menuLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (this.href === window.location.href) {
                menuLinks.forEach(l => l.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });
}

function setupResponsiveMenu() {
    
    const nav = document.querySelector('nav');
    if (window.innerWidth <= 768) {
        
    }
}


window.API = API;
window.Utils = Utils;
window.UI = UI;
window.Modal = Modal;
