export const THEME_STORAGE_KEY = 'cornTheme'

export type ThemeId =
  | 'system'
  | 'graphite'
  | 'ocean'
  | 'forest'
  | 'amber'

export type ThemeMode = 'light' | 'dark' | 'system'

export interface ThemeSelection {
  palette: ThemeId
  mode: ThemeMode
}

export interface ThemeMetadata {
  id: ThemeId
  name: string
  description: string
}

export const DEFAULT_THEME_SELECTION: ThemeSelection = {
  palette: 'system',
  mode: 'dark', // 深色模式优先
}

export const THEME_METADATA: readonly ThemeMetadata[] = [
  {
    id: 'system',
    name: '清透青',
    description: '默认主题，清新的薄荷青色'
  },
  {
    id: 'graphite',
    name: '石墨灰',
    description: '专业稳重的灰色调'
  },
  {
    id: 'ocean',
    name: '海洋蓝',
    description: '深邃的海洋蓝'
  },
  {
    id: 'forest',
    name: '松林绿',
    description: '自然的森林绿'
  },
  {
    id: 'amber',
    name: '琥珀金',
    description: '温暖的琥珀金'
  },
] as const

const THEME_IDS = new Set<ThemeId>(THEME_METADATA.map(({ id }) => id))

function isValidThemeId(value: unknown): value is ThemeId {
  return typeof value === 'string' && THEME_IDS.has(value as ThemeId)
}

function isValidMode(value: unknown): value is ThemeMode {
  return value === 'light' || value === 'dark' || value === 'system'
}

export function loadThemeSelection(): ThemeSelection {
  if (typeof window === 'undefined' || typeof window.localStorage !== 'object') {
    return { ...DEFAULT_THEME_SELECTION }
  }

  try {
    const raw = window.localStorage.getItem(THEME_STORAGE_KEY)
    if (!raw) return { ...DEFAULT_THEME_SELECTION }

    const candidate = JSON.parse(raw)
    if (!candidate || typeof candidate !== 'object') {
      return { ...DEFAULT_THEME_SELECTION }
    }

    if (!isValidThemeId(candidate.palette) || !isValidMode(candidate.mode)) {
      return { ...DEFAULT_THEME_SELECTION }
    }

    return { palette: candidate.palette, mode: candidate.mode }
  } catch {
    return { ...DEFAULT_THEME_SELECTION }
  }
}

export function saveThemeSelection(selection: ThemeSelection): void {
  if (typeof window === 'undefined' || typeof window.localStorage !== 'object') return

  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(selection))
  } catch {
    // Ignore storage errors
  }
}

export function resolveSystemDarkMode(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function resolveDarkMode(selection: ThemeSelection): boolean {
  return selection.mode === 'dark' || (selection.mode === 'system' && resolveSystemDarkMode())
}

export function applyTheme(selection: ThemeSelection, isDark = resolveDarkMode(selection)): boolean {
  if (typeof document === 'undefined') return isDark

  const root = document.documentElement
  root.dataset.theme = selection.palette
  root.classList.toggle('dark', isDark)
  return isDark
}
