import sys
import os
import csv
import math
import json
import shutil
import threading
import urllib.request
import webbrowser
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QTimer
from PySide6.QtGui import QPixmap, QPen, QColor, QPainter, QFont, QImage, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox,
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QDoubleSpinBox,
    QComboBox, QPushButton, QLabel, QTextEdit, QSplitter, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QGroupBox, QGraphicsItem, QGraphicsSimpleTextItem,
    QDialog, QDialogButtonBox
)


APP_NAME = "Canine Impaction Analyzer"
APP_VERSION = "1.1.2"
DEVELOPER = "Samer Mheissen"

COPYRIGHT_TEXT = "© 2026 Samer Mheissen. All rights reserved."

# Patient data are intentionally stored OUTSIDE the installed application.
# This lets software updates replace the app without deleting patient records.
DATA_FOLDER_NAME = "PDC Analyzer Data"
GITHUB_LATEST_RELEASE_API = (
    "https://api.github.com/repos/Mheissen/Canine-Impaction-Analyzer/releases/latest"
)
GITHUB_RELEASES_URL = (
    "https://github.com/Mheissen/Canine-Impaction-Analyzer/releases/latest"
)
UPDATE_CHECK_DAYS = 7

MASTER_RESULTS_FIELDS = [
    "Patient_ID",
    "Age",

    "Right_Root_Development",
    "Right_Alpha_Angle",
    "Right_Occlusal_Angle",
    "Right_D_mm",
    "Right_Sector",
    "Right_Eruption_Assessment",
    "Right_Recommendation",

    "Left_Root_Development",
    "Left_Alpha_Angle",
    "Left_Occlusal_Angle",
    "Left_D_mm",
    "Left_Sector",
    "Left_Eruption_Assessment",
    "Left_Recommendation",
]


