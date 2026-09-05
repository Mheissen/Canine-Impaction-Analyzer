# Canine Impaction Analyzer v1.0

**Developed by Samer Mheissen**  
© 2026 Samer Mheissen. All rights reserved.

Canine Impaction Analyzer is a desktop research application for standardized
measurement of maxillary canine position on panoramic radiographs.

## Current capabilities

- Import panoramic radiographs in common image formats.
- Record Patient/Study ID and age.
- Record right and left canine root-development stage.
- Guided landmark placement.
- Alpha angle (α): canine long axis relative to maxillary midline.
- Canine–occlusal plane angle.
- Perpendicular distance D in pixels and calibrated millimeters.
- Five-sector positional classification.
- Export measurements and landmark coordinates to CSV.
- Zoom, pan, undo, and reset.
- Color-coded anatomical and measurement lines.
- Built-in User Guide and About information.

## Line colors

- Red — canine long axis
- Green — maxillary midline
- Blue dashed — central/lateral incisor axes
- Magenta — occlusal plane
- Yellow — calibration line

## Research-use notice

The measurement functions are intended for research and method development.

The current eruption assessment and recommendation logic is provisional and
has not yet been validated as an independent clinical decision-support model.
The software must not be used as a substitute for professional diagnosis,
clinical judgment, or treatment planning.

## macOS

Run:

```bash
chmod +x build_mac.command
./build_mac.command
```

The application will be created under:

`dist/Canine Impaction Analyzer.app`

For public distribution, sign with an Apple Developer ID certificate and
submit the application for notarization.

## Windows

Run:

`build_windows.bat`

The executable will be created under:

`dist\Canine Impaction Analyzer\Canine Impaction Analyzer.exe`

For public distribution, digitally sign the executable/installer with a
trusted code-signing certificate.

## Antivirus / trust

Unsigned PyInstaller applications may trigger reputation or SmartScreen
warnings even when the source is clean.

Recommended public-release workflow:

1. Build on a clean Mac or Windows system.
2. Scan the finished binary.
3. Digitally sign the Windows executable/installer.
4. Sign and notarize the macOS application.
5. Publish SHA-256 checksums.
6. Distribute only through an official release page such as GitHub Releases.

## Privacy

Do not bundle patient radiographs, names, dates of birth, or other identifiable
clinical data with the application package.

## Version

1.0.0
