from PyQt4 import QtGui, QtCore
from lib.mlt import mlt as mlt

mlt.Factory.init()
mlt_profile = mlt.Profile('hdv_720_25p')

class PlayerWindow(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.setGeometry(0, 0, 320, 180+50)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        self.setMaximumSize(QtCore.QSize(320, 180+50))
        self.setMinimumSize(QtCore.QSize(320, 180+50))

        self.clip = None
        self.playhead = 0
        self.playheadX = 0

        self.img = QtGui.QImage()

        self.imgPlayhead = 0

        self.clip_length = 0

    def setClip(self, clip):
        self.clip = clip

        self.producer = mlt.Producer(mlt_profile, clip.path)

        self.consumer =  mlt.Consumer(mlt_profile, "sdl")
        self.consumer.set("rescale", "none")
        self.consumer.set("window_id", int(self.winId()))

        self.consumer.connect(self.producer)
        #self.m_consumer.start()

        self.clip_length = self.producer.get_length()

        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)

        darkBgColor = self.palette().color(QtGui.QPalette.Window).darker(120)
        painter.fillRect(QtCore.QRect(0, 0, self.width(), self.height()), darkBgColor)

        if self.clip:

            color = [c*255 for c in self.clip._color]
            white = QtGui.QColor(255, 255, 255)

            painter.setPen(QtGui.QColor(*color))
            painter.setBrush(QtGui.QColor(*color))

            painter.drawRoundedRect(QtCore.QRect(0, 180+5, self.width()-1, 40), 3, 3)

            painter.setPen(white)
            painter.drawLine(self.playhead, 180, self.playhead, self.height())

            in_pos = self.width()*self.clip.in_frame/self.clip_length
            out_pos = self.width()*self.clip.out_frame/self.clip_length

            painter.setBrush(white)
            off = 3

            polygon1 = QtGui.QPolygonF()

            polygon1.append(QtCore.QPointF(in_pos, 185))
            polygon1.append(QtCore.QPointF(in_pos-off, 185-off))
            polygon1.append(QtCore.QPointF(in_pos+off, 185-off))

            painter.drawPolygon(polygon1)

            polygon1 = QtGui.QPolygonF()

            polygon1.append(QtCore.QPointF(out_pos, 185))
            polygon1.append(QtCore.QPointF(out_pos-off, 185-off))
            polygon1.append(QtCore.QPointF(out_pos+off, 185-off))

            painter.drawPolygon(polygon1)

            painter.drawText(0, 180+50, "%d" % self.playheadX)

            w = 1280
            h = 720

            if self.imgPlayhead != self.playheadX:

                self.imgPlayhead = self.playheadX

                frame = self.consumer.get_frame()
                frame.set("consumer_deinterlace", 1)

                size = (w, h)
                rgb = frame.get_image(mlt.mlt_image_rgb24, *size)

                self.img = QtGui.QImage(rgb, size[0], size[1], QtGui.QImage.Format_RGB888)

            painter.drawImage(QtCore.QRect(0, 0, 320, 180), self.img, QtCore.QRect(0, 0, w, h))

        painter.end()

    def keyPressEvent(self, event):
        QtGui.QWidget.keyPressEvent(self, event)

        if event.key() == QtCore.Qt.Key_Left:
            self.playheadX -= 1
            self.update()

        elif event.key() == QtCore.Qt.Key_Right:
            self.playheadX += 1
            self.update()

        elif event.key() == QtCore.Qt.Key_I: # move in point
            self.clip.in_frame = self.playheadX
            self.update()

        elif event.key() == QtCore.Qt.Key_O: # move out point
            self.clip.out_frame = self.playheadX
            self.update()

    def mouseMoveEvent(self, event):

        QtGui.QWidget.mouseMoveEvent(self, event)

        if event.buttons() & QtCore.Qt.LeftButton:
            self.playhead = event.pos().x()

            self.playhead = max(0, self.playhead)

            self.playheadX = self.playhead*self.clip_length/self.width()

            self.consumer.purge()
            self.producer.set_speed(0)
            self.producer.seek(self.playheadX)
            self.producer.set_speed(1)

            self.update()

    def mousePressEvent(self, event):

        QtGui.QWidget.mousePressEvent(self, event)

        if event.buttons() & QtCore.Qt.LeftButton:
            self.playhead = event.pos().x()
            self.update()

