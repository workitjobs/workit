"""Page code that a developer module runs, which a plain Worker runs as its fixed copy (apply.plain.fixed): Ask
Claude's (apply.ask) and the emailed code's (apply.email_code). Here, not in those modules, so the Student build,
which holds neither (apply.build, KAN-723), still lists every fixed function at a plain Worker's first page call."""

# Ask Claude's (apply.ask): the fields it reads, and one put back.
_SELECTOR = "input, select, textarea, [role=combobox]:not(input), [contenteditable=true], [role=checkbox]:not(input), [role=switch]:not(input)"
# Every field a frame shows, with its value: the page's state, for Claude and for the read-back.
FIELDS = """() => {
  const text = el => ((el && (el.innerText || el.textContent)) || '').replace(/\\s+/g, ' ').trim();
  const shown = el => !el.checkVisibility || el.checkVisibility();
  const custom = el => el.tagName !== 'INPUT' && /^(checkbox|switch)$/.test(el.getAttribute('role') || '');
  const labelOf = el => {
    const by = (el.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean)
      .map(id => text(document.getElementById(id))).join(' ');
    const own = el.labels && el.labels.length ? [...el.labels].map(text).join(' ') : '';
    const inner = custom(el) ? text(el) || text(el.closest('label') || el.parentElement) : '';
    return (el.getAttribute('aria-label') || by || own || inner || el.placeholder || el.name || el.id || '').slice(0, 300);
  };
  const all = [...document.querySelectorAll(SELECTOR)];
  const fields = [];
  all.forEach((el, i) => {
    const type = el.tagName === 'INPUT' ? (el.type || 'text') : el.tagName === 'SELECT' || el.tagName === 'TEXTAREA'
      ? el.tagName.toLowerCase() : custom(el) ? 'checkbox' : el.getAttribute('role') === 'combobox' ? 'combobox' : 'editable';
    if (['hidden', 'submit', 'button', 'image', 'reset'].includes(type)) return;
    const box = type === 'checkbox' || type === 'radio';
    const f = {i, type, label: labelOf(el)};
    // Not on view: another step of a form that keeps every step in the page, so its fields are read back too.
    if (!shown(el) && !(box && el.labels && [...el.labels].some(shown))) f.hidden = true;
    if (el.required || el.getAttribute('aria-required') === 'true') f.required = true;
    // A dropdown built on a text box (Eightfold's, Microsoft's): its value is only the text it shows, and setting
    // the text back doesn't pick the option again, so UNDO leaves it alone.
    if (el.tagName === 'INPUT' && (el.getAttribute('role') === 'combobox' || el.hasAttribute('aria-autocomplete')
        || /listbox/.test(el.getAttribute('aria-haspopup') || ''))) f.combo = true;
    const group = el.closest('fieldset, [role=group], [role=radiogroup]');
    const legend = group && text(group.querySelector('legend, [role=heading], label, p'));
    if (legend && legend !== f.label) f.group = legend.slice(0, 300);
    if (box) f.checked = custom(el) ? el.getAttribute('aria-checked') === 'true' : el.checked;
    else if (type === 'password') f.value = el.value ? '(secret)' : '';
    else if (type === 'select') f.value = [...el.selectedOptions].map(text).join('; ');
    else if (type === 'file') f.value = [...(el.files || [])].map(x => x.name).join('; ');
    else if (type === 'combobox' || type === 'editable') f.value = text(el).slice(0, 500);
    else f.value = String(el.value || '').slice(0, 2000);
    fields.push(f);
  });
  return {url: location.href, title: document.title, fields: fields.slice(0, 400)};
}""".replace("SELECTOR", repr(_SELECTOR))
# Put one field back as it was: [its index in SELECTOR's list, its type, its old value or checked].
UNDO = """([i, type, old]) => {
  const el = [...document.querySelectorAll(SELECTOR)][i];
  if (!el) return false;
  if (el.tagName !== 'INPUT' && type === 'checkbox') {  // a custom box: its own click flips aria-checked
    if (!/^(checkbox|switch)$/.test(el.getAttribute('role') || '')) return false;
    const on = () => el.getAttribute('aria-checked') === 'true';
    if (on() !== old) el.click();
    return on() === old;
  }
  if (type === 'checkbox' || type === 'radio') {
    if (el.type !== type) return false;
    if (el.checked !== old) el.click();
    return el.checked === old;
  }
  const text = o => (o.innerText || o.textContent || '').replace(/\\s+/g, ' ').trim();
  if (el.tagName === 'SELECT') {  // FIELDS reads a select by its option's text: pick that option again
    const option = [...el.options].find(o => text(o) === old) || (old === '' ? el.options[0] : null);
    if (!option) return false;
    el.value = option.value;
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
    return [...el.selectedOptions].map(text).join('; ') === old;
  }
  if (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA') return false;  // a custom dropdown or editable box
  if (el.getAttribute('role') === 'combobox' || el.hasAttribute('aria-autocomplete')
      || /listbox/.test(el.getAttribute('aria-haspopup') || '')) return false;  // its text alone isn't its pick
  const proto = Object.getPrototypeOf(el), set = Object.getOwnPropertyDescriptor(proto, 'value');
  if (!set || !set.set) return false;
  set.set.call(el, old);
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
  return el.value === old;
}""".replace("SELECTOR", repr(_SELECTOR))

# The emailed code's (apply.email_code): the words of a box, read in the page (its id, name, label, placeholder
# and autocomplete).
WORDS = "b => [b.id, b.name, b.getAttribute('aria-label'), b.placeholder, b.autocomplete].join(' ')"
