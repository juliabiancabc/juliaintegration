document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag for AJAX requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    // Auto-hide flash messages after 5 seconds
    const flashBanners = document.querySelectorAll('.flash-banner');
    flashBanners.forEach(banner => {
        setTimeout(() => {
            banner.style.display = 'none';
        }, 5000);
    });
    
    // character counter for caption
    const captionInput = document.querySelector('input[name="caption"]');
    if (captionInput) {
        const maxLength = 120;
        
        // create counter element
        const counter = document.createElement('small');
        counter.className = 'text-muted d-block mt-1';
        counter.id = 'caption-counter';
        
        // insert after the input group
        const inputGroup = captionInput.closest('.input-group');
        if (inputGroup && inputGroup.parentElement) {
            inputGroup.parentElement.appendChild(counter);
        }
        
        function updateCounter() {
            const remaining = maxLength - captionInput.value.length;
            counter.textContent = `${captionInput.value.length}/${maxLength} characters`;
            
            if (remaining < 20) {
                counter.className = 'text-warning d-block mt-1';
            } else {
                counter.className = 'text-muted d-block mt-1';
            }
        }
        
        captionInput.addEventListener('input', updateCounter);
        updateCounter();
    }
    
    // confirm before delete
    const deleteForms = document.querySelectorAll('form[action*="/delete"]');
    deleteForms.forEach(form => {
        if (!form.hasAttribute('onsubmit')) {
            form.addEventListener('submit', function(e) {
                if (!confirm('Are you sure you want to delete this story?')) {
                    e.preventDefault();
                }
            });
        }
    });
    
    // media thumbnails click handler (for view page)
    const mediaThumbnails = document.querySelectorAll('.media-thumbnail');
    const mainMedia = document.querySelector('.story-media-large img');
    
    if (mediaThumbnails.length > 0 && mainMedia) {
        mediaThumbnails.forEach(thumb => {
            thumb.addEventListener('click', function() {
                // update active state
                mediaThumbnails.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // update main image
                const thumbImg = this.querySelector('img');
                if (thumbImg) {
                    mainMedia.src = thumbImg.src;
                }
            });
        });
    }
    
    // drag and drop for media upload
    const mediaUploadArea = document.getElementById('mediaUploadArea');
    const mediaInput = document.getElementById('mediaInput');
    
    if (mediaUploadArea && mediaInput) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            mediaUploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            mediaUploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            mediaUploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            mediaUploadArea.style.borderColor = '#6366f1';
            mediaUploadArea.style.backgroundColor = '#e0e7ff';
        }
        
        function unhighlight() {
            mediaUploadArea.style.borderColor = '#e5e7eb';
            mediaUploadArea.style.backgroundColor = '#f3f4f6';
        }
        
        mediaUploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            // create a new FileList-like object and assign to input
            const dataTransfer = new DataTransfer();
            Array.from(files).forEach(file => {
                if (file.type.startsWith('image/') || file.type.startsWith('video/')) {
                    dataTransfer.items.add(file);
                }
            });
            
            mediaInput.files = dataTransfer.files;
            
            // trigger change event to update preview
            const event = new Event('change', { bubbles: true });
            mediaInput.dispatchEvent(event);
        }
    }
    
    // Like button AJAX (optional enhancement)
    const likeForms = document.querySelectorAll('form[action*="/like"]');
    likeForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            fetch(this.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // update the like count in the UI
                    const countSpan = this.querySelector('span');
                    if (countSpan) {
                        const currentCount = parseInt(countSpan.textContent) || 0;
                        countSpan.textContent = currentCount + 1;
                    }
                    
                    // add visual feedback
                    const icon = this.querySelector('i');
                    if (icon) {
                        icon.classList.remove('bi-heart');
                        icon.classList.add('bi-heart-fill');
                        icon.style.color = '#ef4444';
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // fallback to normal form submission
                this.submit();
            });
        });
    });
});

// utility function to format dates
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// utility function to format time ago
function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    const intervals = {
        year: 31536000,
        month: 2592000,
        week: 604800,
        day: 86400,
        hour: 3600,
        minute: 60
    };
    
    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
        const interval = Math.floor(seconds / secondsInUnit);
        if (interval >= 1) {
            return interval === 1 ? `1 ${unit} ago` : `${interval} ${unit}s ago`;
        }
    }
    
    return 'Just now';
}
