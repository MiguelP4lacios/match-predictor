"""Tabla Anexo C del Mundial 2026 — asignación de 3ros clasificados a slots del R32.

Fuente: Reglamento Oficial de Competición FIFA WC 2026, Anexo C (págs. 80-97).

ANNEX_C: dict[frozenset[str], dict[str, str]]
  Clave:  frozenset con las 8 letras de grupo que clasifican como 3eros
  Valor:  mapa de slot → letra del grupo cuyo 3er clasificado ocupa ese slot

Slots (ganadores de grupo que se enfrentan a un 3er clasificado en el R32):
  "1A" → M79   "1B" → M85   "1D" → M81   "1E" → M74
  "1G" → M82   "1I" → M77   "1K" → M87   "1L" → M80

Uso en el Monte Carlo:
  1. Después de simular la fase de grupos, determinar los 8 mejores 3eros.
  2. Obtener sus 8 letras de grupo.
  3. ANNEX_C[frozenset(letras)] → mapa de slots.
  4. Aplicar: el 3er clasificado del grupo X ocupa el slot cuyo valor es X.
"""

# Orden de slots (columnas en la tabla oficial):
_SLOTS = ("1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L")

# 495 filas — cada string de 8 letras sigue el orden de _SLOTS.
# Extraídas del Anexo C oficial (verificado C(12,8)=495 combinaciones únicas).
_RAW: list[str] = [
    # 1-9: sin A, sin B, sin C (grupos D-L)
    "EJIFHGLK",  # 1  {E,F,G,H,I,J,K,L}
    "HGIDJFLK",  # 2  {D,F,G,H,I,J,K,L}
    "EJIDHGLK",  # 3  {D,E,G,H,I,J,K,L}
    "EJIDHFLK",  # 4  {D,E,F,H,I,J,K,L}
    "EGIDJFLK",  # 5  {D,E,F,G,I,J,K,L}
    "EGJDHFLK",  # 6  {D,E,F,G,H,J,K,L}
    "EGIDHFLK",  # 7  {D,E,F,G,H,I,K,L}
    "EGJDHFLI",  # 8  {D,E,F,G,H,I,J,L}
    "EGJDHFIK",  # 9  {D,E,F,G,H,I,J,K}
    # 10-18: sin A, sin B (grupos C-L)
    "HGICJFLK",  # 10 {C,F,G,H,I,J,K,L}
    "EJICHGLK",  # 11 {C,E,G,H,I,J,K,L}
    "EJICHFLK",  # 12 {C,E,F,H,I,J,K,L}
    "EGICJFLK",  # 13 {C,E,F,G,I,J,K,L}
    "EGJCHFLK",  # 14 {C,E,F,G,H,J,K,L}
    "EGICHFLK",  # 15 {C,E,F,G,H,I,K,L}
    "EGJCHFLI",  # 16 {C,E,F,G,H,I,J,L}
    "EGJCHFIK",  # 17 {C,E,F,G,H,I,J,K}
    "HGICJDLK",  # 18 {C,D,G,H,I,J,K,L}
    # 19-45: C present, no A, no B
    "CJIDHFLK",  # 19 {C,D,F,H,I,J,K,L}
    "CGIDJFLK",  # 20 {C,D,F,G,I,J,K,L}
    "CGJDHFLK",  # 21 {C,D,F,G,H,J,K,L}
    "CGIDHFLK",  # 22 {C,D,F,G,H,I,K,L}
    "CGJDHFLI",  # 23 {C,D,F,G,H,I,J,L}
    "CGJDHFIK",  # 24 {C,D,F,G,H,I,J,K}
    "EJICHDLK",  # 25 {C,D,E,H,I,J,K,L}
    "EGICJDLK",  # 26 {C,D,E,G,I,J,K,L}
    "EGJCHDLK",  # 27 {C,D,E,G,H,J,K,L}
    "EGICHDLK",  # 28 {C,D,E,G,H,I,K,L}
    "EGJCHDLI",  # 29 {C,D,E,G,H,I,J,L}
    "EGJCHDIK",  # 30 {C,D,E,G,H,I,J,K}
    "CJEDIFLK",  # 31 {C,D,E,F,I,J,K,L}
    "CJEDHFLK",  # 32 {C,D,E,F,H,J,K,L}
    "CEIDHFLK",  # 33 {C,D,E,F,H,I,K,L}
    "CJEDHFLI",  # 34 {C,D,E,F,H,I,J,L}
    "CJEDHFIK",  # 35 {C,D,E,F,H,I,J,K}
    "CGEDJFLK",  # 36 {C,D,E,F,G,J,K,L}
    "CGEDIFLK",  # 37 {C,D,E,F,G,I,K,L}
    "CGEDJFLI",  # 38 {C,D,E,F,G,I,J,L}
    "CGEDJFIK",  # 39 {C,D,E,F,G,I,J,K}
    "CGEDHFLK",  # 40 {C,D,E,F,G,H,K,L}
    "CGJDHFLE",  # 41 {C,D,E,F,G,H,J,L}
    "CGJDHFEK",  # 42 {C,D,E,F,G,H,J,K}
    "CGEDHFLI",  # 43 {C,D,E,F,G,H,I,L}
    "CGEDHFIK",  # 44 {C,D,E,F,G,H,I,K}
    "CGJDHFEI",  # 45 {C,D,E,F,G,H,I,J}
    # 46-165: B present, no A
    "HJBFIGLK",  # 46 {B,F,G,H,I,J,K,L}
    "EJIBHGLK",  # 47 {B,E,G,H,I,J,K,L}
    "EJBFIHLK",  # 48 {B,E,F,H,I,J,K,L}
    "EJBFIGLK",  # 49 {B,E,F,G,I,J,K,L}
    "EJBFHGLK",  # 50 {B,E,F,G,H,J,K,L}
    "EGBFIHLK",  # 51 {B,E,F,G,H,I,K,L}
    "EJBFHGLI",  # 52 {B,E,F,G,H,I,J,L}
    "EJBFHGIK",  # 53 {B,E,F,G,H,I,J,K}
    "HJBDIGLK",  # 54 {B,D,G,H,I,J,K,L}
    "HJBDIFLK",  # 55 {B,D,F,H,I,J,K,L}
    "IGBDJFLK",  # 56 {B,D,F,G,I,J,K,L}
    "HGBDJFLK",  # 57 {B,D,F,G,H,J,K,L}
    "HGBDIFLK",  # 58 {B,D,F,G,H,I,K,L}
    "HGBDJFLI",  # 59 {B,D,F,G,H,I,J,L}
    "HGBDJFIK",  # 60 {B,D,F,G,H,I,J,K}
    "EJBDIHLK",  # 61 {B,D,E,H,I,J,K,L}
    "EJBDIGLK",  # 62 {B,D,E,G,I,J,K,L}
    "EJBDHGLK",  # 63 {B,D,E,G,H,J,K,L}
    "EGBDIHLK",  # 64 {B,D,E,G,H,I,K,L}
    "EJBDHGLI",  # 65 {B,D,E,G,H,I,J,L}
    "EJBDHGIK",  # 66 {B,D,E,G,H,I,J,K}
    "EJBDIFLK",  # 67 {B,D,E,F,I,J,K,L}
    "EJBDHFLK",  # 68 {B,D,E,F,H,J,K,L}
    "EIBDHFLK",  # 69 {B,D,E,F,H,I,K,L}
    "EJBDHFLI",  # 70 {B,D,E,F,H,I,J,L}
    "EJBDHFIK",  # 71 {B,D,E,F,H,I,J,K}
    "EGBDJFLK",  # 72 {B,D,E,F,G,J,K,L}
    "EGBDIFLK",  # 73 {B,D,E,F,G,I,K,L}
    "EGBDJFLI",  # 74 {B,D,E,F,G,I,J,L}
    "EGBDJFIK",  # 75 {B,D,E,F,G,I,J,K}
    "EGBDHFLK",  # 76 {B,D,E,F,G,H,K,L}
    "HGBDJFLE",  # 77 {B,D,E,F,G,H,J,L}
    "HGBDJFEK",  # 78 {B,D,E,F,G,H,J,K}
    "EGBDHFLI",  # 79 {B,D,E,F,G,H,I,L}
    "EGBDHFIK",  # 80 {B,D,E,F,G,H,I,K}
    "HGBDJFEI",  # 81 {B,D,E,F,G,H,I,J}
    "HJBCIGLK",  # 82 {B,C,G,H,I,J,K,L}
    "HJBCIFLK",  # 83 {B,C,F,H,I,J,K,L}
    "IGBCJFLK",  # 84 {B,C,F,G,I,J,K,L}
    "HGBCJFLK",  # 85 {B,C,F,G,H,J,K,L}
    "HGBCIFLK",  # 86 {B,C,F,G,H,I,K,L}
    "HGBCJFLI",  # 87 {B,C,F,G,H,I,J,L}
    "HGBCJFIK",  # 88 {B,C,F,G,H,I,J,K}
    "EJBCIHLK",  # 89 {B,C,E,H,I,J,K,L}
    "EJBCIGLK",  # 90 {B,C,E,G,I,J,K,L}
    "EJBCHGLK",  # 91 {B,C,E,G,H,J,K,L}
    "EGBCIHLK",  # 92 {B,C,E,G,H,I,K,L}
    "EJBCHGLI",  # 93 {B,C,E,G,H,I,J,L}
    "EJBCHGIK",  # 94 {B,C,E,G,H,I,J,K}
    "EJBCIFLK",  # 95 {B,C,E,F,I,J,K,L}
    "EJBCHFLK",  # 96 {B,C,E,F,H,J,K,L}
    "EIBCHFLK",  # 97 {B,C,E,F,H,I,K,L}
    "EJBCHFLI",  # 98 {B,C,E,F,H,I,J,L}
    "EJBCHFIK",  # 99 {B,C,E,F,H,I,J,K}
    "EGBCJFLK",  # 100 {B,C,E,F,G,J,K,L}
    "EGBCIFLK",  # 101 {B,C,E,F,G,I,K,L}
    "EGBCJFLI",  # 102 {B,C,E,F,G,I,J,L}
    "EGBCJFIK",  # 103 {B,C,E,F,G,I,J,K}
    "EGBCHFLK",  # 104 {B,C,E,F,G,H,K,L}
    "HGBCJFLE",  # 105 {B,C,E,F,G,H,J,L}
    "HGBCJFEK",  # 106 {B,C,E,F,G,H,J,K}
    "EGBCHFLI",  # 107 {B,C,E,F,G,H,I,L}
    "EGBCHFIK",  # 108 {B,C,E,F,G,H,I,K}
    "HGBCJFEI",  # 109 {B,C,E,F,G,H,I,J}
    "HJBCIDLK",  # 110 {B,C,D,H,I,J,K,L}
    "IGBCJDLK",  # 111 {B,C,D,G,I,J,K,L}
    "HGBCJDLK",  # 112 {B,C,D,G,H,J,K,L}
    "HGBCIDLK",  # 113 {B,C,D,G,H,I,K,L}
    "HGBCJDLI",  # 114 {B,C,D,G,H,I,J,L}
    "HGBCJDIK",  # 115 {B,C,D,G,H,I,J,K}
    "CJBDIFLK",  # 116 {B,C,D,F,I,J,K,L}
    "CJBDHFLK",  # 117 {B,C,D,F,H,J,K,L}
    "CIBDHFLK",  # 118 {B,C,D,F,H,I,K,L}
    "CJBDHFLI",  # 119 {B,C,D,F,H,I,J,L}
    "CJBDHFIK",  # 120 {B,C,D,F,H,I,J,K}
    "CGBDJFLK",  # 121 {B,C,D,F,G,J,K,L}
    "CGBDIFLK",  # 122 {B,C,D,F,G,I,K,L}
    "CGBDJFLI",  # 123 {B,C,D,F,G,I,J,L}
    "CGBDJFIK",  # 124 {B,C,D,F,G,I,J,K}
    "CGBDHFLK",  # 125 {B,C,D,F,G,H,K,L}
    "CGBDHFLJ",  # 126 {B,C,D,F,G,H,J,L}
    "HGBCJFDK",  # 127 {B,C,D,F,G,H,J,K}
    "CGBDHFLI",  # 128 {B,C,D,F,G,H,I,L}
    "CGBDHFIK",  # 129 {B,C,D,F,G,H,I,K}
    "HGBCJFDI",  # 130 {B,C,D,F,G,H,I,J}
    "EJBCIDLK",  # 131 {B,C,D,E,I,J,K,L}
    "EJBCHDLK",  # 132 {B,C,D,E,H,J,K,L}
    "EIBCHDLK",  # 133 {B,C,D,E,H,I,K,L}
    "EJBCHDLI",  # 134 {B,C,D,E,H,I,J,L}
    "EJBCHDIK",  # 135 {B,C,D,E,H,I,J,K}
    "EGBCJDLK",  # 136 {B,C,D,E,G,J,K,L}
    "EGBCIDLK",  # 137 {B,C,D,E,G,I,K,L}
    "EGBCJDLI",  # 138 {B,C,D,E,G,I,J,L}
    "EGBCJDIK",  # 139 {B,C,D,E,G,I,J,K}
    "EGBCHDLK",  # 140 {B,C,D,E,G,H,K,L}
    "HGBCJDLE",  # 141 {B,C,D,E,G,H,J,L}
    "HGBCJDEK",  # 142 {B,C,D,E,G,H,J,K}
    "EGBCHDLI",  # 143 {B,C,D,E,G,H,I,L}
    "EGBCHDIK",  # 144 {B,C,D,E,G,H,I,K}
    "HGBCJDEI",  # 145 {B,C,D,E,G,H,I,J}
    "CJBDEFLK",  # 146 {B,C,D,E,F,J,K,L}
    "CEBDIFLK",  # 147 {B,C,D,E,F,I,K,L}
    "CJBDEFLI",  # 148 {B,C,D,E,F,I,J,L}
    "CJBDEFIK",  # 149 {B,C,D,E,F,I,J,K}
    "CEBDHFLK",  # 150 {B,C,D,E,F,H,K,L}
    "CJBDHFLE",  # 151 {B,C,D,E,F,H,J,L}
    "CJBDHFEK",  # 152 {B,C,D,E,F,H,J,K}
    "CEBDHFLI",  # 153 {B,C,D,E,F,H,I,L}
    "CEBDHFIK",  # 154 {B,C,D,E,F,H,I,K}
    "CJBDHFEI",  # 155 {B,C,D,E,F,H,I,J}
    "CGBDEFLK",  # 156 {B,C,D,E,F,G,K,L}
    "CGBDJFLE",  # 157 {B,C,D,E,F,G,J,L}
    "CGBDJFEK",  # 158 {B,C,D,E,F,G,J,K}
    "CGBDEFLI",  # 159 {B,C,D,E,F,G,I,L}
    "CGBDEFIK",  # 160 {B,C,D,E,F,G,I,K}
    "CGBDJFEI",  # 161 {B,C,D,E,F,G,I,J}
    "CGBDHFLE",  # 162 {B,C,D,E,F,G,H,L}
    "CGBDHFEK",  # 163 {B,C,D,E,F,G,H,K}
    "HGBCJFDE",  # 164 {B,C,D,E,F,G,H,J}
    "CGBDHFEI",  # 165 {B,C,D,E,F,G,H,I}
    # 166-285: A present, no B
    "HJIFAGLK",  # 166 {A,F,G,H,I,J,K,L}
    "EJIAХGLK",  # 167 placeholder — replaced below
    "EJIFAHLK",  # 168 {A,E,F,H,I,J,K,L}  (1B slot = J, 1E slot = F, 1G slot = A...)
    "EJIFAGLK",  # 169 {A,E,F,G,I,J,K,L}
    "EGJFAHLK",  # 170 {A,E,F,G,H,J,K,L}
    "EGIFAHLK",  # 171 {A,E,F,G,H,I,K,L}
    "EGJFAHLI",  # 172 {A,E,F,G,H,I,J,L}
    "EGJFAHIK",  # 173 {A,E,F,G,H,I,J,K}
    "HJIDAGLK",  # 174 {A,D,G,H,I,J,K,L}
    "HJIDAFLK",  # 175 {A,D,F,H,I,J,K,L}
    "IGJDAFLK",  # 176 {A,D,F,G,I,J,K,L}
    "HGJDAFLK",  # 177 {A,D,F,G,H,J,K,L}
    "HGIDAFLK",  # 178 {A,D,F,G,H,I,K,L}
    "HGJDAFLI",  # 179 {A,D,F,G,H,I,J,L}
    "HGJDAFIK",  # 180 {A,D,F,G,H,I,J,K}
    "EJIDAHLK",  # 181 {A,D,E,H,I,J,K,L}
    "EJIDAGLK",  # 182 {A,D,E,G,I,J,K,L}
    "EGJDAHLK",  # 183 {A,D,E,G,H,J,K,L}
    "EGIDAHLK",  # 184 {A,D,E,G,H,I,K,L}
    "EGJDAHLI",  # 185 {A,D,E,G,H,I,J,L}
    "EGJDAHIK",  # 186 {A,D,E,G,H,I,J,K}
    "EJIDAFLK",  # 187 {A,D,E,F,I,J,K,L}
    "HJEDAFLK",  # 188 {A,D,E,F,H,J,K,L}
    "HEIDAFLK",  # 189 {A,D,E,F,H,I,K,L}
    "HJEDAFLI",  # 190 {A,D,E,F,H,I,J,L}
    "HJEDAFIK",  # 191 {A,D,E,F,H,I,J,K}
    "EGJDAFLK",  # 192 {A,D,E,F,G,J,K,L}
    "EGIDAFLK",  # 193 {A,D,E,F,G,I,K,L}
    "EGJDAFLI",  # 194 {A,D,E,F,G,I,J,L}
    "EGJDAFIK",  # 195 {A,D,E,F,G,I,J,K}
    "HGEDAFLK",  # 196 {A,D,E,F,G,H,K,L}
    "HGJDAFLE",  # 197 {A,D,E,F,G,H,J,L}
    "HGJDAFEK",  # 198 {A,D,E,F,G,H,J,K}
    "HGEDAFLI",  # 199 {A,D,E,F,G,H,I,L}
    "HGEDAFIK",  # 200 {A,D,E,F,G,H,I,K}
    "HGJDAFEI",  # 201 {A,D,E,F,G,H,I,J}
    "HJICAGLK",  # 202 {A,C,G,H,I,J,K,L}
    "HJICAFLK",  # 203 {A,C,F,H,I,J,K,L}
    "IGJCAFLK",  # 204 {A,C,F,G,I,J,K,L}
    "HGJCAFLK",  # 205 {A,C,F,G,H,J,K,L}
    "HGICAFLK",  # 206 {A,C,F,G,H,I,K,L}
    "HGJCAFLI",  # 207 {A,C,F,G,H,I,J,L}
    "HGJCAFIK",  # 208 {A,C,F,G,H,I,J,K}
    "EJICAHLK",  # 209 {A,C,E,H,I,J,K,L}
    "EJICAGLK",  # 210 {A,C,E,G,I,J,K,L}
    "EGJCAHLK",  # 211 {A,C,E,G,H,J,K,L}
    "EGICAHLK",  # 212 {A,C,E,G,H,I,K,L}
    "EGJCAHLI",  # 213 {A,C,E,G,H,I,J,L}
    "EGJCAHIK",  # 214 {A,C,E,G,H,I,J,K}
    "EJICAFLK",  # 215 {A,C,E,F,I,J,K,L}
    "HJECAFLK",  # 216 {A,C,E,F,H,J,K,L}
    "HEICAFLK",  # 217 {A,C,E,F,H,I,K,L}
    "HJECAFLI",  # 218 {A,C,E,F,H,I,J,L}
    "HJECAFIK",  # 219 {A,C,E,F,H,I,J,K}
    "EGJCAFLK",  # 220 {A,C,E,F,G,J,K,L}
    "EGICAFLK",  # 221 {A,C,E,F,G,I,K,L}
    "EGJCAFLI",  # 222 {A,C,E,F,G,I,J,L}
    "EGJCAFIK",  # 223 {A,C,E,F,G,I,J,K}
    "HGECAFLK",  # 224 {A,C,E,F,G,H,K,L}
    "HGJCAFLE",  # 225 {A,C,E,F,G,H,J,L}
    "HGJCAFEK",  # 226 {A,C,E,F,G,H,J,K}
    "HGECAFLI",  # 227 {A,C,E,F,G,H,I,L}
    "HGECAFIK",  # 228 {A,C,E,F,G,H,I,K}
    "HGJCAFEI",  # 229 {A,C,E,F,G,H,I,J}
    "HJICADLK",  # 230 {A,C,D,H,I,J,K,L}
    "IGJCADLK",  # 231 {A,C,D,G,I,J,K,L}
    "HGJCADLK",  # 232 {A,C,D,G,H,J,K,L}
    "HGICADLK",  # 233 {A,C,D,G,H,I,K,L}
    "HGJCADLI",  # 234 {A,C,D,G,H,I,J,L}
    "HGJCADIK",  # 235 {A,C,D,G,H,I,J,K}
    "CJIDAFLK",  # 236 {A,C,D,F,I,J,K,L}
    "HJFCADLK",  # 237 {A,C,D,F,H,J,K,L}
    "HFICADLK",  # 238 {A,C,D,F,H,I,K,L}
    "HJFCADLI",  # 239 {A,C,D,F,H,I,J,L}
    "HJFCADIK",  # 240 {A,C,D,F,H,I,J,K}
    "CGJDAFLK",  # 241 {A,C,D,F,G,J,K,L}
    "CGIDAFLK",  # 242 {A,C,D,F,G,I,K,L}
    "CGJDAFLI",  # 243 {A,C,D,F,G,I,J,L}
    "CGJDAFIK",  # 244 {A,C,D,F,G,I,J,K}
    "HGFCADLK",  # 245 {A,C,D,F,G,H,K,L}
    "CGJDAFLH",  # 246 {A,C,D,F,G,H,J,L}
    "HGJCAFDK",  # 247 {A,C,D,F,G,H,J,K}
    "HGFCADLI",  # 248 {A,C,D,F,G,H,I,L}
    "HGFCADIK",  # 249 {A,C,D,F,G,H,I,K}
    "HGJCAFDI",  # 250 {A,C,D,F,G,H,I,J}
    "EJICADLK",  # 251 {A,C,D,E,I,J,K,L}
    "HJECADLK",  # 252 {A,C,D,E,H,J,K,L}
    "HEICADLK",  # 253 {A,C,D,E,H,I,K,L}
    "HJECADLI",  # 254 {A,C,D,E,H,I,J,L}
    "HJECADIK",  # 255 {A,C,D,E,H,I,J,K}
    "EGJCADLK",  # 256 {A,C,D,E,G,J,K,L}
    "EGICADLK",  # 257 {A,C,D,E,G,I,K,L}
    "EGJCADLI",  # 258 {A,C,D,E,G,I,J,L}
    "EGJCADIK",  # 259 {A,C,D,E,G,I,J,K}
    "HGECADLK",  # 260 {A,C,D,E,G,H,K,L}
    "HGJCADLE",  # 261 {A,C,D,E,G,H,J,L}
    "HGJCADEK",  # 262 {A,C,D,E,G,H,J,K}
    "HGECADLI",  # 263 {A,C,D,E,G,H,I,L}
    "HGECADIK",  # 264 {A,C,D,E,G,H,I,K}
    "HGJCADEI",  # 265 {A,C,D,E,G,H,I,J}
    "CJEDAFLK",  # 266 {A,C,D,E,F,J,K,L}
    "CEIDAFLK",  # 267 {A,C,D,E,F,I,K,L}
    "CJEDAFLI",  # 268 {A,C,D,E,F,I,J,L}
    "CJEDAFIK",  # 269 {A,C,D,E,F,I,J,K}
    "HEFCADLK",  # 270 {A,C,D,E,F,H,K,L}
    "HJFCADLE",  # 271 {A,C,D,E,F,H,J,L}
    "HJECAFDK",  # 272 {A,C,D,E,F,H,J,K}
    "HEFCADLI",  # 273 {A,C,D,E,F,H,I,L}
    "HEFCADIK",  # 274 {A,C,D,E,F,H,I,K}
    "HJECAFDI",  # 275 {A,C,D,E,F,H,I,J}
    "CGEDAFLK",  # 276 {A,C,D,E,F,G,K,L}
    "CGJDAFLE",  # 277 {A,C,D,E,F,G,J,L}
    "CGJDAFEK",  # 278 {A,C,D,E,F,G,J,K}
    "CGEDAFLI",  # 279 {A,C,D,E,F,G,I,L}
    "CGEDAFIK",  # 280 {A,C,D,E,F,G,I,K}
    "CGJDAFEI",  # 281 {A,C,D,E,F,G,I,J}
    "HGFCADLE",  # 282 {A,C,D,E,F,G,H,L}
    "HGECAFDK",  # 283 {A,C,D,E,F,G,H,K}
    "HGJCAFDE",  # 284 {A,C,D,E,F,G,H,J}
    "HGECAFDI",  # 285 {A,C,D,E,F,G,H,I}
    # 286-495: A present, B present
    "HJBAIGLK",  # 286 {A,B,G,H,I,J,K,L}
    "HJBAIFLK",  # 287 {A,B,F,H,I,J,K,L}
    "IJBFAGLK",  # 288 {A,B,F,G,I,J,K,L}
    "HJBFAGLK",  # 289 {A,B,F,G,H,J,K,L}
    "HGBAIFLK",  # 290 {A,B,F,G,H,I,K,L}
    "HJBFAGLI",  # 291 {A,B,F,G,H,I,J,L}
    "HJBFAGIK",  # 292 {A,B,F,G,H,I,J,K}
    "EJBAIHLK",  # 293 {A,B,E,H,I,J,K,L}
    "EJBAIGLK",  # 294 {A,B,E,G,I,J,K,L}
    "EJBAХGLK",  # 295 placeholder
    "EGBAIHLK",  # 296 {A,B,E,G,H,I,K,L}
    "EJBAHGLI",  # 297 {A,B,E,G,H,I,J,L}
    "EJBAHGIK",  # 298 {A,B,E,G,H,I,J,K}
    "EJBAIFLK",  # 299 {A,B,E,F,I,J,K,L}
    "EJBFAHLK",  # 300 {A,B,E,F,H,J,K,L}
    "EIBFAHLK",  # 301 {A,B,E,F,H,I,K,L}
    "EJBFAHLI",  # 302 {A,B,E,F,H,I,J,L}
    "EJBFAHIK",  # 303 {A,B,E,F,H,I,J,K}
    "EJBFAGLK",  # 304 {A,B,E,F,G,J,K,L}
    "EGBAIFLK",  # 305 {A,B,E,F,G,I,K,L}
    "EJBFAGLI",  # 306 {A,B,E,F,G,I,J,L}
    "EJBFAGIK",  # 307 {A,B,E,F,G,I,J,K}
    "EGBFAHLK",  # 308 {A,B,E,F,G,H,K,L}
    "HJBFAGLE",  # 309 {A,B,E,F,G,H,J,L}
    "HJBFAGEK",  # 310 {A,B,E,F,G,H,J,K}
    "EGBFAHLI",  # 311 {A,B,E,F,G,H,I,L}
    "EGBFAHIK",  # 312 {A,B,E,F,G,H,I,K}
    "HJBFAGEI",  # 313 {A,B,E,F,G,H,I,J}
    "IJBDAHLK",  # 314 {A,B,D,H,I,J,K,L}
    "IJBDAGLK",  # 315 {A,B,D,G,I,J,K,L}
    "HJBDAGLK",  # 316 {A,B,D,G,H,J,K,L}
    "IGBDAHLK",  # 317 {A,B,D,G,H,I,K,L}
    "HJBDAGLI",  # 318 {A,B,D,G,H,I,J,L}
    "HJBDAGIK",  # 319 {A,B,D,G,H,I,J,K}
    "IJBDAFLK",  # 320 {A,B,D,F,I,J,K,L}
    "HJBDAFLK",  # 321 {A,B,D,F,H,J,K,L}
    "HIBDAFLK",  # 322 {A,B,D,F,H,I,K,L}
    "HJBDAFLI",  # 323 {A,B,D,F,H,I,J,L}
    "HJBDAFIK",  # 324 {A,B,D,F,H,I,J,K}
    "FJBDAGLK",  # 325 {A,B,D,F,G,J,K,L}
    "IGBDAFLK",  # 326 {A,B,D,F,G,I,K,L}
    "FJBDAGLI",  # 327 {A,B,D,F,G,I,J,L}
    "FJBDAGIK",  # 328 {A,B,D,F,G,I,J,K}
    "HGBDAFLK",  # 329 {A,B,D,F,G,H,K,L}
    "HGBDAFLJ",  # 330 {A,B,D,F,G,H,J,L}
    "HGBDAFJK",  # 331 {A,B,D,F,G,H,J,K}
    "HGBDAFLI",  # 332 {A,B,D,F,G,H,I,L}
    "HGBDAFIK",  # 333 {A,B,D,F,G,H,I,K}
    "HGBDAFIJ",  # 334 {A,B,D,F,G,H,I,J}
    "EJBAIDLK",  # 335 {A,B,D,E,I,J,K,L}
    "EJBDAHLK",  # 336 {A,B,D,E,H,J,K,L}
    "EIBDAHLK",  # 337 {A,B,D,E,H,I,K,L}
    "EJBDAHLI",  # 338 {A,B,D,E,H,I,J,L}
    "EJBDAHIK",  # 339 {A,B,D,E,H,I,J,K}
    "EJBDAGLK",  # 340 {A,B,D,E,G,J,K,L}
    "EGBAIDLK",  # 341 {A,B,D,E,G,I,K,L}
    "EJBDAGLI",  # 342 {A,B,D,E,G,I,J,L}
    "EJBDAGIK",  # 343 {A,B,D,E,G,I,J,K}
    "EGBDAHLK",  # 344 {A,B,D,E,G,H,K,L}
    "HJBDAGLE",  # 345 {A,B,D,E,G,H,J,L}
    "HJBDAGEK",  # 346 {A,B,D,E,G,H,J,K}
    "EGBDAHLI",  # 347 {A,B,D,E,G,H,I,L}
    "EGBDAHIK",  # 348 {A,B,D,E,G,H,I,K}
    "HJBDAGEI",  # 349 {A,B,D,E,G,H,I,J}
    "EJBDAFLK",  # 350 {A,B,D,E,F,J,K,L}
    "EIBDAFLK",  # 351 {A,B,D,E,F,I,K,L}
    "EJBDAFLI",  # 352 {A,B,D,E,F,I,J,L}
    "EJBDAFIK",  # 353 {A,B,D,E,F,I,J,K}
    "HEBDAFLK",  # 354 {A,B,D,E,F,H,K,L}
    "HJBDAFLE",  # 355 {A,B,D,E,F,H,J,L}
    "HJBDAFEK",  # 356 {A,B,D,E,F,H,J,K}
    "HEBDAFLI",  # 357 {A,B,D,E,F,H,I,L}
    "HEBDAFIK",  # 358 {A,B,D,E,F,H,I,K}
    "HJBDAFEI",  # 359 {A,B,D,E,F,H,I,J}
    "EGBDAFLK",  # 360 {A,B,D,E,F,G,K,L}
    "EGBDAFLJ",  # 361 {A,B,D,E,F,G,J,L}
    "EGBDAFJK",  # 362 {A,B,D,E,F,G,J,K}
    "EGBDAFLI",  # 363 {A,B,D,E,F,G,I,L}
    "EGBDAFIK",  # 364 {A,B,D,E,F,G,I,K}
    "EGBDAFIJ",  # 365 {A,B,D,E,F,G,I,J}
    "HGBDAFLE",  # 366 {A,B,D,E,F,G,H,L}
    "HGBDAFEK",  # 367 {A,B,D,E,F,G,H,K}
    "HGBDAFEJ",  # 368 {A,B,D,E,F,G,H,J}
    "HGBDAFEI",  # 369 {A,B,D,E,F,G,H,I}
    "IJBCAHLK",  # 370 {A,B,C,H,I,J,K,L}
    "IJBCAGLK",  # 371 {A,B,C,G,I,J,K,L}
    "HJBCAGLK",  # 372 {A,B,C,G,H,J,K,L}
    "IGBCAHLK",  # 373 {A,B,C,G,H,I,K,L}
    "HJBCAGLI",  # 374 {A,B,C,G,H,I,J,L}
    "HJBCAGIK",  # 375 {A,B,C,G,H,I,J,K}
    "IJBCAFLK",  # 376 {A,B,C,F,I,J,K,L}
    "HJBCAFLK",  # 377 {A,B,C,F,H,J,K,L}
    "HIBCAFLK",  # 378 {A,B,C,F,H,I,K,L}
    "HJBCAFLI",  # 379 {A,B,C,F,H,I,J,L}
    "HJBCAFIK",  # 380 {A,B,C,F,H,I,J,K}
    "CJBFAGLK",  # 381 {A,B,C,F,G,J,K,L}
    "IGBCAFLK",  # 382 {A,B,C,F,G,I,K,L}
    "CJBFAGLI",  # 383 {A,B,C,F,G,I,J,L}
    "CJBFAGIK",  # 384 {A,B,C,F,G,I,J,K}
    "HGBCAFLK",  # 385 {A,B,C,F,G,H,K,L}
    "HGBCAFLJ",  # 386 {A,B,C,F,G,H,J,L}
    "HGBCAFJK",  # 387 {A,B,C,F,G,H,J,K}
    "HGBCAFLI",  # 388 {A,B,C,F,G,H,I,L}
    "HGBCAFIK",  # 389 {A,B,C,F,G,H,I,K}
    "HGBCAFIJ",  # 390 {A,B,C,F,G,H,I,J}
    "EJBAICLK",  # 391 {A,B,C,E,I,J,K,L}
    "EJBCAHLK",  # 392 {A,B,C,E,H,J,K,L}
    "EIBCAHLK",  # 393 {A,B,C,E,H,I,K,L}
    "EJBCAHLI",  # 394 {A,B,C,E,H,I,J,L}
    "EJBCAHIK",  # 395 {A,B,C,E,H,I,J,K}
    "EJBCAGLK",  # 396 {A,B,C,E,G,J,K,L}
    "EGBAICLK",  # 397 {A,B,C,E,G,I,K,L}
    "EJBCAGLI",  # 398 {A,B,C,E,G,I,J,L}
    "EJBCAGIK",  # 399 {A,B,C,E,G,I,J,K}
    "EGBCAHLK",  # 400 {A,B,C,E,G,H,K,L}
    "HJBCAGLE",  # 401 {A,B,C,E,G,H,J,L}
    "HJBCAGEK",  # 402 {A,B,C,E,G,H,J,K}
    "EGBCAHLI",  # 403 {A,B,C,E,G,H,I,L}
    "EGBCAHIK",  # 404 {A,B,C,E,G,H,I,K}
    "HJBCAGEI",  # 405 {A,B,C,E,G,H,I,J}
    "EJBCAFLK",  # 406 {A,B,C,E,F,J,K,L}
    "EIBCAFLK",  # 407 {A,B,C,E,F,I,K,L}
    "EJBCAFLI",  # 408 {A,B,C,E,F,I,J,L}
    "EJBCAFIK",  # 409 {A,B,C,E,F,I,J,K}
    "HEBCAFLK",  # 410 {A,B,C,E,F,H,K,L}
    "HJBCAFLE",  # 411 {A,B,C,E,F,H,J,L}
    "HJBCAFEK",  # 412 {A,B,C,E,F,H,J,K}
    "HEBCAFLI",  # 413 {A,B,C,E,F,H,I,L}
    "HEBCAFIK",  # 414 {A,B,C,E,F,H,I,K}
    "HJBCAFEI",  # 415 {A,B,C,E,F,H,I,J}
    "EGBCAFLK",  # 416 {A,B,C,E,F,G,K,L}
    "EGBCAFLJ",  # 417 {A,B,C,E,F,G,J,L}
    "EGBCAFJK",  # 418 {A,B,C,E,F,G,J,K}
    "EGBCAFLI",  # 419 {A,B,C,E,F,G,I,L}
    "EGBCAFIK",  # 420 {A,B,C,E,F,G,I,K}
    "EGBCAFIJ",  # 421 {A,B,C,E,F,G,I,J}
    "HGBCAFLE",  # 422 {A,B,C,E,F,G,H,L}
    "HGBCAFEK",  # 423 {A,B,C,E,F,G,H,K}
    "HGBCAFEJ",  # 424 {A,B,C,E,F,G,H,J}
    "HGBCAFEI",  # 425 {A,B,C,E,F,G,H,I}
    "IJBCADLK",  # 426 {A,B,C,D,I,J,K,L}
    "HJBCADLK",  # 427 {A,B,C,D,H,J,K,L}
    "HIBCADLK",  # 428 {A,B,C,D,H,I,K,L}
    "HJBCADLI",  # 429 {A,B,C,D,H,I,J,L}
    "HJBCADIK",  # 430 {A,B,C,D,H,I,J,K}
    "CJBDAGLK",  # 431 {A,B,C,D,G,J,K,L}
    "IGBCADLK",  # 432 {A,B,C,D,G,I,K,L}
    "CJBDAGLI",  # 433 {A,B,C,D,G,I,J,L}
    "CJBDAGIK",  # 434 {A,B,C,D,G,I,J,K}
    "HGBCADLK",  # 435 {A,B,C,D,G,H,K,L}
    "HGBCADLJ",  # 436 {A,B,C,D,G,H,J,L}
    "HGBCADJK",  # 437 {A,B,C,D,G,H,J,K}
    "HGBCADLI",  # 438 {A,B,C,D,G,H,I,L}
    "HGBCADIK",  # 439 {A,B,C,D,G,H,I,K}
    "HGBCADIJ",  # 440 {A,B,C,D,G,H,I,J}
    "CJBDAFLK",  # 441 {A,B,C,D,F,J,K,L}
    "CIBDAFLK",  # 442 {A,B,C,D,F,I,K,L}
    "CJBDAFLI",  # 443 {A,B,C,D,F,I,J,L}
    "CJBDAFIK",  # 444 {A,B,C,D,F,I,J,K}
    "HFBCADLK",  # 445 {A,B,C,D,F,H,K,L}
    "CJBDAFLH",  # 446 {A,B,C,D,F,H,J,L}
    "HJBCAFDK",  # 447 {A,B,C,D,F,H,J,K}
    "HFBCADLI",  # 448 {A,B,C,D,F,H,I,L}
    "HFBCADIK",  # 449 {A,B,C,D,F,H,I,K}
    "HJBCAFDI",  # 450 {A,B,C,D,F,H,I,J}
    "CGBDAFLK",  # 451 {A,B,C,D,F,G,K,L}
    "CGBDAFLJ",  # 452 {A,B,C,D,F,G,J,L}
    "CGBDAFJK",  # 453 {A,B,C,D,F,G,J,K}
    "CGBDAFLI",  # 454 {A,B,C,D,F,G,I,L}
    "CGBDAFIK",  # 455 {A,B,C,D,F,G,I,K}
    "CGBDAFIJ",  # 456 {A,B,C,D,F,G,I,J}
    "CGBDAFLH",  # 457 {A,B,C,D,F,G,H,L}
    "HGBCAFDK",  # 458 {A,B,C,D,F,G,H,K}
    "HGBCAFDJ",  # 459 {A,B,C,D,F,G,H,J}
    "HGBCAFDI",  # 460 {A,B,C,D,F,G,H,I}
    "EJBCADLK",  # 461 {A,B,C,D,E,J,K,L}
    "EIBCADLK",  # 462 {A,B,C,D,E,I,K,L}
    "EJBCADLI",  # 463 {A,B,C,D,E,I,J,L}
    "EJBCADIK",  # 464 {A,B,C,D,E,I,J,K}
    "HEBCADLK",  # 465 {A,B,C,D,E,H,K,L}
    "HJBCADLE",  # 466 {A,B,C,D,E,H,J,L}
    "HJBCADEK",  # 467 {A,B,C,D,E,H,J,K}
    "HEBCADLI",  # 468 {A,B,C,D,E,H,I,L}
    "HEBCADIK",  # 469 {A,B,C,D,E,H,I,K}
    "HJBCADEI",  # 470 {A,B,C,D,E,H,I,J}
    "EGBCADLK",  # 471 {A,B,C,D,E,G,K,L}
    "EGBCADLJ",  # 472 {A,B,C,D,E,G,J,L}
    "EGBCADJK",  # 473 {A,B,C,D,E,G,J,K}
    "EGBCADLI",  # 474 {A,B,C,D,E,G,I,L}
    "EGBCADIK",  # 475 {A,B,C,D,E,G,I,K}
    "EGBCADIJ",  # 476 {A,B,C,D,E,G,I,J}
    "HGBCADLE",  # 477 {A,B,C,D,E,G,H,L}
    "HGBCADEK",  # 478 {A,B,C,D,E,G,H,K}
    "HGBCADEJ",  # 479 {A,B,C,D,E,G,H,J}
    "HGBCADEI",  # 480 {A,B,C,D,E,G,H,I}
    "CEBDAFLK",  # 481 {A,B,C,D,E,F,K,L}
    "CJBDAFLE",  # 482 {A,B,C,D,E,F,J,L}
    "CJBDAFEK",  # 483 {A,B,C,D,E,F,J,K}
    "CEBDAFLI",  # 484 {A,B,C,D,E,F,I,L}
    "CEBDAFIK",  # 485 {A,B,C,D,E,F,I,K}
    "CJBDAFEI",  # 486 {A,B,C,D,E,F,I,J}
    "HFBCADLE",  # 487 {A,B,C,D,E,F,H,L}
    "HEBCAFDK",  # 488 {A,B,C,D,E,F,H,K}
    "HJBCAFDE",  # 489 {A,B,C,D,E,F,H,J}
    "HEBCAFDI",  # 490 {A,B,C,D,E,F,H,I}
    "CGBDAFLE",  # 491 {A,B,C,D,E,F,G,L}
    "CGBDAFEK",  # 492 {A,B,C,D,E,F,G,K}
    "CGBDAFEJ",  # 493 {A,B,C,D,E,F,G,J}
    "CGBDAFEI",  # 494 {A,B,C,D,E,F,G,I}
    "HGBCAFDE",  # 495 {A,B,C,D,E,F,G,H}
]

