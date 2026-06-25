import { getConfig } from "../config";
import { WorkspaceService } from "../workspaceService";

const config = getConfig();
const service = new WorkspaceService(
  {
    root: config.workspaceRoot,
    schemaDir: config.schemaDir
  },
  {
    akdbUrl: config.akdbUrl,
    akdbProjectId: config.akdbProjectId,
    akdbExportRoot: config.akdbExportRoot,
    connectorsEnabled: config.connectorsEnabled
  }
);

try {
  const info = await service.info();
  console.log(JSON.stringify(info, null, 2));
} finally {
  await service.close();
}
