const fs = require('fs');
const parser = require('@babel/parser');

try {
  const code = fs.readFileSync('c:\\Users\\rnlar\\.gemini\\antigravity\\scratch\\LexMatePH v3\\src\\frontend\\src\\features\\lexify\\LexifyDashboard.jsx', 'utf8');
  parser.parse(code, {
    sourceType: 'module',
    plugins: ['jsx']
  });
  console.log('SUCCESS: No syntax errors!');
} catch (e) {
  console.error('SYNTAX ERROR:', e.message);
  if (e.loc) {
    console.error(`At line ${e.loc.line}, column ${e.loc.column}`);
    const lines = fs.readFileSync('c:\\Users\\rnlar\\.gemini\antigravity\\scratch\\LexMatePH v3\\src\\frontend\\src\\features\\lexify\\LexifyDashboard.jsx', 'utf8').split('\n');
    console.error('Context:', lines[e.loc.line - 1]);
  }
}
