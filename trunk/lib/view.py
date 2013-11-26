from PyQt4 import QtCore, QtOpenGL
import pprint
import os
import math

from OpenGL.GL import *

from lib.camera import Camera

texture_mode = GL_TEXTURE_RECTANGLE

class GLView(QtOpenGL.QGLWidget):
    _zoom_coeff = 0.05
    _scale_coeff = 1.2
    _scale_coeff1 = 1/_scale_coeff

    def __init__(self, parent=None):
        QtOpenGL.QGLWidget.__init__(self, parent)

        self.setAutoFillBackground(False)

        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)

        self.setAttribute(QtCore.Qt.WA_StaticContents, True)
        self.setAttribute(QtCore.Qt.WA_PaintOnScreen, True)

        self.setMouseTracking(True)

        self._mousePos = QtCore.QPoint()
        self._zoomAnchor = QtCore.QPoint()
        self.zoomPos1 = QtCore.QPoint()
        self.zoomPos2 = QtCore.QPoint()

        self.camera = Camera()
        self.camera.identity()

        self.settings = {}
        self.settingsFilename = os.path.expanduser("~/%s.%s" % ("editor", "settings"))

        self.loadSettings()

        self.move(self.settings.get("x", 0), self.settings.get("y", 0))
        self.resize(self.settings.get("w", 450), self.settings.get("h", 700))


    def saveSettings(self):
        fout = open(self.settingsFilename, "w")
        pprint.pprint(self.settings, fout)
        fout.close()

    def loadSettings(self):
        try:
            fin = open(self.settingsFilename, "r")
            self.settings = eval(fin.read())
            fin.close()
        except:
            pass

    def moveEvent(self, event):
        self.settings["x"] = self.x()
        self.settings["y"] = self.y()
        QtOpenGL.QGLWidget.moveEvent(self, event)

    def resizeEvent(self, event):
        self.settings["w"] = self.width()
        self.settings["h"] = self.height()
        QtOpenGL.QGLWidget.resizeEvent(self, event)

    def closeEvent(self, event):
        self.saveSettings()
        QtOpenGL.QGLWidget.closeEvent(self, event)

    def glInit(self):
        QtOpenGL.QGLWidget.glInit(self)

    def initializeGL(self):
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, self.width(), self.height(), 0.0, -1.0, 1.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def convertNumpyToGLTexture(self, rgb): # rgb should be numpy array

        glEnable(texture_mode)

        tex_id = glGenTextures(1)

        glBindTexture(texture_mode, tex_id)

        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(texture_mode, 0, GL_RGB, rgb.shape[0], rgb.shape[1], 0, GL_RGB, GL_UNSIGNED_BYTE, rgb)
        glTexParameterf(texture_mode, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameterf(texture_mode, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameterf(texture_mode, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(texture_mode, GL_TEXTURE_MIN_FILTER, GL_NEAREST)

        glDisable(texture_mode)

        return tex_id

    def resizeGL(self, width, height):
        self.setUpdatesEnabled(False)

        glViewport(0, 0, self.rect().width(), self.rect().height())
        self.initializeGL()

        self.setUpdatesEnabled(True)

    def _beforeScale(self):
        self.zoomPos1 = self.camera.qt_to_opengl(self._zoomAnchor)

    def _afterScale(self):
        self.zoomPos2 = self.camera.qt_to_opengl(self._zoomAnchor)
        self.camera.translate((self.zoomPos2.x() - self.zoomPos1.x()) * self.camera.m[0],
                              (self.zoomPos2.y() - self.zoomPos1.y()) * self.camera.m[0])

    def wheelEvent(self, event):
        self._zoomAnchor = event.pos()

        self._beforeScale()

        # math.pow(self._scale_coeff, math.copysign(1, event.delta()))
        # => 3 times slower (as measured with timeit module)

        if event.delta() > 0:
            self.camera.scale(self._scale_coeff)
        else:
            self.camera.scale(self._scale_coeff1)

        self._afterScale()

    def mousePressEvent(self, event):
        QtOpenGL.QGLWidget.mousePressEvent(self, event)

        self._mousePos = event.pos()
        self._zoomAnchor = event.pos()

        #if event.buttons() & QtCore.Qt.LeftButton:
        #    self.playhead = event.x()

        self.update()

    def mouseReleaseEvent(self, event):
        QtOpenGL.QGLWidget.mouseReleaseEvent(self, event)

        self._mousePos = event.pos()

        self.update()

    def mouseMoveEvent(self, event):
        QtOpenGL.QGLWidget.mouseMoveEvent(self, event)

        dx = event.x() - self._mousePos.x()
        dy = event.y() - self._mousePos.y()

        self._mousePos = event.pos()

        if (event.buttons() & QtCore.Qt.MidButton) and (event.modifiers() & QtCore.Qt.AltModifier):
            self.camera.translate(dx, dy)

        elif (event.buttons() & QtCore.Qt.RightButton) and (event.modifiers() & QtCore.Qt.AltModifier):
            self._beforeScale()
            self.camera.scale(1.0 + math.copysign(self._zoom_coeff, dx))
            self._afterScale()

        self.update()
