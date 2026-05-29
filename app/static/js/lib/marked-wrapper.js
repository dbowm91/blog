// marked.min.js is loaded via <script> tag (UMD bundle).
// Access the global marked object set by the UMD wrapper.
const marked = globalThis.marked;

if (marked) {
  marked.setOptions({ gfm: true, breaks: false });
}

export { marked };
export default marked;