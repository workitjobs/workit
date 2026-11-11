"""The page's natives, for Ask's and the profile check's reads of an element (KAN-783).

A page can give an element, or a prototype, a getter or a method of its own: one
that throws, one that lies ("Next" on its Submit), one that calls the native
submit while the guard reads it, or a Proxy in the prototype chain. A guard that read
`el.innerText`, `el.getAttribute(...)`, `RegExp.prototype.test` or
`[...nodes].some(...)` read the page's code. Two of those sent an application
on main (the review of #449).

NATIVES is a JS prelude: `$`-named consts taken from the browser's own
prototypes when it runs. The guard script has its own such built-ins (KAN-710,
apply.submit_guard); NATIVES serves the reads that also run outside it, so one
body serves both: PROFILE_DIALOG (Claude fill evaluates it on its own) and
send_click.ELEMENT (Ask's read, by plain.tools too, and the drive guard's Ask
section, which runs NATIVES once as the guard starts, before any page code). An
arrow `$R` call never looks a method up on the object it reads, a `$bare()` array
has no prototype (so no setter of the page's runs on a write to it), and loops go
by index (no iterator of the page's). Evaluated on its own, it runs at the call:
in the extension's isolated world that is the browser's own, and in the page's
world it is no worse than a plain read.

It holds only what those two read. Each helper takes their own values (strings, elements) and answers
`''`, `null`, `false` or a `$bare()` array for anything it can't read. A
brand-checked getter that doesn't fit throws, and the guards' listeners treat
any throw as "may send" (fail closed)."""

