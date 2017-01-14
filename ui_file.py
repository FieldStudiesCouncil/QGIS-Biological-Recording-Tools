# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_file.ui'
#
# Created: Sat Jan 14 14:59:26 2017
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_File(object):
    def setupUi(self, File):
        File.setObjectName(_fromUtf8("File"))
        File.resize(317, 388)
        self.verticalLayout = QtGui.QVBoxLayout(File)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.pteEnvironment = QtGui.QPlainTextEdit(File)
        self.pteEnvironment.setObjectName(_fromUtf8("pteEnvironment"))
        self.verticalLayout.addWidget(self.pteEnvironment)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.pbClose = QtGui.QPushButton(File)
        self.pbClose.setObjectName(_fromUtf8("pbClose"))
        self.horizontalLayout.addWidget(self.pbClose)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(File)
        QtCore.QMetaObject.connectSlotsByName(File)

    def retranslateUi(self, File):
        File.setWindowTitle(_translate("File", "FSC Tom.bio - Information", None))
        self.pbClose.setText(_translate("File", "Close", None))

