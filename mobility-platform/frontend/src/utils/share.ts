export function shareTrackUrl(tripId: string): string {
  return `${window.location.origin}/track/${encodeURIComponent(tripId)}`;
}

export async function copyShareLink(tripId: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(shareTrackUrl(tripId));
    return true;
  } catch {
    return false;
  }
}
