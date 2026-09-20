document.addEventListener('DOMContentLoaded', () => {
    const defaults = window.MONTAGE_DEFAULTS || { maxEdge: 10000, maxMegapixels: 100 };
    const form = document.getElementById('montage-form');
    const fileInput = document.getElementById('image_file');
    const fileNameDisplay = document.getElementById('file-name');
    const predefinedSelect = document.getElementById('predefined_img');
    const elementDirInput = document.getElementById('element_dir');
    const samplingInput = document.getElementById('org_img_pixel');
    const tileInput = document.getElementById('element_img_pixel');
    const maxEdgeInput = document.getElementById('max_output_edge');
    const maxMegapixelsInput = document.getElementById('max_output_megapixels');
    const allowLargeInput = document.getElementById('allow_large_output');
    const largeOutputConfirm = document.getElementById('large-output-confirm');
    const generateBtn = document.getElementById('generate-btn');
    const updateDbBtn = document.getElementById('update-db-btn');
    const dbStatus = document.getElementById('db-status');
    const overlay = document.getElementById('loading-overlay');
    const resultImg = document.getElementById('result-img');
    const emptyMessage = document.querySelector('.empty-message');
    const viewControls = document.getElementById('view-controls');
    const downloadBtn = document.getElementById('download-btn');
    const resultStats = document.getElementById('result-stats');
    const previewArea = document.getElementById('preview-area');
    const estimateDimensions = document.getElementById('estimate-dimensions');
    const estimateState = document.getElementById('estimate-state');
    const estimateMeta = document.getElementById('estimate-meta');
    const estimateWarning = document.getElementById('estimate-warning');
    const readoutScaleFill = document.getElementById('readout-scale-fill');

    let sourceDimensions = null;
    let sourceObjectUrl = null;
    let sourceRevision = 0;
    let requestInProgress = false;
    let currentScale = 1;
    let translateX = 0;
    let translateY = 0;
    let isDragging = false;
    let startX = 0;
    let startY = 0;

    try {
        const savedDir = localStorage.getItem('last_element_dir');
        if (savedDir) elementDirInput.value = savedDir;
    } catch {
        // Remembering a directory is optional when browser storage is blocked.
    }

    function rememberDirectory(directory) {
        try {
            localStorage.setItem('last_element_dir', directory);
        } catch {
            // Storage policy or quota errors must not prevent generation.
        }
    }

    function setRequestInProgress(active) {
        requestInProgress = active;
        for (const control of form.querySelectorAll('input, select, button')) {
            control.disabled = active;
        }
        form.setAttribute('aria-busy', String(active));
    }

    function positiveInteger(input) {
        const value = Number(input.value);
        return Number.isSafeInteger(value) && value > 0 ? value : null;
    }

    function updateLargeOutputConfirmation() {
        const maxEdge = positiveInteger(maxEdgeInput) || 0;
        const maxMegapixels = positiveInteger(maxMegapixelsInput) || 0;
        const raised = maxEdge > defaults.maxEdge || maxMegapixels > defaults.maxMegapixels;
        largeOutputConfirm.hidden = !raised;
        if (!raised) allowLargeInput.checked = false;
        document.querySelector('.summary-value').textContent = `${maxEdge || '—'} px / ${maxMegapixels || '—'} MP`;
        return raised;
    }

    function calculateOutputPlan(width, height) {
        const requestedSampling = positiveInteger(samplingInput);
        const requestedTile = positiveInteger(tileInput);
        const maxEdge = positiveInteger(maxEdgeInput);
        const maxMegapixels = positiveInteger(maxMegapixelsInput);
        if (![requestedSampling, requestedTile, maxEdge, maxMegapixels].every(Boolean)) return null;

        const maxPixels = maxMegapixels * 1000000;
        if (!Number.isSafeInteger(maxPixels)) return null;
        let sampling = Math.max(
            requestedSampling,
            Math.ceil(width / maxEdge),
            Math.ceil(height / maxEdge),
            Math.ceil(Math.sqrt((width * height) / maxPixels))
        );
        let columns;
        let rows;
        do {
            columns = Math.ceil(width / sampling);
            rows = Math.ceil(height / sampling);
            if (columns <= maxEdge && rows <= maxEdge && columns * rows <= maxPixels) break;
            sampling += 1;
        } while (true);

        const cells = columns * rows;
        const tile = Math.min(
            requestedTile,
            Math.floor(maxEdge / columns),
            Math.floor(maxEdge / rows),
            Math.floor(Math.sqrt(maxPixels / cells))
        );
        if (tile < 1) return null;

        const outputWidth = columns * tile;
        const outputHeight = rows * tile;
        const pixels = outputWidth * outputHeight;
        const rawMemory = pixels * 3 / (1024 ** 2);
        return {
            sampling,
            tile,
            columns,
            rows,
            outputWidth,
            outputHeight,
            pixels,
            rawMemory,
            peakMemory: rawMemory * 2.15,
            maxPixels,
            wasLimited: sampling !== requestedSampling || tile !== requestedTile
        };
    }

    function showEstimate(plan, authoritative = false) {
        if (!plan) {
            estimateDimensions.textContent = '— × —';
            estimateState.textContent = sourceDimensions ? '參數不完整' : '等待圖片';
            estimateMeta.textContent = sourceDimensions
                ? '所有尺寸與上限都必須大於 0。'
                : '選取圖片後會在這裡估算格數與記憶體。';
            estimateWarning.hidden = true;
            readoutScaleFill.style.width = '0%';
            return;
        }
        estimateDimensions.textContent = `${plan.outputWidth.toLocaleString()} × ${plan.outputHeight.toLocaleString()}`;
        estimateState.textContent = authoritative ? '實際輸出' : '即時估算';
        estimateMeta.textContent = `${plan.columns} × ${plan.rows} 格 · 原始緩衝 ${plan.rawMemory.toFixed(1)} MiB · 儲存尖峰約 ${plan.peakMemory.toFixed(1)} MiB`;
        estimateWarning.hidden = !plan.wasLimited;
        estimateWarning.textContent = plan.wasLimited
            ? `已保護輸出：取樣調整為 ${plan.sampling}px，素材格調整為 ${plan.tile}px。`
            : '';
        readoutScaleFill.style.width = `${Math.min(100, (plan.pixels / plan.maxPixels) * 100).toFixed(1)}%`;
    }

    function refreshEstimate() {
        updateLargeOutputConfirmation();
        showEstimate(sourceDimensions
            ? calculateOutputPlan(sourceDimensions.width, sourceDimensions.height)
            : null);
    }

    function clearSourceDimensions() {
        sourceRevision += 1;
        sourceDimensions = null;
        if (sourceObjectUrl) URL.revokeObjectURL(sourceObjectUrl);
        sourceObjectUrl = null;
        refreshEstimate();
    }

    function loadDimensions(url) {
        const revision = sourceRevision;
        const probe = new Image();
        probe.onload = () => {
            if (revision !== sourceRevision) return;
            sourceDimensions = { width: probe.naturalWidth, height: probe.naturalHeight };
            if (sourceObjectUrl === url) {
                URL.revokeObjectURL(url);
                sourceObjectUrl = null;
            }
            refreshEstimate();
        };
        probe.onerror = () => {
            if (revision !== sourceRevision) return;
            sourceDimensions = null;
            if (sourceObjectUrl === url) {
                URL.revokeObjectURL(url);
                sourceObjectUrl = null;
            }
            showEstimate(null);
            estimateState.textContent = '無法預覽';
            estimateMeta.textContent = '瀏覽器無法讀取圖片尺寸，仍可嘗試生成，由伺服器確認格式與輸出限制。';
        };
        probe.src = url;
    }

    [samplingInput, tileInput, maxEdgeInput, maxMegapixelsInput].forEach((input) => {
        input.addEventListener('input', refreshEstimate);
    });

    fileInput.addEventListener('change', () => {
        clearSourceDimensions();
        if (fileInput.files.length) {
            const file = fileInput.files[0];
            fileNameDisplay.textContent = file.name;
            predefinedSelect.value = '';
            sourceObjectUrl = URL.createObjectURL(file);
            loadDimensions(sourceObjectUrl);
        } else {
            fileNameDisplay.textContent = '尚未選取';
        }
    });

    predefinedSelect.addEventListener('change', () => {
        clearSourceDimensions();
        if (predefinedSelect.value) {
            fileInput.value = '';
            fileNameDisplay.textContent = '使用範例圖片';
            loadDimensions(`/target_img/${encodeURIComponent(predefinedSelect.value)}`);
        }
    });

    updateDbBtn.addEventListener('click', async () => {
        if (requestInProgress) return;
        const elementDir = elementDirInput.value.trim();
        if (!elementDir) {
            dbStatus.textContent = '請先輸入素材資料夾。';
            dbStatus.className = 'db-status error';
            return;
        }
        rememberDirectory(elementDir);
        updateDbBtn.classList.add('is-loading');
        setRequestInProgress(true);
        dbStatus.textContent = '正在讀取素材色彩…';
        dbStatus.className = 'db-status loading';
        try {
            const payload = new FormData();
            payload.append('element_dir', elementDir);
            const response = await fetch('/api/update_elements', { method: 'POST', body: payload });
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.error || '更新失敗');
            dbStatus.textContent = `索引完成 · ${data.count} 張素材`;
            dbStatus.className = 'db-status success';
        } catch (error) {
            dbStatus.textContent = error.message;
            dbStatus.className = 'db-status error';
        } finally {
            updateDbBtn.classList.remove('is-loading');
            setRequestInProgress(false);
        }
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (requestInProgress || !form.reportValidity()) return;
        if (!fileInput.files.length && !predefinedSelect.value) {
            estimateState.textContent = '缺少圖片';
            estimateMeta.textContent = '請上傳圖片或選擇一張範例圖片。';
            return;
        }
        const raised = updateLargeOutputConfirmation();
        if (raised && !allowLargeInput.checked) {
            document.querySelector('.limit-panel').open = true;
            allowLargeInput.focus();
            estimateState.textContent = '需要確認';
            estimateMeta.textContent = '提高安全上限前，請確認大型輸出的記憶體風險。';
            return;
        }

        rememberDirectory(elementDirInput.value.trim());
        // Disabled controls are omitted by FormData, so capture the request first.
        const payload = new FormData(form);
        const requestedMaxPixels = positiveInteger(maxMegapixelsInput) * 1000000;
        generateBtn.classList.add('is-loading');
        setRequestInProgress(true);
        overlay.classList.add('active');
        overlay.setAttribute('aria-hidden', 'false');
        try {
            const response = await fetch('/api/montage', {
                method: 'POST',
                body: payload
            });
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.error || '生成失敗');

            resultImg.src = `${data.result_url}?t=${Date.now()}`;
            resultImg.hidden = false;
            emptyMessage.hidden = true;
            viewControls.hidden = false;
            resultStats.hidden = false;
            downloadBtn.href = data.result_url;
            downloadBtn.download = data.result_url.split('/').pop() || 'montage.png';
            document.getElementById('result-size').textContent = `${data.output_width.toLocaleString()} × ${data.output_height.toLocaleString()} px`;
            document.getElementById('result-grid').textContent = `${data.grid.columns} × ${data.grid.rows} 格`;
            document.getElementById('result-time').textContent = `${(data.timings_ms.total / 1000).toFixed(2)} 秒`;
            showEstimate({
                outputWidth: data.output_width,
                outputHeight: data.output_height,
                columns: data.grid.columns,
                rows: data.grid.rows,
                rawMemory: data.raw_memory_mb,
                peakMemory: data.estimated_peak_memory_mb,
                sampling: data.effective_sampling_size,
                tile: data.effective_element_size,
                pixels: data.output_pixels,
                maxPixels: requestedMaxPixels,
                wasLimited: data.was_limited
            }, true);
            resetView();
        } catch (error) {
            estimateState.textContent = '生成中止';
            estimateMeta.textContent = error.message;
            estimateWarning.hidden = true;
        } finally {
            generateBtn.classList.remove('is-loading');
            setRequestInProgress(false);
            overlay.classList.remove('active');
            overlay.setAttribute('aria-hidden', 'true');
        }
    });

    function updateTransform() {
        if (resultImg.hidden) return;
        resultImg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${currentScale})`;
    }

    function resetView() {
        currentScale = 1;
        translateX = 0;
        translateY = 0;
        updateTransform();
    }

    document.getElementById('zoom-in').addEventListener('click', () => {
        currentScale = Math.min(20, currentScale * 1.2);
        updateTransform();
    });
    document.getElementById('zoom-out').addEventListener('click', () => {
        currentScale = Math.max(0.1, currentScale / 1.2);
        updateTransform();
    });
    document.getElementById('zoom-reset').addEventListener('click', resetView);

    previewArea.addEventListener('wheel', (event) => {
        if (resultImg.hidden) return;
        event.preventDefault();
        currentScale *= event.deltaY < 0 ? 1.1 : (1 / 1.1);
        currentScale = Math.max(0.1, Math.min(20, currentScale));
        updateTransform();
    }, { passive: false });

    resultImg.addEventListener('dragstart', (event) => event.preventDefault());
    previewArea.addEventListener('mousedown', (event) => {
        if (resultImg.hidden || event.button !== 0 || event.target.closest('.view-controls')) return;
        event.preventDefault();
        isDragging = true;
        startX = event.clientX - translateX;
        startY = event.clientY - translateY;
    });
    window.addEventListener('mousemove', (event) => {
        if (!isDragging) return;
        translateX = event.clientX - startX;
        translateY = event.clientY - startY;
        updateTransform();
    });
    window.addEventListener('mouseup', () => { isDragging = false; });

    refreshEstimate();
});
