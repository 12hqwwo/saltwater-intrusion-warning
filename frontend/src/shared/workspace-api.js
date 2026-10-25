import { requestJSON } from "../api.js";

export const workspaceAPI = (path, options) => requestJSON("/workspace" + path, options);
export const artifactURL = (id, name) => `/api/v1/workspace/artifacts/${encodeURIComponent(id)}/${encodeURIComponent(name)}`;
