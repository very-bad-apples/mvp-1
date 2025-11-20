const http = require('http');
const fs = require('fs').promises;
const path = require('path');
const yaml = require('js-yaml');

const PORT = 3000;
const OUTPUT_DIR = path.join(__dirname, '../../backend/mv/director/configs');

const server = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.method === 'POST' && req.url === '/save') {
    let body = '';

    req.on('data', chunk => {
      body += chunk.toString();
    });

    req.on('end', async () => {
      try {
        const { templateName, format, template } = JSON.parse(body);

        // Validate
        if (!templateName || !/^[a-zA-Z0-9-_]+$/.test(templateName)) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid template name' }));
          return;
        }

        // Generate content
        const ext = format === 'json' ? 'json' : 'yaml';
        const content = format === 'json'
          ? JSON.stringify(template, null, 2)
          : yaml.dump(template, { indent: 2 });

        // Ensure output directory exists
        await fs.mkdir(OUTPUT_DIR, { recursive: true });

        // Save file
        const filename = `${templateName}.${ext}`;
        const filepath = path.join(OUTPUT_DIR, filename);
        await fs.writeFile(filepath, content, 'utf-8');

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: true,
          filename,
          path: filepath
        }));

      } catch (error) {
        console.error('Save error:', error);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: error.message }));
      }
    });
  } else {
    res.writeHead(404);
    res.end('Not found');
  }
});

server.listen(PORT, () => {
  console.log(`Save server running on http://localhost:${PORT}`);
  console.log(`Output directory: ${OUTPUT_DIR}`);
});

