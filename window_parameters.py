from PyQt4 import QtGui, QtCore

class ParameterWindow(QtGui.QWidget):

    def __init__(self, main_window=None, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.setWindowFlags(QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool | QtCore.Qt.CustomizeWindowHint)
        self.setWindowTitle("properties")

        self.setStyleSheet("""font-size:10pt; background-color: rgb(70, 70, 70); color: rgb(255, 255, 255);""")

        self.setGeometry(0, 0, 300, 480)

        self.layout = QtGui.QFormLayout(self)

        self.keys = []
        self.values = []
        self.node = None

        self.editors = {}

        self.main_window = main_window

    def setData(self, node, keys, values):

        #print "setData", node, keys, values

        if node == self.node:
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

        self.setUpdatesEnabled(True)

    def onEditingFinished(self):
        editor = self.sender()

        if self.node:
            self.node.setData(editor.paramName, float(str(editor.text())))

        if self.main_window:
            self.main_window.update()

if __name__ == '__main__':

    app = QtGui.QApplication([])

    f = ParameterWindow()
    f.show()
    f.raise_()

    f.setData(None, ["in", "out", "start", "stop", "track"], [0, 1, 100, 200, 0])
    f.setData(None, ["in", "out", "start", "stop", "track"], [0, 1, 100, 200, 0])
    f.setData(None, ["in", "out", "start", "stop", "track"], [0, 1, 100, 200, 0])

    app.exec_()
