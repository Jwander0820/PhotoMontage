document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('image_file');
    const fileNameDisplay = document.getElementById('file-name');
    const form = document.getElementById('montage-form');
    const generateBtn = document.getElementById('generate-btn');
    const resultImg = document.getElementById('result-img');
    const emptyMessage = document.querySelector('.empty-message');
    const overlay = document.getElementById('loading-overlay');
    const predefinedSelect = document.getElementById('predefined_img');
    const updateDbBtn = document.getElementById('update-db-btn');
    const dbStatus = document.getElementById('db-status');
    const elementDirInput = document.getElementById('element_dir');

    // Load previously saved directory
    const savedDir = localStorage.getItem('last_element_dir');
    if (savedDir) {
        elementDirInput.value = savedDir;
    }
    
    const viewControls = document.getElementById('view-controls');
    const downloadBtn = document.getElementById('download-btn');
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const zoomResetBtn = document.getElementById('zoom-reset');
    const previewArea = document.getElementById('preview-area');

    // View State
    let currentScale = 1;
    let translateX = 0;
    let translateY = 0;
    let isDragging = false;
    let startX, startY;

    function updateTransform() {
        if (!resultImg.src) return;
        resultImg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${currentScale})`;
    }

    function resetView() {
        currentScale = 1;
        translateX = 0;
        translateY = 0;
        updateTransform();
    }

    zoomInBtn.addEventListener('click', () => {
        currentScale *= 1.2;
        updateTransform();
    });

    zoomOutBtn.addEventListener('click', () => {
        currentScale /= 1.2;
        updateTransform();
    });

    zoomResetBtn.addEventListener('click', resetView);

    previewArea.addEventListener('wheel', (e) => {
        if (resultImg.style.display !== 'block') return;
        e.preventDefault(); // Prevent page scrolling
        
        const zoomFactor = 1.1;
        if (e.deltaY < 0) {
            currentScale *= zoomFactor;
        } else {
            currentScale /= zoomFactor;
        }
        
        currentScale = Math.max(0.1, Math.min(currentScale, 20)); // Limit scale 0.1x to 20x
        updateTransform();
    });

    // Block native image drag entirely
    resultImg.addEventListener('dragstart', (e) => e.preventDefault());

    previewArea.addEventListener('mousedown', (e) => {
        if (resultImg.style.display !== 'block') return;
        if (e.button !== 0) return; // Only left click
        
        e.preventDefault(); // Prevent text selection & native drag for all targets
        
        isDragging = true;
        startX = e.clientX - translateX;
        startY = e.clientY - translateY;
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        translateX = e.clientX - startX;
        translateY = e.clientY - startY;
        updateTransform();
    });

    window.addEventListener('mouseup', () => {
        isDragging = false;
    });



    updateDbBtn.addEventListener('click', async () => {
        const elementDir = elementDirInput.value.trim();
        if (!elementDir) {
            alert('Please specify a local folder path.');
            return;
        }
        
        localStorage.setItem('last_element_dir', elementDir);

        updateDbBtn.classList.add('is-loading');
        updateDbBtn.disabled = true;
        dbStatus.textContent = 'Scanning images...';
        dbStatus.className = 'db-status loading';

        try {
            const formData = new FormData();
            formData.append('element_dir', elementDir);

            const response = await fetch('/api/update_elements', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                dbStatus.textContent = `Success: ${data.count} images loaded.`;
                dbStatus.className = 'db-status success';
            } else {
                dbStatus.textContent = `Error: ${data.error}`;
                dbStatus.className = 'db-status error';
            }
        } catch (err) {
            console.error('Update DB error:', err);
            dbStatus.textContent = 'Connection failed.';
            dbStatus.className = 'db-status error';
        } finally {
            updateDbBtn.classList.remove('is-loading');
            updateDbBtn.disabled = false;
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileNameDisplay.textContent = e.target.files[0].name;
            predefinedSelect.value = ""; // Clear predefined if file selected
        } else {
            fileNameDisplay.textContent = 'No file chosen';
        }
    });

    predefinedSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            fileInput.value = ""; // Clear file input if predefined selected
            fileNameDisplay.textContent = 'No file chosen';
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Validate
        if (fileInput.files.length === 0 && !predefinedSelect.value) {
            alert('Please upload an image or select a predefined one.');
            return;
        }
        
        // Save element dir on submit as well
        localStorage.setItem('last_element_dir', elementDirInput.value.trim());

        const formData = new FormData(form);

        // UI updates for loading state
        generateBtn.classList.add('is-loading');
        generateBtn.disabled = true;
        overlay.classList.add('active');

        try {
            const response = await fetch('/api/montage', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // Bust cache with timestamp
                resultImg.src = data.result_url + '?t=' + new Date().getTime();
                resultImg.style.display = 'block';
                emptyMessage.style.display = 'none';
                viewControls.style.display = 'flex';
                
                // Configure download link
                downloadBtn.href = data.result_url;
                const filenameMatch = data.result_url.split('/').pop();
                downloadBtn.download = filenameMatch || 'montage.png';
                
                resetView();
            } else {
                alert('Error generating montage: ' + (data.error || 'Unknown error'));
            }
        } catch (err) {
            console.error('Fetch error:', err);
            alert('Failed to connect to the server.');
        } finally {
            generateBtn.classList.remove('is-loading');
            generateBtn.disabled = false;
            overlay.classList.remove('active');
        }
    });
});
