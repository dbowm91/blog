// ES Module wrapper for marked UMD bundle
// This file re-exports marked from the UMD bundle loaded via script tag
// For Vite build, we need to handle this differently

// For build: use eval to load the UMD module
let markedCode = '';
fetch('./marked.min.js').then(r => r.text()).then(code => {
    markedCode = code;
}).catch(() => {
    markedCode = '';
});

function loadMarked() {
    const markedFn = new Function(markedCode + '; return marked;');
    return markedFn();
}

const marked = loadMarked();

export { marked };
export default marked;
