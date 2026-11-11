// Runs the jsCode of one n8n Code node outside n8n, for the pytest suite.
//
// stdin:  { "workflow": "<path to workflow json>", "node": "<node name>",
//           "input": [ {...}, ... ],            // items arriving on the node's input
//           "nodes": { "<other node>": [ {...} ] } }   // what $('<other node>') returns
// stdout: JSON array with the .json of every item the node returned
//
// Only the n8n globals the workflows actually use are stubbed: $input and $().
const fs = require('fs');

const req = JSON.parse(fs.readFileSync(0, 'utf8'));
const workflow = JSON.parse(fs.readFileSync(req.workflow, 'utf8'));
const node = workflow.nodes.find((n) => n.name === req.node);
if (!node || !node.parameters || typeof node.parameters.jsCode !== 'string') {
  console.error(`No Code node named "${req.node}" in ${req.workflow}`);
  process.exit(2);
}

const wrap = (rows) => (rows || []).map((json) => ({ json }));
const accessor = (rows) => ({
  first: () => wrap(rows)[0],
  all: () => wrap(rows),
});
const $input = accessor(req.input);
const $ = (name) => {
  if (!req.nodes || !(name in req.nodes)) {
    throw new Error(`Test did not provide output for node "${name}"`);
  }
  return accessor(req.nodes[name]);
};

const run = new Function('$input', '$', node.parameters.jsCode);
const result = run($input, $);
process.stdout.write(JSON.stringify((result || []).map((item) => item.json)));
