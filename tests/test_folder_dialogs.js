import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

function fixture() {
    class Element {
        constructor() { this.handlers = {}; this.open = false; this.value = ''; this.dataset = {}; this.content = {cloneNode() { return {}; }}; }
        addEventListener(type, handler) { this.handlers[type] = handler; }
        querySelectorAll() { return []; }
        querySelector() { return null; }
        replaceChildren() {}
        append() {}
        setCustomValidity() {}
        reportValidity() { return true; }
        showModal() { this.open = true; }
        close() { if (!this.open) return; this.open = false; this.handlers.close?.(); }
    }
    const elements = new Map();
    const get = id => {
        if (!elements.has(id)) elements.set(id, new Element());
        return elements.get(id);
    };
    get('folder-library-data').textContent = JSON.stringify({folders:[{id:'folder',name:'Words',sets:[]}],sets:[],memberships:{}});
    get('folder-settings-name').value = 'Words';
    const document = new Element();
    document.getElementById = get;
    document.createElement = () => new Element();
    const navigations = [];
    let reloads = 0;
    const location = {href:'http://localhost/set/example/overview',search:'',assign: url => navigations.push(url),reload: () => reloads++};
    const storage = new Map();
    const sessionStorage = {setItem:(key,value)=>storage.set(key,value),getItem:key=>storage.get(key),removeItem:key=>storage.delete(key)};
    const source = readFileSync(new URL('../static/js/modules/folders.js',import.meta.url),'utf8').replace('export function','function');
    runInNewContext(source+'\ninitializeFolders();',{document,window:{location},sessionStorage,URLSearchParams,fetch:async()=>({ok:true,json:async()=>({id:'new',name:'New Folder'})})});
    const click = (selector, dataset) => document.handlers.click({button:0,preventDefault(){},target:{closest: value=>value===selector?{dataset}:null}});
    return {get,click,storage,navigations,location,reloads:()=>reloads};
}

test('canceling settings opened from folder contents restores the contents without navigation',()=>{
    const f=fixture();
    f.click('[data-sidebar-folder]',{sidebarFolder:'folder'});
    assert.equal(f.get('folder-contents-dialog').open,true);
    f.get('folder-contents-dialog').querySelectorAll = () => [];
    // The same delegated action is used by the tile's settings control.
    f.click('[data-manage-folder]',{manageFolder:'folder'});
    assert.equal(f.get('folder-contents-dialog').open,false);
    f.get('folder-settings-dialog').close();
    assert.equal(f.get('folder-contents-dialog').open,true);
    f.get('folder-contents-dialog').close();
    assert.equal(f.reloads(),0);
    assert.deepEqual(f.navigations,[]);
});

test('saving settings refreshes the originating URL and remembers which folder to reopen',async()=>{
    const f=fixture();
    f.click('[data-manage-folder]',{manageFolder:'folder'});
    await f.get('folder-settings-form').handlers.submit({preventDefault(){}});
    assert.equal(f.reloads(),1);
    assert.deepEqual(f.navigations,[]);
    assert.deepEqual(JSON.parse(f.storage.get('verve-reopen-folder')),{path:f.location.href,id:'folder'});
});

test('canceling initial set selection refreshes the same page without redirecting home',async()=>{
    const f=fixture();
    f.get('folder-name-input').value='New Folder';
    await f.get('folder-name-form').handlers.submit({preventDefault(){}});
    f.get('folder-settings-dialog').close();
    assert.equal(f.reloads(),1);
    assert.deepEqual(f.navigations,[]);
    assert.equal(f.storage.has('verve-reopen-folder'),false);
});