def app_data_dir():
    """
    Cross-platform writable data location, outside the installed app.
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    folder = base / DATA_FOLDER_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def safe_patient_filename(patient_id):
    cleaned = "".join(
        ch if ch.isalnum() or ch in ("-", "_") else "_"
        for ch in patient_id.strip()
    )
    return cleaned or "patient"


def version_tuple(version_text):
    parts = version_text.strip().lstrip("vV").split(".")
    nums = []
    for part in parts[:3]:
        m = re.match(r"(\d+)", part)
        nums.append(int(m.group(1)) if m else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


# ============================================================
# MATH / MEASUREMENT FUNCTIONS
# ============================================================

def vec(a, b):
    """Vector from point a to point b."""
    return (b[0] - a[0], b[1] - a[1])


def norm(v):
    return math.hypot(v[0], v[1])


def calculate_angle(vector1, vector2):
    """Acute angle in degrees between two vectors."""
    den = norm(vector1) * norm(vector2)
    if den == 0:
        return float("nan")
    cos_angle = (
        vector1[0] * vector2[0] + vector1[1] * vector2[1]
    ) / den
    cos_angle = max(-1.0, min(1.0, cos_angle))
    angle = math.degrees(math.acos(cos_angle))
    return 180.0 - angle if angle > 90.0 else angle


def pixel_distance(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def point_to_line_distance(point, line_a, line_b):
    """Perpendicular distance from point to infinite line."""
    vx = line_b[0] - line_a[0]
    vy = line_b[1] - line_a[1]
    length = math.hypot(vx, vy)
    if length == 0:
        return float("nan")
    px = point[0] - line_a[0]
    py = point[1] - line_a[1]
    cross = vx * py - vy * px
    return abs(cross) / length


def x_on_line_at_y(point1, point2, target_y):
    x1, y1 = point1
    x2, y2 = point2
    if abs(y2 - y1) < 1e-9:
        return (x1 + x2) / 2.0
    t = (target_y - y1) / (y2 - y1)
    return x1 + t * (x2 - x1)


def classify_sector(
    cusp,
    mid1,
    mid2,
    distal_lateral,
    lateral_crown,
    lateral_apex,
    distal_central,
    central_crown,
    central_apex,
):
    """
    Five-sector prototype using:
    - maxillary midline
    - lateral incisor crown-apex long axis
    - central incisor crown-apex long axis
    - distal boundaries parallel to corresponding incisor axes

    Returns sector plus boundary information.
    """
    cusp_y = cusp[1]

    midline_x = x_on_line_at_y(mid1, mid2, cusp_y)
    lateral_axis_x = x_on_line_at_y(lateral_crown, lateral_apex, cusp_y)
    central_axis_x = x_on_line_at_y(central_crown, central_apex, cusp_y)

    lateral_axis_vector = (
        lateral_apex[0] - lateral_crown[0],
        lateral_apex[1] - lateral_crown[1],
    )
    distal_lateral_2 = (
        distal_lateral[0] + lateral_axis_vector[0],
        distal_lateral[1] + lateral_axis_vector[1],
    )
    distal_lateral_x = x_on_line_at_y(
        distal_lateral, distal_lateral_2, cusp_y
    )

    central_axis_vector = (
        central_apex[0] - central_crown[0],
        central_apex[1] - central_crown[1],
    )
    distal_central_2 = (
        distal_central[0] + central_axis_vector[0],
        distal_central[1] + central_axis_vector[1],
    )
    distal_central_x = x_on_line_at_y(
        distal_central, distal_central_2, cusp_y
    )

    cusp_d = abs(cusp[0] - midline_x)
    distal_lateral_d = abs(distal_lateral_x - midline_x)
    lateral_axis_d = abs(lateral_axis_x - midline_x)
    distal_central_d = abs(distal_central_x - midline_x)
    central_axis_d = abs(central_axis_x - midline_x)

    order_ok = (
        distal_lateral_d >= lateral_axis_d >=
        distal_central_d >= central_axis_d
    )

    if cusp_d >= distal_lateral_d:
        sector = 1
    elif cusp_d >= lateral_axis_d:
        sector = 2
    elif cusp_d >= distal_central_d:
        sector = 3
    elif cusp_d >= central_axis_d:
        sector = 4
    else:
        sector = 5

    return {
        "sector": sector,
        "order_ok": order_ok,
        "midline_x": midline_x,
        "distal_lateral_x": distal_lateral_x,
        "lateral_axis_x": lateral_axis_x,
        "distal_central_x": distal_central_x,
        "central_axis_x": central_axis_x,
    }


def provisional_assessment(age, sector, alpha, root_stage):
    """
    Research prototype only.
    These are NOT validated clinical decision rules.
    """
    if sector <= 2 and alpha <= 20 and age <= 11.5 and root_stage <= 3:
        return (
            "Favorable eruption characteristics",
            "Observation and periodic follow-up",
        )
    elif sector <= 3 and alpha <= 30 and age <= 12.5:
        return (
            "Intermediate displacement",
            "Consider primary canine extraction and radiographic follow-up",
        )
    elif sector >= 4 or alpha > 30 or age > 12.5:
        return (
            "Unfavorable eruption characteristics",
            "Orthodontic assessment; consider active management",
        )
    return (
        "Intermediate eruption characteristics",
        "Close observation and reassessment",
    )


# ============================================================
# CLICK SEQUENCE
# ============================================================

LANDMARK_SEQUENCE = [
    ("right_cusp", "RIGHT canine: click cusp tip"),
    ("right_apex", "RIGHT canine: click apex"),
    ("left_cusp", "LEFT canine: click cusp tip"),
    ("left_apex", "LEFT canine: click apex"),

    ("mid1", "MIDLINE: first point between the maxillary central-incisor incisal edges"),
    ("mid2", "MIDLINE: second point at the CEJ level of the maxillary central-incisor crowns"),

    ("right_distal_lateral", "RIGHT: distal border of lateral incisor"),
    ("right_lateral_crown", "RIGHT: crown midpoint of lateral incisor"),
    ("right_lateral_apex", "RIGHT: apex of lateral incisor"),
    ("right_distal_central", "RIGHT: distal border of central incisor"),
    ("right_central_crown", "RIGHT: crown midpoint of central incisor"),
    ("right_central_apex", "RIGHT: apex of central incisor"),

    ("left_distal_lateral", "LEFT: distal border of lateral incisor"),
    ("left_lateral_crown", "LEFT: crown midpoint of lateral incisor"),
    ("left_lateral_apex", "LEFT: apex of lateral incisor"),
    ("left_distal_central", "LEFT: distal border of central incisor"),
    ("left_central_crown", "LEFT: crown midpoint of central incisor"),
    ("left_central_apex", "LEFT: apex of central incisor"),

    ("occ1", "OCCLUSAL PLANE: click the mesial cusp of one upper first molar"),
    ("occ2", "OCCLUSAL PLANE: click the corresponding mesial cusp of the opposite upper first molar"),

    ("cal1", "CALIBRATION: first point of a known reference distance"),
    ("cal2", "CALIBRATION: second point of the same known reference distance"),
]


# ============================================================
# IMAGE VIEW
# ============================================================

class LandmarkItem(QGraphicsEllipseItem):
    """Small draggable landmark with cross-platform constant screen size."""

    def __init__(self, key, number, x, y, move_callback):
        radius = 4.0
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.key = key
        self.move_callback = move_callback
        self._ready = False

        pen = QPen(QColor(255, 0, 0))
        pen.setWidthF(1.8)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QColor(255, 0, 0))

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.setCursor(Qt.OpenHandCursor)
        self.setZValue(10)
        self.setPos(x, y)

        label = QGraphicsSimpleTextItem(str(number), self)
        label.setBrush(QColor(255, 255, 0))
        label.setFont(QFont("Arial", 6))
        label.setPos(5, 2)
        label.setAcceptedMouseButtons(Qt.NoButton)

        self._ready = True

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if (
            self._ready
            and change == QGraphicsItem.ItemPositionHasChanged
            and self.move_callback is not None
        ):
            pos = self.pos()
            self.move_callback(self.key, pos.x(), pos.y())
        return result


class ImageView(QGraphicsView):
    image_clicked = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.pixmap_item = None
        self.accept_landmarks = False
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def load_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            raise ValueError("Could not load image.")
        self.scene().clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene().addItem(self.pixmap_item)
        self.setSceneRect(self.pixmap_item.boundingRect())
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        if self.pixmap_item is None:
            return
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        # Existing landmark points are draggable after placement.
        if event.button() == Qt.LeftButton:
            clicked_item = self.itemAt(event.position().toPoint())
            probe = clicked_item
            while probe is not None:
                if isinstance(probe, LandmarkItem):
                    super().mousePressEvent(event)
                    return
                probe = probe.parentItem()

        # Otherwise, a left click records the next landmark while the
        # guided landmark sequence is active.
        if (
            self.accept_landmarks
            and event.button() == Qt.LeftButton
            and self.pixmap_item is not None
        ):
            scene_pos = self.mapToScene(event.position().toPoint())
            if self.pixmap_item.contains(
                self.pixmap_item.mapFromScene(scene_pos)
            ):
                image_pos = self.pixmap_item.mapFromScene(scene_pos)
                self.image_clicked.emit(image_pos.x(), image_pos.y())
                return
        super().mousePressEvent(event)


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    update_available = Signal(str, str)
    update_check_finished = Signal(str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1600, 980)

        self.image_path = None
        self.points = {}
        self.click_index = 0
        self.marker_items = {}
        self.line_items = []

        self.data_dir = app_data_dir()
        self.records_dir = self.data_dir / "patient_records"
        self.images_dir = self.data_dir / "images"
        self.traced_dir = self.data_dir / "traced_images"
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.traced_dir.mkdir(parents=True, exist_ok=True)

        self.master_results_path = self.data_dir / "PDC_Analyzer_Results.csv"
        self.settings_path = self.data_dir / "settings.json"

        self.update_available.connect(self.show_update_available)
        self.update_check_finished.connect(self.show_manual_update_result)

        self.build_ui()

        # Do not delay application startup. The weekly check begins only
        # after the main window is already visible and responsive.
        QTimer.singleShot(2500, self.maybe_check_for_updates)

    def build_ui(self):
        help_menu = self.menuBar().addMenu("Help")

        check_updates_action = QAction("Check for Updates", self)
        check_updates_action.triggered.connect(
            lambda: self.check_for_updates(manual=True)
        )
        help_menu.addAction(check_updates_action)

        help_menu.addSeparator()

        guide_action = QAction("User Guide", self)
        guide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(guide_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ----------------------------------------------------
        # LEFT CONTROL PANEL
        # ----------------------------------------------------

        controls = QWidget()
        controls.setMinimumWidth(430)
        controls.setMaximumWidth(560)

        controls_layout = QVBoxLayout(controls)

        patient_box = QGroupBox("Patient / Study")
        patient_form = QFormLayout(patient_box)

        self.patient_id = QLineEdit()
        patient_form.addRow("Patient ID:", self.patient_id)

        self.age = QDoubleSpinBox()
        self.age.setRange(1.0, 100.0)
        self.age.setDecimals(2)
        self.age.setValue(12.0)
        patient_form.addRow("Age (years):", self.age)

        root_options = [
            "1 - Less than 1/3 root formed",
            "2 - About 1/3 root formed",
            "3 - About 2/3 root formed",
            "4 - Root almost complete, apex open",
            "5 - Root complete, apex closed",
        ]

        self.right_root = QComboBox()
        self.right_root.addItems(root_options)
        patient_form.addRow("Right root:", self.right_root)

        self.left_root = QComboBox()
        self.left_root.addItems(root_options)
        patient_form.addRow("Left root:", self.left_root)

        # Results update automatically if age or root stage is changed later.
        self.age.valueChanged.connect(self.recalculate_if_complete)
        self.right_root.currentIndexChanged.connect(self.recalculate_if_complete)
        self.left_root.currentIndexChanged.connect(self.recalculate_if_complete)

        controls_layout.addWidget(patient_box)

        calibration_box = QGroupBox("Calibration")
        calibration_form = QFormLayout(calibration_box)

        self.known_mm = QDoubleSpinBox()
        self.known_mm.setRange(0.01, 1000.0)
        self.known_mm.setDecimals(3)
        self.known_mm.setValue(10.0)
        calibration_form.addRow("Known distance (mm):", self.known_mm)
        self.known_mm.valueChanged.connect(self.recalculate_if_complete)

        calibration_hint = QLabel(
            "Use a ruler/calibration marker when available. If not, use a "
            "reference dimension that is independently known for that image "
            "(for example, a measured central-incisor crown dimension or "
            "molar crown width)."
        )
        calibration_hint.setWordWrap(True)
        calibration_hint.setStyleSheet("font-size: 10px;")
        calibration_form.addRow(calibration_hint)

        controls_layout.addWidget(calibration_box)

        patient_buttons = QHBoxLayout()

        self.new_patient_button = QPushButton("New Patient")
        self.new_patient_button.clicked.connect(self.new_patient)
        patient_buttons.addWidget(self.new_patient_button)

        self.open_patient_button = QPushButton("Open Patient")
        self.open_patient_button.clicked.connect(self.open_patient)
        patient_buttons.addWidget(self.open_patient_button)

        controls_layout.addLayout(patient_buttons)

        self.open_button = QPushButton("Open Panoramic Image")
        self.open_button.clicked.connect(self.open_image)
        controls_layout.addWidget(self.open_button)

        self.start_button = QPushButton("Start Landmark Measurement")
        self.start_button.clicked.connect(self.start_measurement)
        controls_layout.addWidget(self.start_button)

        self.undo_button = QPushButton("Undo Last Landmark")
        self.undo_button.clicked.connect(self.undo_last)
        controls_layout.addWidget(self.undo_button)

        self.reset_button = QPushButton("Reset Landmarks")
        self.reset_button.clicked.connect(self.reset_landmarks)
        controls_layout.addWidget(self.reset_button)

        self.guide_button = QPushButton("User Guide")
        self.guide_button.clicked.connect(self.show_user_guide)
        controls_layout.addWidget(self.guide_button)

        self.about_button = QPushButton("About")
        self.about_button.clicked.connect(self.show_about)
        controls_layout.addWidget(self.about_button)

        self.instruction = QLabel(
            "Open a panoramic image, then start measurement."
        )
        self.instruction.setWordWrap(True)
        self.instruction.setStyleSheet(
            "font-size: 15px; font-weight: 600; padding: 10px;"
        )
        controls_layout.addWidget(self.instruction)

        self.progress = QLabel("Landmarks: 0 / 22")
        controls_layout.addWidget(self.progress)

        edit_hint = QLabel(
            "After placement, drag any red point to refine it. Results and "
            "lines recalculate automatically. Root stage, age, and calibration "
            "distance can also be changed later."
        )
        edit_hint.setWordWrap(True)
        edit_hint.setStyleSheet("font-size: 11px; padding: 4px;")
        controls_layout.addWidget(edit_hint)

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setMinimumHeight(330)
        controls_layout.addWidget(self.results, 1)

        self.save_button = QPushButton("Save Patient")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_patient)
        controls_layout.addWidget(self.save_button)

        research_note = QLabel(
            "Line colors: RED = canine axis | GREEN = midline | "
            "BLUE dashed = incisor axes | MAGENTA = occlusal plane | "
            "YELLOW = calibration.\n\n"
            "Research prototype. The measurement tools are separate from "
            "the provisional eruption recommendation rules, which require "
            "validation before clinical use.\n\n"
            + COPYRIGHT_TEXT
        )
        research_note.setWordWrap(True)
        research_note.setStyleSheet(
            "font-size: 11px; padding: 6px;"
        )
        controls_layout.addWidget(research_note)

        # ----------------------------------------------------
        # IMAGE PANEL
        # ----------------------------------------------------

        self.view = ImageView()
        self.view.image_clicked.connect(self.record_click)

        splitter.addWidget(controls)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(1, 1)

    def show_about(self):
        about = f"""
{APP_NAME}
Version {APP_VERSION}