NATIVES = r"""
  const $R = Reflect.apply, $gopd = Object.getOwnPropertyDescriptor, $setProto = Object.setPrototypeOf;
  const $bare = () => $setProto([], null);
  const $getter = (proto, name) => {
    const d = proto ? $gopd(proto, name) : undefined, f = d && d.get;
    return (o) => (f ? $R(f, o, []) : undefined);
  };
  const $method = (proto, name) => {
    const f = proto ? proto[name] : undefined;
    return typeof f === 'function' ? (o, ...a) => $R(f, o, a) : null;
  };
  // The first of these kinds' getters whose brand check takes the node (an input's type, a button's).
  const $prop = (name, ...kinds) => {
    const gs = $bare();
    for (let i = 0; i < kinds.length; i++) {
      const d = kinds[i] ? $gopd(kinds[i].prototype, name) : undefined;
      if (d && d.get) gs[gs.length] = d.get;
    }
    return (o) => {
      for (let i = 0; i < gs.length; i++) { try { return $R(gs[i], o, []); } catch (e) {} }
      return undefined;
    };
  };
  const $SP = String.prototype, $EP = Element.prototype, $NP = Node.prototype, $DP = Document.prototype;
  const $exec = RegExp.prototype.exec;
  const $txt = (v) => (typeof v === 'string' ? v : '');
  const $found = (re, s) => $R($exec, re, [$txt(s)]);
  const $re = (re, s) => $found(re, s) !== null;
  const $trimS = $method($SP, 'trim'), $sliceS = $method($SP, 'slice');
  const $trim = (s) => $trimS($txt(s));
  const $cut = (s, a, b) => (b === undefined ? $sliceS($txt(s), a) : $sliceS($txt(s), a, b));
  // Each run of white space as one space (a fresh /g regex, its lastIndex its own).
  const $collapse = (s) => {
    s = $txt(s);
    const r = /\s+/g;
    let out = '', at = 0, m;
    while ((m = $R($exec, r, [s])) !== null) { out += $cut(s, at, m.index) + ' '; at = r.lastIndex; }
    return out + $cut(s, at);
  };
  const $words = (s) => {
    s = $collapse($trim(s));
    const out = $bare();
    let w = '';
    for (let i = 0; i < s.length; i++) {
      if (s[i] === ' ') { if (w) out[out.length] = w; w = ''; } else w += s[i];
    }
    if (w) out[out.length] = w;
    return out;
  };
  const $any = (a, f) => { for (let i = 0; i < a.length; i++) if (f(a[i])) return true; return false; };
  const $join = (a, sep) => { let out = ''; for (let i = 0; i < a.length; i++) if (a[i]) out += (out ? sep : '') + a[i]; return out; };

  const $nodeType = $getter($NP, 'nodeType');
  const $isNode = (n) => { try { return typeof $nodeType(n) === 'number'; } catch (e) { return false; } };
  const $isEl = (n) => { try { return $nodeType(n) === 1; } catch (e) { return false; } };
  const $isDoc = (n) => { try { return $nodeType(n) === 9; } catch (e) { return false; } };
  const $tagGet = $getter($EP, 'tagName'), $attrM = $method($EP, 'getAttribute');
  const $closestM = $method($EP, 'closest');
  const $elOne = $method($EP, 'querySelector'), $elAll = $method($EP, 'querySelectorAll');
  const $docOne = $method($DP, 'querySelector'), $docAll = $method($DP, 'querySelectorAll');
  const $tag = (n) => ($isEl(n) ? $txt($tagGet(n)) : '');
  const $attr = (n, name) => ($isEl(n) ? $txt($attrM(n, name)) : '');
  const $up = (n, sel) => ($isEl(n) ? $closestM(n, sel) : null);
  const $nlLen = $getter(NodeList.prototype, 'length'), $nlItem = $method(NodeList.prototype, 'item');
  const $hcLen = $getter(HTMLCollection.prototype, 'length'), $hcItem = $method(HTMLCollection.prototype, 'item');
  // A NodeList's or an HTMLCollection's nodes, as a $bare() array.
  const $nodes = (c) => {
    const out = $bare();
    if (c === null || c === undefined) return out;
    let len, item;
    try { len = $nlLen(c); item = $nlItem; } catch (e) { len = $hcLen(c); item = $hcItem; }
    for (let i = 0; i < len; i++) out[i] = item(c, i);
    return out;
  };
  const $one = (scope, sel) => ($isEl(scope) ? $elOne(scope, sel) : $isDoc(scope) ? $docOne(scope, sel) : null);
  const $all = (scope, sel) => $nodes($isEl(scope) ? $elAll(scope, sel) : $isDoc(scope) ? $docAll(scope, sel) : null);
  const $innerGet = $getter(HTMLElement.prototype, 'innerText'), $textGet = $getter($NP, 'textContent');
  const $textOf = (n) => ($isNode(n) ? $txt($textGet(n)) : '');
  // What a person reads on the element: innerText, or the text of an element that has none (an SVG's).
  const $text = (n) => {
    if (!$isNode(n)) return '';
    try { return $txt($innerGet(n)); } catch (e) { return $textOf(n); }
  };
  const $parentGet = $getter($NP, 'parentElement');
  const $parent = (n) => ($isNode(n) ? $parentGet(n) : null);
  const $containsM = $method($NP, 'contains');
  const $contains = (a, b) => $isNode(a) && $containsM(a, b) === true;
  const $visM = $method($EP, 'checkVisibility');
  const $shown = (n) => !$visM || ($isEl(n) && $visM(n) === true);
  const $IN = typeof HTMLInputElement === 'function' ? HTMLInputElement : null;
  const $BU = typeof HTMLButtonElement === 'function' ? HTMLButtonElement : null;
  const $SE = typeof HTMLSelectElement === 'function' ? HTMLSelectElement : null;
  const $TA = typeof HTMLTextAreaElement === 'function' ? HTMLTextAreaElement : null;
  const $typeOf = $prop('type', $IN, $BU, $SE, $TA, HTMLFieldSetElement, HTMLOutputElement);
  const $valueOf = $prop('value', $IN, $BU, $SE, $TA, HTMLOutputElement, HTMLOptionElement);
  const $labelsOf = $prop('labels', $IN, $BU, $SE, $TA, HTMLOutputElement, HTMLMeterElement, HTMLProgressElement);
  const $type = (n) => $txt($typeOf(n));
  const $value = (n) => $txt($valueOf(n));
  const $labels = (n) => { const l = $labelsOf(n); return l ? $nodes(l) : null; };
  const $control = $getter(typeof HTMLLabelElement === 'function' ? HTMLLabelElement.prototype : null, 'control');
  const $byIdM = $method($DP, 'getElementById');
  const $byId = (id) => $byIdM(document, id);
"""