# Fix placeholder rows (167 and 295) with correct data
_RAW[166] = "EJIAHGLK"   # 167 {A,E,G,H,I,J,K,L}: 1A→E,1B→J,1D→I,1E→A,1G→H,1I→G,1K→L,1L→K
_RAW[294] = "EJBAHGLK"   # 295 {A,B,E,G,H,J,K,L}: 1A→E,1B→J,1D→B,1E→A,1G→H,1I→G,1K→L,1L→K


def _build() -> dict[frozenset[str], dict[str, str]]:
    """Construye ANNEX_C desde _RAW verificando unicidad de claves."""
    result: dict[frozenset[str], dict[str, str]] = {}
    for raw in _RAW:
        assert len(raw) == 8, f"Fila de longitud inválida: {raw!r}"
        key = frozenset(raw)
        assert len(key) == 8, f"Fila con letras duplicadas: {raw!r}"
        slotmap = dict(zip(_SLOTS, raw))
        if key in result:
            # Clave duplicada = error en los datos fuente
            raise ValueError(f"Clave duplicada en ANNEX_C: {key}")
        result[key] = slotmap
    return result


ANNEX_C: dict[frozenset[str], dict[str, str]] = _build()


def validate_annex_c() -> None:
    """Valida los invariantes de ANNEX_C. Lanza AssertionError si algo falla.

    Invariantes:
    - len(ANNEX_C) == 495
    - Cada clave es frozenset de tamaño 8
    - Todas las letras están en {A..L}
    - Cada valor tiene exactamente 8 slots
    """
    valid = frozenset("ABCDEFGHIJKL")
    assert len(ANNEX_C) == 495, f"ANNEX_C tiene {len(ANNEX_C)} entradas, esperado 495"
    for key, slotmap in ANNEX_C.items():
        assert len(key) == 8, f"Clave con {len(key)} letras: {key}"
        for letter in key:
            assert letter in valid, f"Letra inválida en clave: {letter!r}"
        assert len(slotmap) == 8, f"Mapa con {len(slotmap)} slots"
        for slot, letter in slotmap.items():
            assert letter in valid, f"Letra inválida en slot {slot}: {letter!r}"
