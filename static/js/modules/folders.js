/** Folder organization lives on the home page; cards keep their original sets. */
export function initializeFolders() {
    const dataElement = document.getElementById('folder-library-data');
    if (!dataElement) return;
    const library = JSON.parse(dataElement.textContent);
    const nameDialog = document.getElementById('folder-name-dialog');
    const nameForm = document.getElementById('folder-name-form');
    const nameInput = document.getElementById('folder-name-input');
    const nameError = document.getElementById('folder-name-error');
    const settings = document.getElementById('folder-settings-dialog');
    const settingsForm = document.getElementById('folder-settings-form');
    const settingsName = document.getElementById('folder-settings-name');
    const options = document.getElementById('folder-settings-sets');
    const settingsSearch = document.getElementById('folder-settings-search');
    const settingsError = document.getElementById('folder-settings-error');
    const contents = document.getElementById('folder-contents-dialog');
    const contentsGrid = document.getElementById('folder-contents-grid');
    const contentsSearch = document.getElementById('folder-contents-search');
    let currentFolder = null;
    let busy = false;
    let createdFolder = false;
    let returnToContents = false;
    const reopenKey = 'verve-reopen-folder';

    async function save(url, method, body) {
        const response = await fetch(url, {method, headers: {'Content-Type': 'application/json'},
            ...(body === undefined ? {} : {body: JSON.stringify(body)})});
        if (!response.ok) throw new Error('Could not save the Folder. Check its Name and selection, then try again.');
        return response.json();
    }
    function setBusy(dialog, value) {
        busy = value;
        dialog.querySelectorAll('button, input').forEach(control => { control.disabled = value; });
    }
    function bindDialog(dialog) {
        dialog.querySelectorAll('[data-close-folder-dialog]').forEach(button => button.addEventListener('click', () => close(dialog)));
        dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
        dialog.addEventListener('click', event => {
            const bounds = dialog.getBoundingClientRect();
            if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right
                || event.clientY < bounds.top || event.clientY > bounds.bottom)) close(dialog);
        });
    }
    function close(dialog) {
        if (busy) return;
        dialog.close();
    }
    function refreshPage(folderId = null) {
        // Refresh changed library data while retaining the originating page and URL.
        try {
            if (folderId) sessionStorage.setItem(reopenKey, JSON.stringify({path: window.location.href, id: folderId}));
            else sessionStorage.removeItem(reopenKey);
        } catch { /* A refresh still works when browser storage is unavailable. */ }
        createdFolder = false;
        window.location.reload();
    }
    function showSettings(id) {
        currentFolder = library.folders.find(folder => folder.id === id);
        if (!currentFolder || busy) return;
        returnToContents = contents.open;
        contents.close();
        settingsName.value = currentFolder.name;
        settingsName.setCustomValidity('');
        settingsSearch.value = '';
        settingsError.hidden = true;
        options.replaceChildren();
        for (const set of library.sets) {
            const label = document.createElement('label');
            label.className = 'folder-set-option';
            label.dataset.search = set.name.replaceAll('_', ' ').toLowerCase();
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.name = 'set_ids';
            checkbox.value = set.id;
            checkbox.checked = library.memberships[set.id] === id;
            const title = document.createElement('span');
            title.className = 'folder-set-name';
            title.textContent = set.name;
            const detail = document.createElement('span');
            detail.className = 'folder-set-count';
            detail.textContent = `${set.card_count} ${set.card_count === 1 ? 'Card' : 'Cards'}`;
            const previous = library.folders.find(folder => folder.id === library.memberships[set.id]);
            const checkboxControl = document.createElement('span');
            checkboxControl.className = 'folder-checkbox';
            const checkmark = document.createElement('span');
            checkmark.className = 'material-symbols-rounded folder-checkbox-mark';
            checkmark.textContent = 'check';
            checkmark.setAttribute('aria-hidden', 'true');
            checkboxControl.append(checkbox, checkmark);
            label.append(checkboxControl, title, detail);
            if (previous && previous.id !== id) {
                const description = `Selecting removes this Set from “${previous.name}” when you save.`;
                checkbox.setAttribute('aria-description', description);
                const notice = document.createElement('span');
                notice.className = 'folder-set-move-note';
                notice.title = description;
                const prefix = document.createElement('span');
                prefix.textContent = 'Selecting removes from ';
                const folder = document.createElement('span');
                folder.className = 'folder-set-previous-name';
                folder.textContent = previous.name;
                const suffix = document.createElement('span');
                suffix.textContent = ' on save';
                notice.append(prefix, folder, suffix);
                label.append(notice);
            }
            options.append(label);
        }
        if (!library.sets.length) {
            const empty = document.createElement('p');
            empty.textContent = 'No Sets yet. Create a Set on the Home Page to add it here.';
            options.append(empty);
        }
        updateSelection();
        settings.showModal();
    }
    function updateSelection() {
        let added = 0;
        let removed = 0;
        for (const input of options.querySelectorAll('input[type="checkbox"]')) {
            const wasSelected = library.memberships[input.value] === currentFolder.id;
            if (input.checked && !wasSelected) added++;
            if (!input.checked && wasSelected) removed++;
        }
        const changes = [];
        if (added) changes.push(`Add ${added} ${added === 1 ? 'Set' : 'Sets'}`);
        if (removed) changes.push(`Remove ${removed} ${removed === 1 ? 'Set' : 'Sets'}`);
        document.getElementById('folder-settings-save').textContent = changes.length ? `Save (${changes.join(', ')})` : 'Save';
    }
    function showContents(id) {
        currentFolder = library.folders.find(folder => folder.id === id);
        if (!currentFolder || busy) return;
        document.getElementById('folder-contents-title').textContent = currentFolder.name;
        contentsSearch.value = '';
        contentsGrid.replaceChildren();
        for (const set of currentFolder.sets) {
            const template = [...document.querySelectorAll('[data-folder-set-template]')].find(item => item.dataset.folderSetTemplate === set.id);
            if (template) contentsGrid.append(template.content.cloneNode(true));
        }
        document.getElementById('folder-contents-empty').hidden = currentFolder.sets.length !== 0;
        document.getElementById('folder-contents-no-results').hidden = true;
        const learn = document.getElementById('folder-contents-learn');
        learn.href = `/folder/${encodeURIComponent(id)}/learn`;
        learn.dataset.studyFolder = id;
        contents.showModal();
    }
    bindDialog(nameDialog);
    bindDialog(settings);
    bindDialog(contents);
    // A newly created folder already exists, even if its initial selection is canceled.
    settings.addEventListener('close', () => {
        if (createdFolder) { refreshPage(); return; }
        if (returnToContents) {
            returnToContents = false;
            showContents(currentFolder.id);
        }
    });
    nameDialog.querySelectorAll('[data-close-folder-name]').forEach(button => button.addEventListener('click', () => close(nameDialog)));
    nameDialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
    nameInput.addEventListener('input', () => { nameInput.setCustomValidity(''); nameError.hidden = true; });
    document.querySelector('[data-new-folder]')?.addEventListener('click', () => {
        nameForm.reset();
        nameInput.setCustomValidity('');
        nameError.hidden = true;
        nameDialog.showModal();
    });
    nameForm.addEventListener('submit', async event => {
        event.preventDefault();
        if (busy) return;
        const name = nameInput.value.trim();
        nameInput.setCustomValidity(name ? '' : 'Please enter a Folder Name.');
        if (!nameForm.reportValidity()) return;
        setBusy(nameDialog, true);
        try {
            const result = await save('/api/folders', 'POST', {name});
            library.folders.push({...result, sets: [], card_count: 0, due_count: 0});
            createdFolder = true;
            setBusy(nameDialog, false);
            nameDialog.close();
            showSettings(result.id);
        } catch (error) {
            nameError.textContent = error.message;
            nameError.hidden = false;
        } finally { setBusy(nameDialog, false); }
    });
    settingsName.addEventListener('input', () => settingsName.setCustomValidity(''));
    options.addEventListener('change', updateSelection);
    settingsSearch.addEventListener('input', () => {
        const search = settingsSearch.value.toLowerCase();
        options.querySelectorAll('.folder-set-option').forEach(option => { option.hidden = !option.dataset.search.includes(search); });
    });
    settingsForm.addEventListener('submit', async event => {
        event.preventDefault();
        if (busy) return;
        const name = settingsName.value.trim();
        settingsName.setCustomValidity(name ? '' : 'Please enter a Folder Name.');
        if (!settingsForm.reportValidity()) return;
        setBusy(settings, true);
        settingsError.hidden = true;
        try {
            await save(`/api/folders/${currentFolder.id}/sets`, 'PUT', {
                name, set_ids: [...options.querySelectorAll('input:checked')].map(input => input.value)});
            refreshPage(currentFolder.id);
        } catch (error) {
            settingsError.textContent = error.message;
            settingsError.hidden = false;
        } finally { setBusy(settings, false); }
    });
    function deleteFolder(id) {
        if (busy) return;
        window.showConfirmationModal({title:'Delete Folder', message:'Delete this Folder? Its Sets and Learning Progress will be kept.',
            confirmText:'Delete Folder', onConfirm: async () => {
                try { await save(`/api/folders/${id}`, 'DELETE'); refreshPage(); }
                catch (error) { showSettings(id); settingsError.textContent = error.message; settingsError.hidden = false; }
            }});
    }
    contentsSearch.addEventListener('input', () => {
        let matches = 0;
        contentsGrid.querySelectorAll('.set-card').forEach(card => {
            card.hidden = !card.querySelector('.card-normal-title').textContent.toLowerCase().includes(contentsSearch.value.toLowerCase());
            if (!card.hidden) matches++;
        });
        document.getElementById('folder-contents-no-results').hidden = matches !== 0 || currentFolder.sets.length === 0;
    });
    contents.querySelectorAll('[data-edit-current-folder]').forEach(button => button.addEventListener('click', () => showSettings(currentFolder.id)));
    document.addEventListener('click', event => {
        const sidebarFolder = event.target.closest('[data-sidebar-folder]');
        if (sidebarFolder) {
            if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            showContents(sidebarFolder.dataset.sidebarFolder);
            return;
        }
        const remove = event.target.closest('[data-delete-folder]');
        if (remove) { deleteFolder(remove.dataset.deleteFolder); return; }
        const manage = event.target.closest('[data-manage-folder]');
        if (manage) { showSettings(manage.dataset.manageFolder); return; }
        if (event.target.closest('button, a, input')) return;
        const folder = event.target.closest('[data-open-folder]');
        const set = event.target.closest('[data-set-overview]');
        if (folder) showContents(folder.dataset.openFolder);
        else if (set) window.location.assign(set.dataset.setOverview);
    });
    document.addEventListener('keydown', event => {
        if (!['Enter',' '].includes(event.key) || !event.target.matches('[data-open-folder], [data-set-overview]')) return;
        event.preventDefault();
        event.target.click();
    });
    document.querySelectorAll('[data-clear-search]').forEach(button => {
        button.addEventListener('click', () => {
            const field = document.getElementById(button.dataset.clearSearch);
            field.value = '';
            field.dispatchEvent(new Event('input', {bubbles: true}));
            field.focus();
        });
    });
    let requested = new URLSearchParams(window.location.search).get('folder');
    try {
        const reopen = JSON.parse(sessionStorage.getItem(reopenKey) || 'null');
        sessionStorage.removeItem(reopenKey);
        if (reopen?.path === window.location.href) requested = reopen.id;
    } catch { /* Direct folder links also work without browser storage. */ }
    if (requested) showContents(requested);
}
