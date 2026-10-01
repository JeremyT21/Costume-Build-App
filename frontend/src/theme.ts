import { useEffect, useState } from 'react';

import type { CostumeSummary } from './types';

export const DEFAULT_HUE = 262;
const SECOND_HUE_OFFSET = 78;
const THIRD_HUE_OFFSET = -44;
const SAMPLE_SIZE = 48;
const MIN_CHROMA_WEIGHT = 0.6;

let currentHue = DEFAULT_HUE;
const hueCache = new Map<string, number>();

interface HueVector {
  x: number;
  y: number;
  weight: number;
}

function addColor(vector: HueVector, r: number, g: number, b: number): void {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const chroma = max - min;
  if (chroma < 0.08) return;
  let hue: number;
  if (max === r) hue = ((g - b) / chroma) % 6;
  else if (max === g) hue = (b - r) / chroma + 2;
  else hue = (r - g) / chroma + 4;
  const radians = (hue * 60 * Math.PI) / 180;
  vector.x += Math.cos(radians) * chroma;
  vector.y += Math.sin(radians) * chroma;
  vector.weight += chroma;
}

function vectorHue(vector: HueVector): number | null {
  if (vector.weight < MIN_CHROMA_WEIGHT) return null;
  const degrees = (Math.atan2(vector.y, vector.x) * 180) / Math.PI;
  return Math.round((degrees + 360) % 360);
}

/** Dominant hue of hex colors, weighted toward vivid ones. */
export function hueFromHexColors(colors: string[]): number | null {
  const vector: HueVector = { x: 0, y: 0, weight: 0 };
  for (const color of colors) {
    const match = /^#?([0-9a-f]{6})$/i.exec(color.trim());
    if (!match) continue;
    const value = parseInt(match[1], 16);
    addColor(vector, (value >> 16) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255);
  }
  vector.weight *= 40;
  return vectorHue(vector);
}

/** Dominant hue of an image, sampled on a small canvas. */
export async function hueFromImage(url: string): Promise<number | null> {
  const cached = hueCache.get(url);
  if (cached !== undefined) return cached;
  const image = new Image();
  image.src = url;
  try {
    await image.decode();
  } catch {
    return null;
  }
  const canvas = document.createElement('canvas');
  canvas.width = SAMPLE_SIZE;
  canvas.height = SAMPLE_SIZE;
  const context = canvas.getContext('2d', { willReadFrequently: true });
  if (!context) return null;
  context.drawImage(image, 0, 0, SAMPLE_SIZE, SAMPLE_SIZE);
  const { data } = context.getImageData(0, 0, SAMPLE_SIZE, SAMPLE_SIZE);
  const vector: HueVector = { x: 0, y: 0, weight: 0 };
  for (let i = 0; i < data.length; i += 4) {
    addColor(vector, data[i] / 255, data[i + 1] / 255, data[i + 2] / 255);
  }
  const hue = vectorHue(vector);
  if (hue !== null) hueCache.set(url, hue);
  return hue;
}

/** Stable hue from text so every costume gets its own color. */
export function hueFromText(text: string): number {
  let hash = 0;
  for (const char of text) hash = (hash * 31 + char.charCodeAt(0)) | 0;
  return Math.abs(hash) % 360;
}

export async function costumeHue(
  costume: Pick<CostumeSummary, 'name' | 'image_urls'>,
  componentColors: string[] = [],
): Promise<number> {
  const fromColors = hueFromHexColors(componentColors);
  if (fromColors !== null) return fromColors;
  if (costume.image_urls[0]) {
    const fromImage = await hueFromImage(costume.image_urls[0]);
    if (fromImage !== null) return fromImage;
  }
  return hueFromText(costume.name);
}

/** Moves the app accent to a hue along the shortest way around the color wheel. */
export function applyAccentHue(hue: number): void {
  const delta = ((((hue - currentHue) % 360) + 540) % 360) - 180;
  currentHue += delta;
  const root = document.documentElement.style;
  root.setProperty('--accent-h', String(currentHue));
  root.setProperty('--accent-2-h', String(currentHue + SECOND_HUE_OFFSET));
  root.setProperty('--accent-3-h', String(currentHue + THIRD_HUE_OFFSET));
}

export function resetAccentHue(): void {
  applyAccentHue(DEFAULT_HUE);
}

/** Tints the whole app with a costume's color while it is on screen. */
export function useCostumeTheme(
  costume: Pick<CostumeSummary, 'name' | 'image_urls'> | null,
  componentColors: string[],
): void {
  const key = costume ? `${costume.name}|${costume.image_urls[0] ?? ''}|${componentColors.join()}` : '';

  useEffect(() => {
    if (!costume) return;
    let active = true;
    costumeHue(costume, componentColors).then((hue) => active && applyAccentHue(hue));
    return () => {
      active = false;
    };
    // The key captures every input that changes the hue.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => resetAccentHue, []);
}

/** Resolves one costume's hue for per-card tinting. */
export function useCostumeHue(costume: Pick<CostumeSummary, 'name' | 'image_urls'>): number {
  const [hue, setHue] = useState(() => hueFromText(costume.name));
  useEffect(() => {
    let active = true;
    costumeHue(costume).then((value) => active && setHue(value));
    return () => {
      active = false;
    };
  }, [costume]);
  return hue;
}
