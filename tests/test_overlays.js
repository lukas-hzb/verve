import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

function setup() {
    const listeners = {};
    const classes = new Set();
    const styles = new Map();
    const root = {dataset:{},classList:{add:n=>classes.add(n),remove:n=>classes.delete(n)},style:{setProperty:(k,v)=>styles.set(k,v),removeProperty:k=>styles.delete(k)}};
    const panel = () => ({open:false,matches(){return this.open;},addEventListener(){}});
    const panels = [panel(),panel(),panel()];
    const restored = [];
    let sync;
    const source = readFileSync(new URL('../static/js/modules/overlays.js',import.meta.url),'utf8').replace('export function','function');
    runInNewContext(source+'\ninitializeOverlays();',{
        document:{documentElement:root,querySelectorAll:()=>panels,addEventListener:(name,cb)=>listeners[name]=cb},
        window:{scrollX:0,scrollY:320,scrollTo:(x,y)=>restored.push([x,y])},
        MutationObserver:class {constructor(cb){sync=cb;} observe(){}},
    });
    return {panels,sync,classes,styles,restored,root,listeners};
}

test('modal transitions keep background locked until the last overlay closes and restore the scroll position',()=>{
    const f=setup();
    f.panels[0].open=true;f.sync();
    assert.equal(f.classes.has('overlay-scroll-locked'),true);
    assert.equal(f.styles.get('--overlay-scroll-top'),'-320px');
    f.panels[0].open=false;f.panels[1].open=true;f.sync();
    assert.deepEqual(f.restored,[]);
    f.panels[2].open=true;f.panels[1].open=false;f.sync();
    assert.equal(f.classes.has('overlay-scroll-locked'),true);
    f.panels[2].open=false;f.sync();
    assert.equal(f.classes.has('overlay-scroll-locked'),false);
    assert.deepEqual(f.restored,[[0,320]]);
    assert.equal(f.styles.has('--overlay-scroll-top'),false);
});

test('touch input suppresses restored pointer focus rings while keyboard navigation enables them',()=>{
    const f=setup();
    f.listeners.pointerdown();
    assert.equal(f.root.dataset.inputMethod,'pointer');
    f.listeners.keydown({key:'Tab'});
    assert.equal(f.root.dataset.inputMethod,'keyboard');
    f.listeners.pointerdown();
    f.listeners.keydown({key:'Escape'});
    assert.equal(f.root.dataset.inputMethod,'pointer');
});
