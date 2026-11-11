// A Turbopack loader for Phosphor's glyph tables
// (node_modules/@phosphor-icons/react/dist/defs/<Glyph>.es.js). Each holds a
// Map of all six weights; this keeps regular and the weights that
// src/components/icon-weights.ts names for the glyph, and drops the rest
// (KAN-782). next.config.ts passes that list as the `keep` option.
//
// The table's layout is Phosphor 2.1's, which package.json pins exactly. If a
// new release changes it, the loader throws and the build stops, rather than
// shipping glyphs that draw nothing.

const WEIGHTS = ["bold", "duotone", "fill", "light", "regular", "thin"];
// One entry of the Map: `\n  [\n    "bold",\n ... \n  ]`. Its contents are
// indented deeper, so the first line that is two spaces and `]` ends it.
const ENTRY = /\n {2}\[\n {4}"(\w+)",\n[\s\S]*?\n {2}\]/g;

/**
 * @param {string} source a glyph table's module
 * @param {string} glyph its name, for the error
 * @param {readonly string[]} extra weights to keep beside regular
 */
function stripWeights(source, glyph, extra) {
  const entries = [...source.matchAll(ENTRY)];
  const found = entries.map((m) => m[1]);
  if (found.join() !== WEIGHTS.join()) {
    throw new Error(
      `phosphor-weights-loader: ${glyph}'s weights read as [${found}], not [${WEIGHTS}]. ` +
        "Phosphor's table layout changed; update the loader with the new version.",
    );
  }
  const kept = entries.filter((m) => m[1] === "regular" || extra.includes(m[1]));
  const first = entries[0];
  const last = entries[entries.length - 1];
  return (
    source.slice(0, first.index) +
    kept.map((m) => m[0]).join(",") +
    source.slice(last.index + last[0].length)
  );
}

/** @this {{ resourcePath: string, getOptions(): { keep: Record<string, readonly string[]> } }} */
function phosphorWeightsLoader(source) {
  const glyph = this.resourcePath
    .replace(/\\/g, "/")
    .split("/")
    .pop()
    .replace(/\.es\.js$/, "");
  const { keep } = this.getOptions();
  const extra = Object.keys(keep).filter((weight) => keep[weight].includes(glyph));
  return stripWeights(source, glyph, extra);
}

module.exports = phosphorWeightsLoader;
module.exports.stripWeights = stripWeights;
