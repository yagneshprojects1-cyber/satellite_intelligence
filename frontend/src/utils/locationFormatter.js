/**
 * Location & Tile Name Formatter Utility
 * Converts technical satellite tile IDs & UUIDs into human-understandable geographic titles
 */

export function formatLocationTitle(tileId, latitude, longitude, year = null) {
  if (!tileId && (!latitude || !longitude)) return "Unknown Geographic Sector"

  // Check if tileId contains Sentinel-2 MGRS grid designator (e.g. T43QFV)
  const mgrsMatch = tileId ? tileId.match(/T[0-9]{2}[A-Z]{3}/i) : null
  const numMatch = tileId ? tileId.match(/000[0-9]{3}|[0-9]{3,6}$/) : null
  const yearMatch = year || (tileId ? tileId.match(/^20[2-9][0-9]/) : null)

  let namePart = ""
  if (mgrsMatch && numMatch) {
    namePart = `Grid ${mgrsMatch[0].toUpperCase()} • Zone #${numMatch[0].replace(/^0+/, '')}`
  } else if (mgrsMatch) {
    namePart = `Grid ${mgrsMatch[0].toUpperCase()}`
  } else if (latitude && longitude) {
    namePart = `Sector (${Number(latitude).toFixed(2)}°N, ${Number(longitude).toFixed(2)}°E)`
  } else {
    namePart = `Satellite Sector ${tileId ? tileId.slice(0, 12) : ''}`
  }

  return yearMatch ? `${namePart} (${yearMatch[0] || yearMatch})` : namePart
}

export function formatPairTitle(pairId, beforeDate = '', afterDate = '', latitude = null, longitude = null) {
  if (!pairId) return "Multi-Temporal Pair Comparison"

  // Check if pairId is UUID or tile_vs_tile
  const parts = pairId.split('_vs_')
  const beforePart = parts[0] || ''
  
  const mgrsMatch = beforePart ? beforePart.match(/T[0-9]{2}[A-Z]{3}/i) : null
  const numMatch = beforePart ? beforePart.match(/000[0-9]{3}|[0-9]{3,6}$/) : null

  let sectorName = "Observation Sector"
  if (mgrsMatch && numMatch) {
    sectorName = `Grid ${mgrsMatch[0].toUpperCase()} • Zone #${numMatch[0].replace(/^0+/, '')}`
  } else if (latitude && longitude) {
    sectorName = `Sector (${Number(latitude).toFixed(2)}°N, ${Number(longitude).toFixed(2)}°E)`
  }

  const bYear = beforeDate ? beforeDate.slice(0, 4) : 'Baseline'
  const aYear = afterDate ? afterDate.slice(0, 4) : 'Latest'

  return `${sectorName} • ${bYear} vs. ${aYear}`
}

export function formatDateFriendly(dateStr) {
  if (!dateStr) return 'N/A'
  try {
    const dt = new Date(dateStr)
    if (isNaN(dt.getTime())) return dateStr
    return dt.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch (e) {
    return dateStr
  }
}
