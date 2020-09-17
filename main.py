import sys
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, qRgb, QMouseEvent
from PyQt5.QtWidgets import *
from libimg import Image


class MainWindow(QMainWindow):
    def __init__(self, image_widget: QWidget = None, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        if image_widget is None:
            image_widget = ImageWidget()
        self._image_widget = image_widget

        # Set title and initial size
        self.setWindowTitle("libIMG Editor")
        self.resize(500, 500)

        # menu bar
        menubar = QMenuBar()
        self.setMenuBar(menubar)
        file_menu = menubar.addMenu("File")
        file_menu.aboutToShow.connect(self.file_menu_action_show)
        file_menu.aboutToHide.connect(self.file_menu_action_hide)
        self._new_action = QAction("New", self)
        self._new_action.setShortcut("Ctrl+N")
        self._new_action.triggered.connect(self.new_file_action)
        file_menu.addAction(self._new_action)
        self._open_action = QAction("Open", self)
        self._open_action.setShortcut("Ctrl+O")
        self._open_action.triggered.connect(self.open_file_action)
        file_menu.addAction(self._open_action)
        self._save_action = QAction("Save", self)
        self._save_action.setShortcut("Ctrl+S")
        self._save_action.triggered.connect(self.save_file_action)
        file_menu.addAction(self._save_action)

        self.setCentralWidget(image_widget)

    def file_menu_action_show(self):
        """
        Runs when the File menu is opened
        """

        # Disable save action if no image is loaded
        self._save_action.setEnabled(bool(self._image_widget.get_image()))

    def file_menu_action_hide(self):
        """
        Runs when the File menu is closed
        """

        # Re-enable actions so that shortcuts work
        self._new_action.setEnabled(True)
        self._open_action.setEnabled(True)
        self._save_action.setEnabled(True)

    def open_file_action(self):
        """
        Runs when the Open option is clicked in the menubar
        """
        dialog = QFileDialog()
        filepath = dialog.getOpenFileName(self, caption="Choose the file to open",
                                          filter="libIMG files (*.limg);;All files (*.*)")
        filepath = filepath[0]

        # Check if something was chosen
        if not filepath:
            return

        try:
            self._image_widget.set_image(Image.from_file(filepath))
        except ValueError as e:
            error_box = QMessageBox(self)
            error_box.setIcon(QMessageBox.Critical)
            error_box.setText("Error")
            error_box.setInformativeText(str(e))
            error_box.setWindowTitle("Error loading file")
            error_box.show()

    def new_file_action(self):
        """
        Runs when the New option is clicked in the menubar
        """
        diag = NewFileDialog()
        if diag.exec_() == QDialog.Accepted:
            pixel_array = []
            if diag.get_image_format() == Image.Format_BW:
                # Initialize array in all white
                pixel_array = [[0 for _ in range(diag.get_image_width())] for _ in range(diag.get_image_height())]

            new_image = Image(pixel_array, diag.get_image_format())
            self._image_widget.set_image(new_image)
            self._image_widget.set_edit_mode(True)

    def save_file_action(self):
        """
        Runs when the Save option is clicked in the menubar
        """

        # If no image, don't do anything
        if not self._image_widget.get_image():
            return

        dialog = QFileDialog()
        filepath = dialog.getSaveFileName(self, caption="Choose where to save the image")
        filepath = filepath[0]

        # Only try to save if user chose a path and there is an image loaded
        if not filepath:
            return

        self._image_widget.get_image().write_to_file(filepath)


class ImageWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self._image: Optional[Image] = None
        self._qimage = None
        self._edit_mode = False

        layout = QGridLayout()

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignTop)

        layout.addWidget(self._label, 0, 0)

        self.setLayout(layout)

    def get_image(self):
        return self._image

    def set_image(self, image: Image):
        self._image = image
        self._draw_image()

    def set_edit_mode(self, mode: bool):
        self._edit_mode = mode

    def _draw_image(self):
        black = qRgb(0, 0, 0)
        white = qRgb(255, 255, 255)

        # Create initial QImage (good dimensions, all white)
        self._qimage = QImage(self._image.get_width(), self._image.get_height(), QImage.Format_RGB32)
        self._qimage.fill(white)

        pixel_array = self._image.to_array()

        if self._image.get_image_format() == Image.Format_BW:
            # B & W format, 1 == black,  0 == white
            for row in range(self._image.get_height()):
                for col in range(self._image.get_width()):
                    color = black if int(pixel_array[row][col]) == 1 else white
                    self._qimage.setPixel(col, row, color)

        self._label.setPixmap(QPixmap.fromImage(self._qimage.scaledToHeight(300)))

    def _draw_pixel(self, event: QMouseEvent):
        # Only run if an image is currently loaded and we're in edit mode
        if not self._image or not self._edit_mode:
            return

        pixel_size = 300 // self._image.get_height()  # TODO change 300 by scale factor

        # Subtract 9 because of border around label
        x_pos = (event.pos().x() - 9) // pixel_size
        y_pos = (event.pos().y() - 9) // pixel_size

        # If click is outside of image, do nothing
        if x_pos >= self._image.get_width() or y_pos >= self._image.get_height():
            return

        pixel_array = self._image.to_array()
        pixel_array[y_pos][x_pos] = 1
        self._image = Image(pixel_array, self._image.get_image_format())
        self._draw_image()

    def mouseMoveEvent(self, event: QMouseEvent):
        self._draw_pixel(event)

    def mousePressEvent(self, event: QMouseEvent):
        self._draw_pixel(event)


class NewFileDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # Removes "?" button flag
        self.setWindowTitle("Create a new image")

        layout = QFormLayout()

        self._width_spinbox = QSpinBox()
        self._width_spinbox.setRange(1, 65535)  # 655535 = 2^16 - 1 since we use 2 bytes to determine dimensions

        self._height_spinbox = QSpinBox()
        self._height_spinbox.setRange(1, 65535)

        layout.addRow(QLabel("Width:"), self._width_spinbox)
        layout.addRow(QLabel("Height:"), self._height_spinbox)

        self._image_format_box = QComboBox()
        self._image_format_box.addItem("Black and white")

        layout.addRow(QLabel("Image format:"), self._image_format_box)

        self._button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        layout.addRow(self._button_box)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        self.setLayout(layout)

    def get_image_width(self):
        return self._width_spinbox.value()

    def get_image_height(self):
        return self._height_spinbox.value()

    def get_image_format(self):
        return self._image_format_box.currentIndex()


app = QApplication(sys.argv)
window = MainWindow()
window.show()

sys.exit(app.exec_())
