# Model Notes

## Source PDF

The supplied PDF at `bhrigu-samhita-tmrao.pdf` is a scanned 304-page document. Poppler can render the pages, but text extraction returns empty content because the pages are image-based.

The rendered title page identifies the work as *Bhrigu Samhita*, abridged by Dr. T.M. Rao. Because OCR is not available in this workspace, the project does not claim to have machine-ingested every verse from the PDF. Instead, the interpretation model is transparent and editable in `app/astro/rules.py`.

## Calculation Foundation

- Sidereal zodiac with Lahiri ayanamsa
- Built-in low-precision planetary calculations, with optional Swiss Ephemeris support
- Whole-sign Vedic houses from sidereal lagna
- Moon nakshatra, pada, and nakshatra lord
- Vimshottari dasha balance from the Moon's nakshatra
- Mahadasha and antardasha timing using a 365.25636-day sidereal year

## Bhrigu/Kerala-Style Reading Order

The rule engine follows a sutra-like structure:

1. Judge lagna, lagna lord, Moon, and Moon nakshatra.
2. For each bhava, combine house sign, house lord placement, occupants, and natural karakas.
3. Treat yogas as repeating signatures whose results unfold when their planets are activated by dasha.
4. Use dasha lords to time future themes by their natal house, dignity, and karaka meaning.
5. Give practical remedies and disciplines instead of fatalistic claims.

## Extending The Model

Add or refine rules in `app/astro/rules.py`:

- Add a yoga in `_detect_yogas`.
- Add a life-area lens in `_life_areas`.
- Change dasha forecast language in `_period_forecast`.
- Add tradition-specific remedies in `_planet_practice`.

For a more literal Bhrigu text model, add OCR to convert selected PDF pages into reviewed text, then encode each verified sutra as a named rule with source page metadata.

## Precision Note

The default built-in astronomy module is intended for local project usability. It is suitable for prototype readings and rule development, but a professional astrology workflow should install `pyswisseph` and compare sensitive lagna/nakshatra boundary cases.