Developed by {DEVELOPER}
{COPYRIGHT_TEXT}

Research software for standardized panoramic-radiograph measurements
related to maxillary canine eruption and displacement.

Current measurement functions:
• Alpha angle (α)
• Canine-occlusal angle
• Distance D
• Five-sector position
• Root-development recording
• Persistent patient records and editable saved tracings

IMPORTANT
This software is a research prototype. The current eruption assessment
and recommendation logic has not yet been validated for independent
clinical decision-making and must not replace professional diagnosis,
clinical judgment, or treatment planning.
""".strip()

        QMessageBox.information(
            self,
            f"About {APP_NAME}",
            about
        )

    def show_user_guide(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{APP_NAME} — User Guide")
        dialog.resize(760, 720)

        layout = QVBoxLayout(dialog)

        guide_text = QTextEdit(dialog)
        guide_text.setReadOnly(True)
        guide_text.setPlainText("""
PDC ANALYZER — USER GUIDE

© 2026 Samer Mheissen. All rights reserved.

PURPOSE
Research tool for standardized measurement of maxillary canine position
on panoramic radiographs.

SUPPORTED IMAGES
JPEG/JPG, PNG, TIFF/TIF, BMP, and WebP.

WORKFLOW
1. Open the panoramic image.
2. Enter Patient ID and age.
3. Select right and left canine root-development stages.
4. Enter the known calibration distance.
5. Click Start Landmark Measurement.
6. Follow the landmark instructions.

