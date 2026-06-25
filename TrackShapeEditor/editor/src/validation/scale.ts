export function scalePreview(rawM: number, targetM: number) {
  const factor = targetM / rawM;
  return { factor, scaledM: targetM, warn: factor < 0.75 || factor > 1.25 };
}
