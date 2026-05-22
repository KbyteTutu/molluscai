import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function formatNumber(n) {
  if (n === null || n === undefined) return '-'
  return new Intl.NumberFormat('zh-CN').format(n)
}

export function formatPrice(n) {
  if (n === null || n === undefined || n === '') return null
  const num = typeof n === 'string' ? parseFloat(n) : n
  if (Number.isNaN(num)) return null
  return '€' + num.toFixed(2)
}

export function formatDate(s) {
  if (!s) return '-'
  try {
    return new Date(s).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch {
    return s
  }
}

const SHELL_IMAGE_BASE = 'https://shellauction.net/'
const MINIO_BASE = '/minio/'

function isPresentablePath(p) {
  if (!p) return false
  const lower = p.toLowerCase()
  if (lower.endsWith('.gif')) return false
  if (lower.includes('_thumb')) return false
  return true
}

export function imageUrls(item) {
  const locals = item?.images_local
  const origins = item?.images_origin

  if (Array.isArray(locals) && locals.length) {
    return locals.map(p => MINIO_BASE + p)
  }

  if (!Array.isArray(origins) || !origins.length) return []
  const seen = new Set()
  const out = []
  for (const raw of origins) {
    for (const part of raw.split(';')) {
      const p = part.trim()
      if (!isPresentablePath(p)) continue
      const url = SHELL_IMAGE_BASE + p.replace(/^\//, '')
      if (seen.has(url)) continue
      seen.add(url)
      out.push(url)
    }
  }
  return out
}

export function imageUrlsWithFallback(item) {
  const locals = item?.images_local
  const origins = item?.images_origin

  const cachedUrls = Array.isArray(locals) && locals.length
    ? locals.map(p => MINIO_BASE + p)
    : []

  const originUrls = []
  if (Array.isArray(origins) && origins.length) {
    const seen = new Set()
    for (const raw of origins) {
      for (const part of raw.split(';')) {
        const p = part.trim()
        if (!isPresentablePath(p)) continue
        const url = SHELL_IMAGE_BASE + p.replace(/^\//, '')
        if (!seen.has(url)) { seen.add(url); originUrls.push(url) }
      }
    }
  }

  const len = Math.max(cachedUrls.length, originUrls.length)
  const out = []
  for (let i = 0; i < len; i++) {
    out.push({ cached: cachedUrls[i] || null, origin: originUrls[i] || null })
  }
  return out
}

export function firstImageUrl(item) {
  const locals = item?.images_local
  if (Array.isArray(locals) && locals.length) return MINIO_BASE + locals[0]
  return imageUrls(item)[0] || null
}

export function firstImagePair(item) {
  const pairs = imageUrlsWithFallback(item)
  return pairs[0] || { cached: null, origin: null }
}

export function originalAuctionUrl(itemNo) {
  return `${SHELL_IMAGE_BASE}auction_shell.php?id=${itemNo}&pres=1`
}

const XOR_KEY = 'tukechao'

export function xorId(itemNo) {
  const s = String(itemNo)
  let result = ''
  for (let i = 0; i < s.length; i++) {
    result += (s.charCodeAt(i) ^ XOR_KEY.charCodeAt(i % XOR_KEY.length)).toString(16).padStart(2, '0')
  }
  return result.toUpperCase()
}

export function decodeXorId(encoded) {
  let result = ''
  for (let i = 0; i < encoded.length; i += 2) {
    const code = parseInt(encoded.substr(i, 2), 16) ^ XOR_KEY.charCodeAt((i / 2) % XOR_KEY.length)
    result += String.fromCharCode(code)
  }
  return result
}
