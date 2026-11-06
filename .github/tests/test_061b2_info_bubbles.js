/* Exercise the production popup lifecycle without HA or a browser process.
 * Real shadow DOM, native details events and layout are covered by the Python
 * browser companion; this fixture covers event ownership and cleanup paths.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let doc;
class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.nodeType = 1;
    this.attrs = new Map(); this.children = []; this.handlers = new Map();
    this.style = {}; this.classList = {add(){}}; this.isConnected = true;
    this.ownerDocument = doc; this.open = false; this.popoverOpen = false;
  }
  addEventListener(type, fn, options) {
    const handlers = this.handlers.get(type) || [];
    if (!handlers.some(item => item.fn === fn && item.options === options))
      handlers.push({fn, options});
    this.handlers.set(type, handlers);
  }
  removeEventListener(type, fn, options) {
    this.handlers.set(type, (this.handlers.get(type) || []).filter(item =>
      item.fn !== fn || item.options !== options));
  }
  emit(type, path = [this], values = {}) {
    const event = {target:path[0], composedPath:()=>path, ...values};
    for (const {fn} of [...(this.handlers.get(type) || [])]) fn(event);
  }
  setAttribute(key, value) { this.attrs.set(key, String(value)); }
  getAttribute(key) { return this.attrs.get(key) ?? null; }
  removeAttribute(key) { this.attrs.delete(key); }
  appendChild(child) { child.parentElement = this; this.children.push(child); return child; }
  attachShadow() { return this.shadowRoot = this.appendChild(new Element('shadow')); }
  contains(node) { return node === this || this.children.some(child => child.contains(node)); }
  remove() { this.isConnected = false; this.parentElement.children = this.parentElement.children.filter(child => child !== this); }
  matches(selector) {
    if (selector === ':popover-open') return this.popoverOpen;
    if (selector === '[data-room-issue114]') return this.attrs.has('data-room-issue114');
    if (selector === '[data-room-fold87]') return this.attrs.has('data-room-fold87');
    return false;
  }
  closest(selector) { return this.matches(selector) ? this : this.parentElement?.closest(selector); }
  querySelector(selector) {
    if (selector === ':scope > summary') return this.children.find(child => child.tagName === 'SUMMARY');
    if (selector === '.hem-context-body76,.metric-help-content') return this.children.find(child => child.tagName === 'DIV');
    return null;
  }
  querySelectorAll() { return []; }
  getBoundingClientRect() { return {top:90, bottom:120, right:400}; }
  showPopover() { this.popoverOpen = true; }
  hidePopover() {
    this.emit('beforetoggle', [this], {newState:'closed'});
    this.popoverOpen = false;
    this.emit('toggle', [this], {newState:'closed'});
  }
  focus() {}
}
doc = new Element('document');
doc.documentElement = {clientWidth:1024, clientHeight:900};
doc.createElement = tag => new Element(tag);
const elements = new Map();
const context = {HTMLElement:Element, document:doc, window:{innerWidth:1024,innerHeight:900},
  console, setTimeout, clearTimeout,
  customElements:{get:name=>elements.get(name),define:(name,ctor)=>elements.set(name,ctor)}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), context);
const Card = elements.get('home-environment-manager-card');
const card = new Card();
card._installFolds87();
card._detailsExpanded66 = new Set();
card._syncRoomIssueButtons115 = () => {};
const outside = new Element('button');
const source = key => {
  const detail = new Element('details');
  if (key) detail.setAttribute('data-detail-id', key);
  detail.appendChild(new Element('summary'));
  detail.appendChild(new Element('div')).innerHTML = '<small>First line</small><small>Second line</small>';
  card.shadowRoot.appendChild(detail);
  return detail;
};
const room = source('room-info:living'), device = source('device-info:climate.hem_heater');
function listeners(count) {
  for (const type of ['click','keydown']) assert.equal((doc.handlers.get(type) || []).length, count, type);
  assert.equal(card.shadowRoot.children.filter(node => node.className === 'hem-floating-info87').length,
    count, 'floating popup node count');
}
function open(detail) {
  detail.open = true;
  const key = detail.getAttribute('data-detail-id');
  if (key) card._detailsExpanded66.add(key);
  card._openInfo87(detail);
  assert.ok(card._floatingInfo87?.isConnected);
  listeners(1);
}
function closed(detail) {
  assert.equal(detail.open, false);
  assert.ok(!card._detailsExpanded66.has(detail.getAttribute('data-detail-id')));
  assert.equal(card._floatingInfo87, null);
  listeners(0);
}
for (let iteration = 0; iteration < 3; iteration++) {
  open(room);
  const pop = card._floatingInfo87;
  const child = pop.appendChild(new Element('small'));
  // At document level native shadow-DOM events are retargeted to the card.
  doc.emit('click', [child,pop,card.shadowRoot,card,doc], {target:card});
  assert.equal(card._floatingInfo87, pop);
  doc.emit('click', [room.children[0],room,card.shadowRoot,card,doc], {target:card});
  assert.equal(card._floatingInfo87, pop, 'source click must reach its own toggle');
  doc.emit('click', [outside,card.shadowRoot,card,doc], {target:card});
  closed(room);
  assert.ok(!card._info76('room-info:living', 'Room', 'Text').includes(' open'));
}
open(room);
card._openInfo87(room); // Same-source refresh replaces its portal, not its open state.
assert.equal(room.open, true); listeners(1);
open(device);
assert.equal(room.open, false);
assert.ok(!card._detailsExpanded66.has('room-info:living'));
doc.emit('click', [outside,doc]); closed(device);
open(room);
doc.emit('keydown', [outside,doc], {key:'ArrowDown'});
assert.ok(card._floatingInfo87);
doc.emit('keydown', [outside,doc], {key:'Escape'}); closed(room);
open(room);
card._floatingInfo87.hidePopover(); closed(room);
const metric = source(null);
open(metric); doc.emit('click', [outside,doc]); closed(metric);
// Existing room-problem navigation owns extra folds: its second press must
// reach that handler before any popup dismissal changes its open-state test.
const problem = new Element('button');
problem.setAttribute('data-room-issue114', 'controllers');
problem.setAttribute('data-issue-area114', 'living');
card.shadowRoot.appendChild(problem);
card._roomIssueViews115 = new Map([['living',{kind:'controllers',infoKey:'device-info:climate.hem_heater'}]]);
open(device);
doc.emit('click', [problem,card.shadowRoot,card,doc], {target:card});
assert.equal(device.open, true);
card._closeInfo87(true); closed(device);
open(room);
const detachedPopup = card._floatingInfo87;
// disconnectedCallback runs after the card and its shadow descendants have
// already left the document; the popup still has a parent in that subtree.
detachedPopup.isConnected = false;
card.disconnectedCallback();
assert.equal(card.shadowRoot.contains(detachedPopup), false, 'Disconnect retained an orphan popup');
assert.equal(card._floatingInfo87, null); listeners(0);
// Simulate the reconnect render rebuilding the still-open disclosure.
open(room); doc.emit('click', [outside,doc]); closed(room);
// No native popover API: fallback must be visible and retain dismissal.
const nativeShow = Element.prototype.showPopover;
Element.prototype.showPopover = undefined;
open(room);
assert.equal(card._floatingInfo87.getAttribute('popover'), null);
doc.emit('click', [outside,doc]); closed(room);
Element.prototype.showPopover = nativeShow;
if (process.argv[3]) {
  const data = JSON.parse(process.argv[3]);
  card._config = {entity:'sensor.hem'};
  card._hass = {language:'el',states:data.states,entities:data.entities};
  const markup = card._climatePanel(data.room);
  const info = markup.match(/data-detail-id="room-info:living"[\s\S]*?class="hem-context-body76">([\s\S]*?)<\/div>/)?.[1];
  const lines = [...(info || '').matchAll(/<small[^>]*>([\s\S]*?)<\/small>/g)].map(match => match[1]);
  assert.ok(lines.length >= 3, JSON.stringify(lines));
  assert.ok(lines[0].includes('Προτεραιότητα'), JSON.stringify(lines));
  assert.ok(lines.some(line => line.includes('Απόφαση υγρασίας') && line.includes('56,2%')), JSON.stringify(lines));
  assert.ok(lines.some(line => line.includes('Σύνοψη δωματίου')), JSON.stringify(lines));
  assert.ok(markup.includes('data-detail-id="setting-help:select.hem_method"'));
}
console.log('061B2_INFO_BUBBLE_LIFECYCLE=PASS');
