/** Verve backups carry their own structure, so separator controls do not apply. */
const upload = document.querySelector('#import-file, #file');
if (upload) {
    const form = upload.closest('form');
    const settings = form.querySelector('.import-box');
    const update = () => {
        const isVerve = document.getElementById('import_type').value === 'file'
            && upload.files[0]?.name.toLowerCase().endsWith('.verve');
        settings.hidden = Boolean(isVerve);
        settings.querySelectorAll('input, select').forEach(control => { control.disabled = Boolean(isVerve); });
    };
    upload.addEventListener('change', update);
    ['tab-file', 'tab-text'].forEach(id => document.getElementById(id)?.addEventListener('click', update));
    update();
}
