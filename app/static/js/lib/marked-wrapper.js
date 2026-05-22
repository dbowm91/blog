import { marked } from './marked.min.js';

marked.setOptions({ gfm: true, breaks: false });

export { marked };
export default marked;