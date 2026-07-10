export interface CapturedPhoto {
  uri: string;
  width: number;
  height: number;
  source: "camera" | "library";
}