MIDLINE
• Point 1: between the incisal edges of the maxillary central incisors.
• Point 2: at approximately the cemento-enamel junction (CEJ) level of
  the maxillary central-incisor crowns.

OCCLUSAL PLANE
Place the two reference points from the mesial cusp of one upper first
molar to the corresponding mesial cusp of the opposite upper first molar.

CALIBRATION
Prefer a radiographic ruler, calibration marker, or verified image metadata.
If these are unavailable, use a dimension independently known for that
specific image/patient, such as a measured central-incisor crown dimension
or molar crown width. Do not treat generic average tooth dimensions as exact.

EDITING AFTER MEASUREMENT
• Drag a red landmark point to refine its position.
• Measurements and connected lines recalculate automatically.
• Age, root-development stage, and calibration distance can be changed later.
• Undo Last Landmark removes the latest point.
• Reset Landmarks clears the measurement set.

LINE COLORS
Red = canine long axes
Green = maxillary midline
Blue dashed = central/lateral incisor axes
Magenta = occlusal plane
Yellow = calibration

OUTPUT
The program calculates alpha angle (α), canine–occlusal angle, distance D,
five-sector position, and records root-development stage. Patient results are saved automatically to one master results file.\nLandmark coordinates are stored only in the internal patient record so\nsaved tracings can be reopened and edited.

