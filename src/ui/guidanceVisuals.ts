export type GuidanceVisualVariant = "arc" | "loop" | "cloud" | "dashed" | "underline" | "note";

const variants: GuidanceVisualVariant[] = ["arc", "loop", "cloud", "dashed", "underline", "note"];

function hashKey(value: string): number {
  return Array.from(value).reduce((hash, char) => {
    return (hash * 31 + char.charCodeAt(0)) >>> 0;
  }, 17);
}

export function stableGuidanceVariant(key: string | undefined): GuidanceVisualVariant {
  if (!key) {
    return "cloud";
  }

  return variants[hashKey(key) % variants.length] ?? "cloud";
}
