# Release Notes — Canine Impaction Analyzer v1.1.0

Developed by **Samer Mheissen**  
© 2026 Samer Mheissen. All rights reserved.

## Changes in v1.1.0

- Matched visible line and landmark thickness across Windows and macOS.
- Lines keep a consistent display thickness while zooming.
- Landmarks are now draggable after placement.
- Measurements and lines update automatically when a landmark is moved.
- Root-development stage, patient age, and calibration distance can be changed after measurement and results update automatically.
- Clarified maxillary midline landmark definition.
- Clarified occlusal-plane definition using corresponding mesial cusps of the upper first molars.
- Expanded calibration instructions for cases without a radiographic ruler or marker.
- Added JPEG/JPG, PNG, TIFF, BMP, and WebP image filters.
- Preserved the Windows short-path builder (`C:\CIA_BUILD\venv`) to avoid PySide6 MAX_PATH installation failures.

## Research notice
The current eruption assessment/recommendation logic remains provisional and requires validation before clinical use.


## v1.1.1
- Fixed User Guide window so it has a dedicated Close button and can be closed normally.
- Slightly reduced landmark-circle size and outline thickness.
- Retained the v1.1 adjustable landmark and automatic recalculation workflow.


## v1.1.2
- Restored a larger left/results panel similar to the earlier application layout.
- Results box now has a larger minimum height so the full measurements are easier to review.
- Fixed User Guide using a reliable modal dialog with a dedicated Close button.
- Reduced landmark circles slightly again for more precise anatomical placement.
