// Exercise asynchronous UI regressions without adding browser dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function setup({ blockedStorage = false } = {}) {
    const elements = new Map();
    const probes = [];
    const requests = [];
    const controls = [];
    function element(id) {
        if (!elements.has(id)) elements.set(id, {
            id, value: '', files: [], disabled: false, hidden: false,
            style: {}, handlers: {}, attributes: {},
            classList: { add() {}, remove() {} },
            addEventListener(type, handler) { this.handlers[type] = handler; },
            setAttribute(name, value) { this.attributes[name] = value; },
            querySelectorAll() { return controls; },
            reportValidity() { return true; },
            focus() {},
        });
        return elements.get(id);
    }
    for (const [id, value] of Object.entries({
        element_dir: './materials', org_img_pixel: '25', element_img_pixel: '100',
        max_output_edge: '10000', max_output_megapixels: '100',
        predefined_img: '', image_file: '', allow_large_output: '',
        'generate-btn': '', 'update-db-btn': '',
    })) {
        element(id).value = value;
        controls.push(element(id));
    }
    const context = {
        document: {
            getElementById: element, querySelector: element,
            addEventListener(type, callback) { callback(); },
        },
        window: { addEventListener() {} },
        localStorage: {
            getItem() { if (blockedStorage) throw new Error('Storage blocked'); return null; },
            setItem() { if (blockedStorage) throw new Error('Storage blocked'); },
        },
        Image: class { constructor() { probes.push(this); } },
        URL: { createObjectURL() { return 'blob:test'; }, revokeObjectURL() {} },
        FormData: class extends Map {
            constructor(form) {
                super();
                if (form) for (const control of controls) {
                    if (!control.disabled) this.set(control.id, control.value);
                }
            }
            append(name, value) { this.set(name, value); }
        },
        fetch(url, options) {
            return new Promise((resolve, reject) => requests.push({ url, options, resolve, reject }));
        },
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/script.js'), 'utf8'), context);
    return {
        element, probes, requests, controls,
        select(value) {
            element('predefined_img').value = value;
            element('predefined_img').handlers.change();
        },
        submit() { return element('montage-form').handlers.submit({ preventDefault() {} }); },
    };
}

test('late image success and failure cannot overwrite the latest source estimate', () => {
    const ui = setup();
    ui.select('slow.png');
    ui.select('fast.png');
    Object.assign(ui.probes[1], { naturalWidth: 50, naturalHeight: 25 });
    ui.probes[1].onload();
    assert.equal(ui.element('estimate-dimensions').textContent, '200 × 100');
    Object.assign(ui.probes[0], { naturalWidth: 500, naturalHeight: 500 });
    ui.probes[0].onload();
    ui.probes[0].onerror();
    assert.equal(ui.element('estimate-dimensions').textContent, '200 × 100');
    ui.select('');
    ui.probes[1].onload();
    assert.equal(ui.element('estimate-state').textContent, '等待圖片');
});

test('blocked storage still permits requests; pending requests lock controls and reject duplicates', async () => {
    const ui = setup({ blockedStorage: true });
    ui.select('target.png');
    const pending = ui.submit();
    assert.equal(ui.requests.length, 1);
    assert.equal(ui.requests[0].options.body.get('org_img_pixel'), '25');
    assert.equal(ui.requests[0].options.body.get('predefined_img'), 'target.png');
    assert.ok(ui.controls.every(control => control.disabled));
    await ui.submit();
    await ui.element('update-db-btn').handlers.click();
    assert.equal(ui.requests.length, 1);
    ui.requests[0].reject(new Error('Connection lost'));
    await pending;
    assert.ok(ui.controls.every(control => !control.disabled));
    assert.equal(ui.element('estimate-meta').textContent, 'Connection lost');
});

test('scanning blocks generation and unlocks the form after success', async () => {
    const ui = setup();
    ui.select('target.png');
    const pending = ui.element('update-db-btn').handlers.click();
    await ui.submit();
    assert.equal(ui.requests.length, 1);
    assert.equal(ui.requests[0].url, '/api/update_elements');
    ui.requests[0].resolve({ ok: true, json: async () => ({ success: true, count: 3 }) });
    await pending;
    assert.ok(ui.controls.every(control => !control.disabled));
    assert.equal(ui.element('db-status').textContent, '索引完成 · 3 張素材');
});

test('fractional dimensions are not silently truncated in the estimate', () => {
    const ui = setup();
    ui.select('target.png');
    Object.assign(ui.probes[0], { naturalWidth: 50, naturalHeight: 25 });
    ui.probes[0].onload();
    ui.element('org_img_pixel').value = '1.5';
    ui.element('org_img_pixel').handlers.input();
    assert.equal(ui.element('estimate-state').textContent, '參數不完整');
});
