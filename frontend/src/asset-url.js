export function assetUrl(path, base) {
  if (!path) return null;
  return path.startsWith('https://') ? path : `${base}${path}`;
}