RESEARCH NOTICE
The current eruption assessment/recommendation is provisional research logic.
The software is not a validated medical device and must not replace
professional diagnosis, clinical judgment, or treatment planning.
""".strip())

        layout.addWidget(guide_text)

        close_button = QPushButton("Close", dialog)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        # Modal execution guarantees the dialog remains functional and
        # the Close button reliably closes it on both macOS and Windows.
        dialog.exec()


    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Panoramic Radiograph",
            "",
            "Supported images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp);;JPEG (*.jpg *.jpeg);;PNG (*.png);;TIFF (*.tif *.tiff);;BMP (*.bmp);;WebP (*.webp);;All Files (*)"
        )

        if not path:
            return

        try:
            self.view.load_image(path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Image Error",
                str(exc)
            )
            return

        self.image_path = path
        self.reset_landmarks()
        self.instruction.setText(
            "Image loaded. Click 'Start Landmark Measurement'."
        )

    def start_measurement(self):
        if not self.image_path:
            QMessageBox.warning(
                self,
                "No Image",
                "Open a panoramic image first."
            )
            return

        self.reset_landmarks()
        self.click_index = 0
        self.view.accept_landmarks = True
        self.update_instruction()

    def record_click(self, x, y):
        if self.image_path is None:
            return

        if self.click_index >= len(LANDMARK_SEQUENCE):
            return

        key, description = LANDMARK_SEQUENCE[self.click_index]
        self.points[key] = (float(x), float(y))

        self.draw_marker(
            key,
            self.points[key],
            self.click_index + 1
        )

        # Draw the related axis/plane immediately when possible.
        self.draw_available_line_for_landmark(key)

        self.click_index += 1
        self.progress.setText(
            f"Landmarks: {self.click_index} / {len(LANDMARK_SEQUENCE)}"
        )

        if self.click_index == len(LANDMARK_SEQUENCE):
            self.view.accept_landmarks = False
            self.calculate_results()
        else:
            self.update_instruction()

    def update_instruction(self):
        if self.click_index < len(LANDMARK_SEQUENCE):
            _, description = LANDMARK_SEQUENCE[self.click_index]
            self.instruction.setText(
                f"Next ({self.click_index + 1}/"
                f"{len(LANDMARK_SEQUENCE)}): {description}"
            )

    def draw_available_line_for_landmark(self, key):
        """
        Draw each measurement line immediately when the second point
        needed to define that line has been clicked.
        """
        p = self.points

        RED = (255, 0, 0)
        GREEN = (0, 220, 0)
        BLUE = (0, 120, 255)
        MAGENTA = (255, 0, 255)
        YELLOW = (255, 215, 0)

        if key == "right_apex":
            self.draw_line(
                p["right_cusp"],
                p["right_apex"],
                RED,
                width=1.8
            )

        elif key == "left_apex":
            self.draw_line(
                p["left_cusp"],
                p["left_apex"],
                RED,
                width=1.8
            )

        elif key == "mid2":
            self.draw_line(
                p["mid1"],
                p["mid2"],
                GREEN,
                width=1.8
            )

        elif key == "right_lateral_apex":
            self.draw_line(
                p["right_lateral_crown"],
                p["right_lateral_apex"],
                BLUE,
                dashed=True,
                width=1.6
            )

        elif key == "right_central_apex":
            self.draw_line(
                p["right_central_crown"],
                p["right_central_apex"],
                BLUE,
                dashed=True,
                width=1.6
            )

        elif key == "left_lateral_apex":
            self.draw_line(
                p["left_lateral_crown"],
                p["left_lateral_apex"],
                BLUE,
                dashed=True,
                width=1.6
            )

        elif key == "left_central_apex":
            self.draw_line(
                p["left_central_crown"],
                p["left_central_apex"],
                BLUE,
                dashed=True,
                width=1.6
            )

        elif key == "occ2":
            self.draw_line(
                p["occ1"],
                p["occ2"],
                MAGENTA,
                width=1.8
            )

        elif key == "cal2":
            self.draw_line(
                p["cal1"],
                p["cal2"],
                YELLOW,
                width=1.8
            )

    def reset_landmarks(self):
        self.points = {}
        self.click_index = 0
        self.marker_items = {}
        self.line_items = []
        self.view.accept_landmarks = False
        self.results.clear()
        self.save_button.setEnabled(False)
        self.progress.setText(
            f"Landmarks: 0 / {len(LANDMARK_SEQUENCE)}"
        )

        if self.image_path:
            try:
                self.view.load_image(self.image_path)
            except Exception:
                pass

    def undo_last(self):
        if self.click_index <= 0:
            return

        self.click_index -= 1
        self.view.accept_landmarks = True
        key, _ = LANDMARK_SEQUENCE[self.click_index]
        self.points.pop(key, None)

        # Redraw from scratch so marker numbering remains correct.
        if self.image_path:
            self.view.load_image(self.image_path)
            old_points = dict(self.points)
            self.marker_items = {}
            self.line_items = []

            for i in range(self.click_index):
                k, _ = LANDMARK_SEQUENCE[i]
                if k in old_points:
                    self.draw_marker(k, old_points[k], i + 1)
                    self.draw_available_line_for_landmark(k)

        self.results.clear()
        self.save_button.setEnabled(False)
        self.progress.setText(
            f"Landmarks: {self.click_index} / {len(LANDMARK_SEQUENCE)}"
        )
        self.update_instruction()

    def draw_marker(self, key, point, number):
        """Draw a small draggable landmark with consistent Mac/Windows size."""
        x, y = point
        item = LandmarkItem(
            key, number, x, y, self.landmark_moved
        )
        self.view.scene().addItem(item)
        self.marker_items[key] = item

    def landmark_moved(self, key, x, y):
        """Update coordinates, lines, and measurements after dragging a point."""
        self.points[key] = (float(x), float(y))
        self.redraw_current_lines()
        self.recalculate_if_complete()

    def recalculate_if_complete(self, *args):
        if all(k in self.points for k, _ in LANDMARK_SEQUENCE):
            self.calculate_results(show_errors=False)

    def clear_lines(self):
        for item in list(self.line_items):
            try:
                self.view.scene().removeItem(item)
            except Exception:
                pass
        self.line_items = []

    def redraw_current_lines(self):
        self.clear_lines()
        for key, _ in LANDMARK_SEQUENCE:
            if key in self.points:
                self.draw_available_line_for_landmark(key)

    def draw_line(self, a, b, color, dashed=False, width=1.6):
        """
        Draw a measurement line with a specific color.
        """
        pen = QPen(QColor(*color))
        pen.setWidthF(width)
        # Cosmetic pen keeps the visible thickness consistent on macOS/Windows
        # and while zooming the radiograph.
        pen.setCosmetic(True)

        if dashed:
            pen.setStyle(Qt.DashLine)

        item = QGraphicsLineItem(
            a[0], a[1],
            b[0], b[1]
        )
        item.setPen(pen)
        self.view.scene().addItem(item)
        self.line_items.append(item)

    def draw_measurement_lines(self):
        p = self.points

        # Color key (RGB)
        RED = (255, 0, 0)          # Canine long axes
        GREEN = (0, 220, 0)        # Maxillary midline
        BLUE = (0, 120, 255)       # Incisor long axes
        MAGENTA = (255, 0, 255)    # Occlusal plane
        YELLOW = (255, 215, 0)     # Calibration line

        # Canine long axes
        self.draw_line(
            p["right_cusp"], p["right_apex"],
            RED, width=1.8
        )
        self.draw_line(
            p["left_cusp"], p["left_apex"],
            RED, width=1.8
        )

        # Maxillary midline
        self.draw_line(
            p["mid1"], p["mid2"],
            GREEN, width=1.8
        )

        # Incisor long axes
        self.draw_line(
            p["right_lateral_crown"],
            p["right_lateral_apex"],
            BLUE, dashed=True
        )
        self.draw_line(
            p["right_central_crown"],
            p["right_central_apex"],
            BLUE, dashed=True
        )
        self.draw_line(
            p["left_lateral_crown"],
            p["left_lateral_apex"],
            BLUE, dashed=True
        )
        self.draw_line(
            p["left_central_crown"],
            p["left_central_apex"],
            BLUE, dashed=True
        )

        # Occlusal plane
        self.draw_line(
            p["occ1"], p["occ2"],
            MAGENTA, width=1.8
        )

        # Calibration
        self.draw_line(
            p["cal1"], p["cal2"],
            YELLOW, width=1.8
        )

    # ========================================================
    # CALCULATION
    # ========================================================

    def calculate_results(self, show_errors=True):
        p = self.points

        cal_pixels = pixel_distance(
            p["cal1"],
            p["cal2"]
        )

        if cal_pixels <= 0:
            if show_errors:
                QMessageBox.warning(
                    self,
                    "Calibration Error",
                    "Calibration points cannot be identical."
                )
            return

        mm_per_pixel = (
            self.known_mm.value()
            / cal_pixels
        )

        right_canine_vector = vec(
            p["right_apex"],
            p["right_cusp"]
        )
        left_canine_vector = vec(
            p["left_apex"],
            p["left_cusp"]
        )
        midline_vector = vec(
            p["mid1"],
            p["mid2"]
        )
        occlusal_vector = vec(
            p["occ1"],
            p["occ2"]
        )

        right_alpha = calculate_angle(
            right_canine_vector,
            midline_vector
        )
        left_alpha = calculate_angle(
            left_canine_vector,
            midline_vector
        )

        right_occ = calculate_angle(
            right_canine_vector,
            occlusal_vector
        )
        left_occ = calculate_angle(
            left_canine_vector,
            occlusal_vector
        )

        right_d_px = point_to_line_distance(
            p["right_cusp"],
            p["occ1"],
            p["occ2"]
        )
        left_d_px = point_to_line_distance(
            p["left_cusp"],
            p["occ1"],
            p["occ2"]
        )

        right_d_mm = right_d_px * mm_per_pixel
        left_d_mm = left_d_px * mm_per_pixel

        right_sector_info = classify_sector(
            p["right_cusp"],
            p["mid1"],
            p["mid2"],
            p["right_distal_lateral"],
            p["right_lateral_crown"],
            p["right_lateral_apex"],
            p["right_distal_central"],
            p["right_central_crown"],
            p["right_central_apex"],
        )

        left_sector_info = classify_sector(
            p["left_cusp"],
            p["mid1"],
            p["mid2"],
            p["left_distal_lateral"],
            p["left_lateral_crown"],
            p["left_lateral_apex"],
            p["left_distal_central"],
            p["left_central_crown"],
            p["left_central_apex"],
        )

        right_sector = right_sector_info["sector"]
        left_sector = left_sector_info["sector"]

        right_root_stage = self.right_root.currentIndex() + 1
        left_root_stage = self.left_root.currentIndex() + 1

        right_assessment, right_rec = provisional_assessment(
            self.age.value(),
            right_sector,
            right_alpha,
            right_root_stage
        )

        left_assessment, left_rec = provisional_assessment(
            self.age.value(),
            left_sector,
            left_alpha,
            left_root_stage
        )

        self.current_result = {
            "Patient_ID": self.patient_id.text().strip(),
            "Age": self.age.value(),

            "Right_Alpha_Angle": right_alpha,
            "Left_Alpha_Angle": left_alpha,

            "Right_Occlusal_Angle": right_occ,
            "Left_Occlusal_Angle": left_occ,

            "Right_D_pixels": right_d_px,
            "Left_D_pixels": left_d_px,

            "Known_Calibration_mm": self.known_mm.value(),
            "Calibration_pixels": cal_pixels,
            "mm_per_pixel": mm_per_pixel,

            "Right_D_mm": right_d_mm,
            "Left_D_mm": left_d_mm,

            "Right_Sector": right_sector,
            "Left_Sector": left_sector,

            "Right_Root_Stage": right_root_stage,
            "Right_Root_Development": self.right_root.currentText(),

            "Left_Root_Stage": left_root_stage,
            "Left_Root_Development": self.left_root.currentText(),

            "Right_Eruption_Assessment": right_assessment,
            "Right_Recommendation": right_rec,

            "Left_Eruption_Assessment": left_assessment,
            "Left_Recommendation": left_rec,

            "Right_Sector_Landmark_Order_OK":
                right_sector_info["order_ok"],
            "Left_Sector_Landmark_Order_OK":
                left_sector_info["order_ok"],
        }

        # Save every landmark coordinate as well.
        for key, point in p.items():
            self.current_result[f"{key}_X"] = point[0]
            self.current_result[f"{key}_Y"] = point[1]

        warning_text = ""
        if not right_sector_info["order_ok"]:
            warning_text += (
                "\nWARNING: RIGHT sector landmarks are not in the "
                "expected anatomical order. Recheck the clicks.\n"
            )
        if not left_sector_info["order_ok"]:
            warning_text += (
                "\nWARNING: LEFT sector landmarks are not in the "
                "expected anatomical order. Recheck the clicks.\n"
            )

        text = f"""
