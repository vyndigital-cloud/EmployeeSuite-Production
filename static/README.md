# Static Assets

## App Icon

The app icon is provided as `icon.svg`. To create the required 1200x1200px PNG:

### Option 1: Online Converter
1. Go to https://cloudconvert.com/svg-to-png
2. Upload `icon.svg`
3. Set size to 1200x1200px
4. Download and save as `icon.png`

### Option 2: Using ImageMagick (if installed)
```bash
convert -background none -size 1200x1200 icon.svg icon.png
```

### Option 3: Using Inkscape
```bash
inkscape icon.svg --export-filename=icon.png --export-width=1200 --export-height=1200
```

## Screenshots

Screenshots should be taken from the live application:
1. Dashboard: `/dashboard`
2. Order Processing: `/dashboard` (after clicking Process Orders)
3. Inventory: `/dashboard` (after clicking Check Inventory)
4. Reports: `/dashboard` (after clicking Generate Report)
5. Settings: `/settings/shopify`

**Requirements:**
- Minimum size: 1280x720px
- Format: PNG or JPG
- Show key features clearly
- Use browser dev tools to set viewport size

## File Structure

```
static/
├── icon.svg          # Source icon (SVG)
├── icon.png          # App icon (1200x1200px) - CREATE THIS
└── README.md         # This file
```
