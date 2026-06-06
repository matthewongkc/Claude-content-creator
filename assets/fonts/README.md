# Fonts

The renderer works out of the box using Pillow's bundled **DejaVu Sans**.
It looks fine — but for genuinely *beautiful* carousels, drop a nicer
font family in here and the renderer will pick it up automatically.

## Recommended (free, great for social)

- **Poppins** — friendly geometric sans → https://fonts.google.com/specimen/Poppins
- **Montserrat** — clean, modern → https://fonts.google.com/specimen/Montserrat
- **Inter** — crisp UI sans → https://fonts.google.com/specimen/Inter

## How to install

Download the family and copy the `Bold` and `Regular` weights here, named
exactly like this (the renderer looks for these stems, in order):

```
assets/fonts/Poppins-Bold.ttf
assets/fonts/Poppins-Regular.ttf
```

`Montserrat-Bold/Regular` and `Inter-Bold/Regular` also work. The renderer
tries Poppins → Montserrat → Inter → DejaVu and uses the first it finds.

> Font files are gitignored (they're large binaries) — each person sets up
> their own. Licensing for the fonts above is the SIL Open Font License.