PATIENT
Patient ID: {self.current_result["Patient_ID"]}
Age: {self.age.value():.2f} years

RIGHT CANINE
Alpha angle (α): {right_alpha:.2f}°
Canine-occlusal angle: {right_occ:.2f}°
Distance D: {right_d_px:.2f} pixels
Distance D: {right_d_mm:.2f} mm
Sector: {right_sector}
Root development: {self.right_root.currentText()}
Assessment: {right_assessment}
Recommendation: {right_rec}

LEFT CANINE
Alpha angle (α): {left_alpha:.2f}°
Canine-occlusal angle: {left_occ:.2f}°
Distance D: {left_d_px:.2f} pixels
Distance D: {left_d_mm:.2f} mm
Sector: {left_sector}
Root development: {self.left_root.currentText()}
Assessment: {left_assessment}
Recommendation: {left_rec}

CALIBRATION
Scale: {mm_per_pixel:.6f} mm/pixel
{warning_text}
NOTE
The eruption assessment/recommendation is provisional research logic,
not a validated clinical decision rule.
""".strip()

        self.results.setPlainText(text)
        self.instruction.setText(
            "Measurement complete. Review the results and click Save Patient."
        )
        self.save_button.setEnabled(True)

    # ========================================================
    # PATIENT STORAGE
    # ========================================================

    def new_patient(self):
        """
        Start a completely new patient without affecting already-saved records.
        """
        self.image_path = None
        self.points = {}
        self.click_index = 0
        self.marker_items = {}
        self.line_items = []
        self.view.accept_landmarks = False
        self.view.scene().clear()
        self.view.pixmap_item = None

        self.patient_id.clear()
        self.age.setValue(12.0)
        self.right_root.setCurrentIndex(0)
        self.left_root.setCurrentIndex(0)
        self.known_mm.setValue(10.0)

        self.results.clear()
        self.save_button.setEnabled(False)
        self.progress.setText(
            f"Landmarks: 0 / {len(LANDMARK_SEQUENCE)}"
        )
        self.instruction.setText(
            "New patient. Enter Patient ID, open a panoramic image, "
            "then start measurement."
        )

    def patient_record_path(self, patient_id):
        return self.records_dir / f"{safe_patient_filename(patient_id)}.json"

    def patient_image_destination(self, patient_id):
        suffix = Path(self.image_path).suffix.lower() if self.image_path else ".png"
        if not suffix:
            suffix = ".png"
        return self.images_dir / f"{safe_patient_filename(patient_id)}_original{suffix}"

    def patient_traced_destination(self, patient_id):
        return self.traced_dir / f"{safe_patient_filename(patient_id)}_traced.png"

    def save_traced_image(self, output_path):
        """
        Save a flattened visual copy of the OPG plus the current tracing.
        The editable coordinates are separately retained in the JSON record.
        """
        if self.view.pixmap_item is None:
            return

        rect = self.view.pixmap_item.boundingRect()
        width = max(1, int(round(rect.width())))
        height = max(1, int(round(rect.height())))

        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(Qt.white)

        painter = QPainter(image)
        self.view.scene().render(
            painter,
            target=QPointF(0, 0) if False else None
        )
        painter.end()

        # QGraphicsScene.render() without a target QRectF can depend on
        # scene extents. Re-render with explicit source/target if needed.
        if image.isNull():
            return

        image.save(str(output_path), "PNG")

    def save_traced_image(self, output_path):
        if self.view.pixmap_item is None:
            return False

        rect = self.view.pixmap_item.boundingRect()
        width = max(1, int(round(rect.width())))
        height = max(1, int(round(rect.height())))

        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(Qt.white)

        painter = QPainter(image)
        self.view.scene().render(
            painter,
            QRectF(0, 0, width, height),
            rect
        )
        painter.end()

        return image.save(str(output_path), "PNG")

    def build_master_result_row(self):
        r = self.current_result

        row = {
            "Patient_ID": r["Patient_ID"],
            "Age": round(float(r["Age"]), 2),

            "Right_Root_Development": r["Right_Root_Development"],
            "Right_Alpha_Angle": round(float(r["Right_Alpha_Angle"]), 2),
            "Right_Occlusal_Angle": round(float(r["Right_Occlusal_Angle"]), 2),
            "Right_D_mm": round(float(r["Right_D_mm"]), 2),
            "Right_Sector": r["Right_Sector"],
            "Right_Eruption_Assessment": r["Right_Eruption_Assessment"],
            "Right_Recommendation": r["Right_Recommendation"],

            "Left_Root_Development": r["Left_Root_Development"],
            "Left_Alpha_Angle": round(float(r["Left_Alpha_Angle"]), 2),
            "Left_Occlusal_Angle": round(float(r["Left_Occlusal_Angle"]), 2),
            "Left_D_mm": round(float(r["Left_D_mm"]), 2),
            "Left_Sector": r["Left_Sector"],
            "Left_Eruption_Assessment": r["Left_Eruption_Assessment"],
            "Left_Recommendation": r["Left_Recommendation"],
        }
        return row

    def update_master_results_file(self):
        """
        One master CSV:
        - new Patient ID -> append
        - existing Patient ID -> replace/update that row
        No landmark coordinates are exported.
        """
        new_row = self.build_master_result_row()
        patient_id = str(new_row["Patient_ID"]).strip()

        rows = []
        if self.master_results_path.exists() and self.master_results_path.stat().st_size:
            try:
                with self.master_results_path.open(
                    "r", newline="", encoding="utf-8-sig"
                ) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
            except Exception:
                rows = []

        replaced = False
        output_rows = []

        for row in rows:
            existing_id = str(row.get("Patient_ID", "")).strip()
            if existing_id.casefold() == patient_id.casefold():
                output_rows.append(new_row)
                replaced = True
            else:
                clean_row = {
                    field: row.get(field, "")
                    for field in MASTER_RESULTS_FIELDS
                }
                output_rows.append(clean_row)

        if not replaced:
            output_rows.append(new_row)

        temp_path = self.master_results_path.with_suffix(".tmp")
        with temp_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=MASTER_RESULTS_FIELDS
            )
            writer.writeheader()
            writer.writerows(output_rows)

        temp_path.replace(self.master_results_path)
        return replaced

    def save_patient(self):
        if not hasattr(self, "current_result"):
            QMessageBox.warning(
                self,
                "No Measurement",
                "Complete the landmark measurement first."
            )
            return

        patient_id = self.patient_id.text().strip()
        if not patient_id:
            QMessageBox.warning(
                self,
                "Patient ID Required",
                "Enter a Patient ID before saving."
            )
            return

        if not self.image_path or not Path(self.image_path).exists():
            QMessageBox.warning(
                self,
                "Image Missing",
                "The original panoramic image could not be found."
            )
            return

        # Make sure the result reflects any last field edits.
        self.calculate_results(show_errors=False)
        self.current_result["Patient_ID"] = patient_id

        record_path = self.patient_record_path(patient_id)
        image_dest = self.patient_image_destination(patient_id)
        traced_dest = self.patient_traced_destination(patient_id)

        try:
            # Preserve original source image separately.
            src_image = Path(self.image_path).resolve()
            if src_image != image_dest.resolve():
                shutil.copy2(src_image, image_dest)

            self.save_traced_image(traced_dest)

            record = {
                "format_version": 1,
                "patient_id": patient_id,
                "age": self.age.value(),
                "right_root_index": self.right_root.currentIndex(),
                "left_root_index": self.left_root.currentIndex(),
                "known_mm": self.known_mm.value(),
                "original_image": str(image_dest),
                "traced_image": str(traced_dest),
                "points": {
                    key: [float(point[0]), float(point[1])]
                    for key, point in self.points.items()
                },
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }

            temp_record = record_path.with_suffix(".json.tmp")
            temp_record.write_text(
                json.dumps(record, indent=2),
                encoding="utf-8"
            )
            temp_record.replace(record_path)

            was_update = self.update_master_results_file()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Save Error",
                str(exc)
            )
            return

        action = "updated" if was_update else "saved"
        self.instruction.setText(
            f"Patient {patient_id} {action} successfully."
        )

        QMessageBox.information(
            self,
            "Patient Saved",
            f"Patient {patient_id} was {action} successfully.\n\n"
            f"Results file:\n{self.master_results_path}\n\n"
            "The original OPG and editable tracing data were also saved."
        )

    def open_patient(self):
        records = sorted(self.records_dir.glob("*.json"))
        if not records:
            QMessageBox.information(
                self,
                "No Saved Patients",
                "No saved patient records were found yet."
            )
            return

        entries = []
        mapping = {}

        for path in records:
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                patient_id = str(record.get("patient_id", path.stem))
                entries.append(patient_id)
                mapping[patient_id] = path
            except Exception:
                continue

        if not entries:
            QMessageBox.warning(
                self,
                "Patient Records",
                "Saved patient records could not be read."
            )
            return

        entries.sort(key=str.casefold)

        patient_id, ok = QInputDialog.getItem(
            self,
            "Open Patient",
            "Select Patient ID:",
            entries,
            0,
            False
        )

        if not ok or not patient_id:
            return

        record_path = mapping[patient_id]

        try:
            record = json.loads(
                record_path.read_text(encoding="utf-8")
            )

            image_path = Path(record["original_image"])
            if not image_path.exists():
                QMessageBox.warning(
                    self,
                    "Image Missing",
                    "The patient record exists, but its original OPG "
                    "could not be found."
                )
                return

            self.view.load_image(str(image_path))
            self.image_path = str(image_path)

            self.patient_id.setText(str(record.get("patient_id", "")))
            self.age.setValue(float(record.get("age", 12.0)))
            self.right_root.setCurrentIndex(
                int(record.get("right_root_index", 0))
            )
            self.left_root.setCurrentIndex(
                int(record.get("left_root_index", 0))
            )
            self.known_mm.setValue(
                float(record.get("known_mm", 10.0))
            )

            loaded_points = record.get("points", {})
            self.points = {
                key: (float(value[0]), float(value[1]))
                for key, value in loaded_points.items()
                if (
                    isinstance(value, (list, tuple))
                    and len(value) == 2
                )
            }

            self.marker_items = {}
            self.line_items = []

            for i, (key, _) in enumerate(LANDMARK_SEQUENCE):
                if key in self.points:
                    self.draw_marker(
                        key,
                        self.points[key],
                        i + 1
                    )

            self.redraw_current_lines()

            self.click_index = sum(
                1 for key, _ in LANDMARK_SEQUENCE
                if key in self.points
            )

            self.progress.setText(
                f"Landmarks: {self.click_index} / "
                f"{len(LANDMARK_SEQUENCE)}"
            )

            complete = all(
                key in self.points
                for key, _ in LANDMARK_SEQUENCE
            )

            if complete:
                self.view.accept_landmarks = False
                self.calculate_results(show_errors=False)
                self.save_button.setEnabled(True)
                self.instruction.setText(
                    f"Patient {patient_id} opened. "
                    "Drag any landmark to edit, then click Save Patient "
                    "to update the same record."
                )
            else:
                self.view.accept_landmarks = True
                self.update_instruction()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Open Patient Error",
                str(exc)
            )

    # ========================================================
    # UPDATE CHECKER
    # ========================================================

    def _load_settings(self):
        try:
            if self.settings_path.exists():
                return json.loads(
                    self.settings_path.read_text(encoding="utf-8")
                )
        except Exception:
            pass
        return {}

    def _save_settings(self, settings):
        try:
            self.settings_path.write_text(
                json.dumps(settings, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def maybe_check_for_updates(self):
        settings = self._load_settings()
        last_text = settings.get("last_update_check")

        should_check = True
        if last_text:
            try:
                last = datetime.fromisoformat(last_text)
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                should_check = (
                    datetime.now(timezone.utc) - last
                    >= timedelta(days=UPDATE_CHECK_DAYS)
                )
            except Exception:
                should_check = True

        if should_check:
            self.check_for_updates(manual=False)

    def check_for_updates(self, manual=False):
        thread = threading.Thread(
            target=self._update_check_worker,
            args=(manual,),
            daemon=True
        )
        thread.start()

    def _update_check_worker(self, manual):
        try:
            request = urllib.request.Request(
                GITHUB_LATEST_RELEASE_API,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "PDC-Analyzer"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=4
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

            latest = str(payload.get("tag_name", "")).lstrip("vV")
            release_url = str(
                payload.get("html_url", GITHUB_RELEASES_URL)
            )

            settings = self._load_settings()
            settings["last_update_check"] = (
                datetime.now(timezone.utc).isoformat()
            )
            self._save_settings(settings)

            if latest and version_tuple(latest) > version_tuple(APP_VERSION):
                self.update_available.emit(latest, release_url)
            elif manual:
                self.update_check_finished.emit(
                    f"You are using the latest available version ({APP_VERSION})."
                )

        except Exception:
            # Automatic checks remain completely silent if offline.
            if manual:
                self.update_check_finished.emit(
                    "Could not check for updates. "
                    "Please check your internet connection and try again."
                )

    def show_update_available(self, latest_version, release_url):
        result = QMessageBox.question(
            self,
            "PDC Analyzer Update",
            f"A newer version is available: v{latest_version}\n"
            f"Current version: v{APP_VERSION}\n\n"
            "Open the download page now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if result == QMessageBox.Yes:
            webbrowser.open(release_url)

    def show_manual_update_result(self, message):
        QMessageBox.information(
            self,
            "Check for Updates",
            message
        )


# ============================================================
# RUN APP
# ============================================================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
