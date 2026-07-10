import { AppRoute } from "./navigation";

export function isAutomaticAnalysisEnabled(
  route: AppRoute,
  permissionGranted: boolean,
  processing: boolean,
  capturing: boolean
): boolean {
  return route === "camera" && permissionGranted && !processing && !capturing;
}
