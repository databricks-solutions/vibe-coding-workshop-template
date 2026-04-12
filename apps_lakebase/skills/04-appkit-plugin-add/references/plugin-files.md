# Files Plugin

**Upstream docs (always check for latest):** https://databricks.github.io/appkit/docs/plugins/files
Also consult the live AppKit docs: `npx @databricks/appkit docs "files"`
The information below may be outdated. Prefer upstream when available.

File operations against Databricks Unity Catalog Volumes with multi-volume support, streaming, and built-in caching.

**Capabilities:** List, read, download, upload, delete, and preview files. Multi-volume named aliases, streaming downloads, content-type resolution, XSS-safe inline serving, upload size limits, automatic cache invalidation, OBO user execution.

## Adding to an Existing AppKit Project

### 1. Register the Plugin

In `server/server.ts`:

```typescript
import { createApp, files, server } from "@databricks/appkit";

await createApp({
  plugins: [
    server(),
    files(),
  ],
});
```

### 2. Environment Variables

Set `DATABRICKS_VOLUME_*` env vars. The suffix becomes the volume key (lowercased).

Add to `.env`:

```env
DATABRICKS_VOLUME_UPLOADS=/Volumes/catalog/schema/uploads
DATABRICKS_VOLUME_EXPORTS=/Volumes/catalog/schema/exports
```

Add to `app.yaml`:

```yaml
env:
  - name: DATABRICKS_VOLUME_UPLOADS
    description: "UC Volume path for uploads"
    value: "/Volumes/catalog/schema/uploads"
  - name: DATABRICKS_VOLUME_EXPORTS
    description: "UC Volume path for exports"
    value: "/Volumes/catalog/schema/exports"
```

**Auto-discovery:** The plugin scans `process.env` for keys matching `DATABRICKS_VOLUME_*` and registers each as a volume automatically. No explicit `volumes` config needed.

### 3. Configuration Options

```typescript
files({
  maxUploadSize: 5_000_000_000, // 5 GB default for all volumes
  customContentTypes: { ".avro": "application/avro" },
  volumes: {
    uploads: { maxUploadSize: 100_000_000 },  // 100 MB for uploads
    exports: {},                               // uses plugin-level defaults
  },
});
```

### 4. Frontend Components

Composable file browser components:

```tsx
import {
  DirectoryList,
  FileBreadcrumb,
  FilePreviewPanel,
} from "@databricks/appkit-ui/react";

function FileBrowserPage() {
  return (
    <div style={{ display: "flex", gap: 16 }}>
      <div style={{ flex: 1 }}>
        <FileBreadcrumb
          rootLabel="uploads"
          segments={["data"]}
          onNavigateToRoot={() => {}}
          onNavigateToSegment={() => {}}
        />
        <DirectoryList
          entries={[]}
          onEntryClick={() => {}}
          resolveEntryPath={(entry) => entry.path ?? ""}
        />
      </div>
      <FilePreviewPanel selectedFile={null} preview={null} />
    </div>
  );
}
```

## HTTP Routes

All mounted under `/api/files/*`. The `:volumeKey` must match a configured volume.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/volumes` | List available volumes |
| GET | `/:volumeKey/list` | List directory contents |
| GET | `/:volumeKey/read?path=` | Read file as text |
| GET | `/:volumeKey/download?path=` | Download file (binary stream) |
| GET | `/:volumeKey/raw?path=` | Inline serve (safe types only) |
| GET | `/:volumeKey/exists?path=` | Check if file exists |
| GET | `/:volumeKey/metadata?path=` | File metadata |
| GET | `/:volumeKey/preview?path=` | File preview |
| POST | `/:volumeKey/upload?path=` | Upload file |
| POST | `/:volumeKey/mkdir` | Create directory |
| DELETE | `/:volumeKey?path=` | Delete file |

## Programmatic API (Server-Side)

```typescript
// OBO access (recommended)
const entries = await appkit.files("uploads").asUser(req).list();
const content = await appkit.files("exports").asUser(req).read("report.csv");

// Service principal access (logs a warning)
const entries = await appkit.files("uploads").list();
```

## Execution Defaults

| Tier | Cache | Retry | Timeout | Operations |
|------|-------|-------|---------|------------|
| Read | 60s | 3x | 30s | list, read, exists, metadata, preview |
| Download | none | 3x | 30s | download, raw |
| Write | none | none | 600s | upload, mkdir, delete |

Write operations automatically invalidate the cached `list` for the parent directory.

## Security

- Dangerous MIME types (`text/html`, `text/javascript`, `image/svg+xml`) are blocked on `/raw` to prevent stored XSS.
- Path traversal (`../`) is rejected.
- Max path length: 4096 characters.
