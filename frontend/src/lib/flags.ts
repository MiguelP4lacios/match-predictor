/**
 * lib/flags — name → emoji flag para las 48 selecciones del WC26.
 * Función pura; no lanza excepciones.
 *
 * Estrategia:
 *  1. Overrides por nombre para selecciones sin ISO-3166-1 (England, Scotland).
 *  2. Lookup name→ISO2 para las 46 restantes.
 *  3. Conversión ISO2 → regional indicator emoji (codepoints U+1F1E6…U+1F1FF).
 *  4. Fallback: 🏳 para nombres desconocidos.
 */

// Overrides explícitos para subdivisiones del Reino Unido (tag emoji)
// England: 🏴󠁧󠁢󠁥󠁮󠁧󠁿  Scotland: 🏴󠁧󠁢󠁳󠁣󠁴󠁿
const NAME_OVERRIDES: Record<string, string> = {
  England: '\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}',
  Scotland: '\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}',
}

// Mapa canónico name → ISO-3166-1 alpha-2 (48 selecciones WC26)
const NAME_TO_ISO2: Record<string, string> = {
  Algeria: 'DZ',
  Argentina: 'AR',
  Australia: 'AU',
  Austria: 'AT',
  Belgium: 'BE',
  'Bosnia and Herzegovina': 'BA',
  Brazil: 'BR',
  Canada: 'CA',
  'Cape Verde': 'CV',
  Colombia: 'CO',
  Croatia: 'HR',
  'Curaçao': 'CW',
  'Czech Republic': 'CZ',
  'DR Congo': 'CD',
  Ecuador: 'EC',
  Egypt: 'EG',
  France: 'FR',
  Germany: 'DE',
  Ghana: 'GH',
  Haiti: 'HT',
  Iran: 'IR',
  Iraq: 'IQ',
  'Ivory Coast': 'CI',
  Japan: 'JP',
  Jordan: 'JO',
  Mexico: 'MX',
  Morocco: 'MA',
  Netherlands: 'NL',
  'New Zealand': 'NZ',
  Norway: 'NO',
  Panama: 'PA',
  Paraguay: 'PY',
  Portugal: 'PT',
  Qatar: 'QA',
  'Saudi Arabia': 'SA',
  Senegal: 'SN',
  'South Africa': 'ZA',
  'South Korea': 'KR',
  Spain: 'ES',
  Sweden: 'SE',
  Switzerland: 'CH',
  Tunisia: 'TN',
  Turkey: 'TR',
  'United States': 'US',
  Uruguay: 'UY',
  Uzbekistan: 'UZ',
}

/**
 * Convierte un código ISO-3166-1 alpha-2 a su emoji de bandera
 * usando regional indicator symbols (U+1F1E6…U+1F1FF).
 */
function iso2ToEmoji(iso2: string): string {
  // Regional Indicator A = U+1F1E6 = 127462; 'A'.charCodeAt(0) = 65
  const base = 0x1f1e6 - 0x41
  return [...iso2.toUpperCase()]
    .map((c) => String.fromCodePoint(base + c.charCodeAt(0)))
    .join('')
}

/**
 * Devuelve la bandera emoji para el nombre canónico de un equipo WC26.
 * Nunca lanza excepciones.
 */
export function nameToFlag(name: string): string {
  if (name in NAME_OVERRIDES) return NAME_OVERRIDES[name]
  const iso2 = NAME_TO_ISO2[name]
  if (!iso2) return '🏳'
  return iso2ToEmoji(iso2)
}