class ParameterWindow(QtGui.QWidget):

    def __init__(self, main_window=None, parent=None):
        QtGui.QWidget.__init__(self, parent)

        if __name__ != '__main__':
            self.setWindowFlags(QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool | QtCore.Qt.CustomizeWindowHint)

        self.setWindowTitle("properties")

        self.setStyleSheet("""font-size:10pt; background-color: rgb(70, 70, 70); color: rgb(255, 255, 255);""")

        self.setGeometry(0, 0, 320, 500)

        self.mainLayout = QtGui.QVBoxLayout(self)
        self.mainLayout.setSpacing(0)
        self.mainLayout.setContentsMargins(2, 2, 2, 2)

        self.layout = QtGui.QFormLayout()
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(3, 3, 3, 3)

        self.keys = []
        self.values = []
        self.node = None

        self.editors = {}

        self.main_window = main_window

        self.player = PlayerWindow(self)

        self.mainLayout.addWidget(self.player)
        self.mainLayout.addLayout(self.layout)
        self.mainLayout.addStretch(1)

    def setData(self, node, keys, values):

        if node == self.node:
            if node != None:
                for k, v in zip(keys, values):
                    self.editors[k].setText(str(v))
                return

        self.setUpdatesEnabled(False)

        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)

        self.keys = keys
        self.values = values

        self.node = node

        self.editors.clear()

        for k, v in zip(keys, values):

            label = QtGui.QLabel(k, self)
            label.setStyleSheet("background-color: transparent; color: rgb(255, 255, 255);")

            lineEdit = QtGui.QLineEdit(str(v), self)
            lineEdit.setStyleSheet("""border-radius: 3px;
                                      border-top: 1px solid rgb(55, 55, 55);
                                      border-left: 1px solid rgb(55, 55, 55);
                                      border-bottom: 1px solid rgb(103, 103, 103);
                                      border-right: 1px solid rgb(103, 103, 103);

                                      color: rgb(255, 255, 255);
                                      background-color: black; """)
            lineEdit.paramName = k

            self.editors[k] = lineEdit

            self.layout.addRow(label, lineEdit)

            self.connect(lineEdit, QtCore.SIGNAL("returnPressed()"), self.onEditingFinished)
            self.connect(lineEdit, QtCore.SIGNAL("editingFinished()"), self.onEditingFinished)

        self.player.setClip(node)
        #self.control.setClip(node)

        self.setUpdatesEnabled(True)

    def onEditingFinished(self):
        editor = self.sender()

        if self.node:
            self.node.setData(editor.paramName, float(str(editor.text())))

        if self.main_window:
            self.main_window.update()

        self.update()

if __name__ == '__main__':

    app = QtGui.QApplication([])

    f = ParameterWindow()
    f.show()
    f.raise_()

    f.setGeometry(100, 100, 320, 500)

    from lib import core
    import random

    hue = random.random()

    color = QtGui.QColor.fromHsvF(hue, 0.5, 0.75)
    r, g, b = color.redF(), color.greenF(), color.blueF()

    clip = core.Clip()
    clip._color = (r, g, b, 1)
    clip.name = "clip_1"

    clip.start_frame = 120
    clip.end_frame = 120+119

    clip.in_frame = 10
    clip.out_frame = 110

    clip.track = 0
    clip.path = "../media/output%d.mov" % (clip.track+1)

    f.setData(clip, ["in_frame", "out_frame", "start_frame", "end_frame", "track"], [clip.in_frame, clip.out_frame, clip.start_frame, clip.end_frame, clip.track])
    #f.setData(clip, ["in", "out", "start", "stop", "track"], [0, 1, 100, 200, 0])
    #f.setData(clip, ["in", "out", "start", "stop", "track"], [0, 1, 100, 200, 0])

    app.exec_()
