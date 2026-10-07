import fs from 'fs';
import path from 'path';

export function discoverRoutes(): string[] {
  const appDir = path.resolve(process.cwd(), 'src/app');
  if (!fs.existsSync(appDir)) {
    throw new Error('Could not find src/app directory');
  }

  const routes: Set<string> = new Set();

  function scan(dir: string, currentPath: string = '') {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      if (entry.isDirectory()) {
        const nextDir = path.join(dir, entry.name);
        
        let nextPath = currentPath;
        // Ignore route groups like (auth)
        if (!entry.name.startsWith('(') && !entry.name.endsWith(')')) {
          nextPath = currentPath + '/' + entry.name;
        }

        scan(nextDir, nextPath);
      } else if (entry.isFile() && /^page\.(tsx|ts|jsx|js)$/.test(entry.name)) {
        // We found a page
        let finalPath = currentPath || '/';
        
        // Handle dynamic segments with mock IDs
        finalPath = finalPath.replace(/\[patientId\]/g, 'user-patient-001');
        finalPath = finalPath.replace(/\[reportId\]/g, 'report-001'); // Assuming report-001 is a valid format based on user-patient-001, but the app uses it correctly.
        finalPath = finalPath.replace(/\[organizationId\]/g, 'org-001');
        finalPath = finalPath.replace(/\[userId\]/g, 'user-admin-001');
        finalPath = finalPath.replace(/\[doctorId\]/g, 'user-doctor-001');

        routes.add(finalPath);
      }
    }
  }

  scan(appDir);
  return Array.from(routes).sort();
}
