from numpy import zeros, reshape, linalg, array, dot
from numpy import float32 as npfloat

from PyQt4 import QtCore

class Camera(object):
    def __init__(self):
        self.clear()
        self.m = []

    def clear(self):
        self.m = zeros([9 + 7], dtype=npfloat)

    def identity(self):
        self.clear()
        self.m[0] = 1
        self.m[5] = 1
        self.m[10] = 1
        self.m[15] = 1

    def values(self):
        return [self.m[12], self.m[13], self.m[0]]

    def setValues(self, data):
        self.identity()

        self.m[12] = npfloat(data[0])
        self.m[13] = npfloat(data[1])
        self.m[0]  = npfloat(data[2])

    def translate(self, dx, dy):
        self.m[12] += dx
        self.m[13] += dy

    def scale(self, ds):
        self.m[0] *= ds
        self.m[5] *= ds

    def _reshaped(self):
        return reshape(self.m, (2 * 2, 2 * 2), "F")

    def _inverted(self):
        return linalg.inv(self._reshaped())

    def opengl_to_qt(self, point):
        p = array([point.x(), point.y(), 0, 1], dtype=npfloat)
        a = dot(self._reshaped(), p)
        return QtCore.QPoint(a[0], a[1])

    def qt_to_opengl(self, point):
        p = array([point.x(), point.y(), 0, 1], dtype=npfloat)
        a = dot(self._inverted(), p)
        return QtCore.QPoint(a[0], a[1]) # should I pre-create instance of QPoint instead?

