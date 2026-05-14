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

function isPresentablePath(p) {
  if (!p) return false
  const lower = p.toLowerCase()
  if (lower.endsWith('.gif')) return false
  if (lower.includes('_thumb')) return false
  return true
}

export function imageUrls(item) {
  const origins = item?.images_origin
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

export function firstImageUrl(item) {
  return imageUrls(item)[0] || null
}

export function originalAuctionUrl(itemNo) {
  return `${SHELL_IMAGE_BASE}auction_shell.php?id=${itemNo}&pres=1`
}
