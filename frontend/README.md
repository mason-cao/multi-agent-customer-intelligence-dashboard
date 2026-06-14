# Nova Core Frontend

React, TypeScript, Vite, Tailwind CSS, Recharts, and TanStack Query frontend for Nova Core.

```bash
npm install
npm run dev
```

Owner access is set up from the Workspaces screen by default. Use **Start Demo
Workspace** to explore without owner access, or **Owner Mode** to create or
enter the owner passcode.

`VITE_ADMIN_API_TOKEN` is optional. Use it only for trusted admin-only frontend
deployments where the backend also has the same `ADMIN_API_TOKEN` configured.

The frontend sends admin and workspace credentials through `src/api/client.ts`.
