// Hotspot Portal Data Collection Server
// Run with: node server.js
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8081;
const DATA_DIR = path.join(__dirname, 'data');

fs.mkdirSync(DATA_DIR, { recursive: true });

const server = http.createServer((req, res) => {
    // CORS headers so the browser allows cross-origin requests
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    if (req.method === 'POST' && req.url === '/collect') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            // One file per day: YYYY-MM-DD.csv
            const date = new Date().toISOString().slice(0, 10);
            const filepath = path.join(DATA_DIR, date + '.csv');

            // If file doesn't exist, write full body (includes headers)
            // If it exists, append only the data row (last line) with a newline
            if (!fs.existsSync(filepath)) {
                fs.writeFileSync(filepath, body);
            } else {
                const lines = body.trim().split('\n');
                const dataRow = lines[lines.length - 1];
                // Ensure file ends with newline before appending
                const existing = fs.readFileSync(filepath, 'utf8');
                const needsNewline = existing.length > 0 && !existing.endsWith('\n');
                fs.appendFileSync(filepath, (needsNewline ? '\n' : '') + dataRow + '\n');
            }

            console.log(`[${new Date().toISOString()}] Data saved to ${filepath}`);
            console.log('--- Received CSV ---');
            console.log(body);
            console.log('---------------------');

            res.writeHead(200, { 'Content-Type': 'text/plain' });
            res.end('OK');
        });
    } else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not found');
    }
});

server.listen(PORT, '0.0.0.0', () => {
    console.log('========================================');
    console.log(' Hotspot Portal Data Collection Server');
    console.log('========================================');
    console.log(` Listening on: 0.0.0.0:${PORT}`);
    console.log(` Endpoint:    POST /collect`);
    console.log(` Data folder:  ${DATA_DIR}`);
    console.log('========================================');
});
