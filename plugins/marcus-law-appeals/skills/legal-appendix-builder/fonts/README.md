# Fonts bundled with legal-appendix-builder

These TrueType fonts are bundled so LibreOffice on a Linux sandbox can
render Hebrew legal documents the way Microsoft Word does on the user's
Windows machine.

## Included
- **David** + David Bold (Hebrew serif, Word default)
- **Times New Roman** Regular / Bold / Italic / Bold Italic
- **Arial** Regular / Bold / Italic / Bold Italic / Black
- **Arial Narrow** Regular / Bold / Italic / Bold Italic
- **Arial Rounded MT Bold**

## Licensing note
These fonts are property of Microsoft Corporation and ship with Microsoft
Windows / Office. They are bundled here for convenience so the same
operator can run the skill on a Linux sandbox they own. **You may use
these fonts only on machines covered by your own valid Microsoft
Windows / Office license.**

If your deployment targets a machine without such a license, replace
`david.ttf` with the open-source equivalent David CLM (from `culmus`
package on Debian/Ubuntu) and replace Times New Roman / Arial with
Liberation Serif / Liberation Sans (metric-compatible substitutes).

## Auto-installation
Running `bind_pdf.bind_pleading()` for the first time on a new machine
checks fontconfig for David / Times New Roman / Arial, and if any are
missing, automatically copies the TTF files from this folder into
`~/.fonts` and refreshes `fc-cache`. No manual step needed.
