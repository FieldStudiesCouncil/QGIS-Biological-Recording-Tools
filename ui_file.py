# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_file.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_File(object):
    def setupUi(self, File):
        File.setObjectName("File")
        File.resize(317, 388)
        self.verticalLayout = QtWidgets.QVBoxLayout(File)
        self.verticalLayout.setObjectName("verticalLayout")
        self.pteEnvironment = QtWidgets.QPlainTextEdit(File)
        self.pteEnvironment.setObjectName("pteEnvironment")
        self.verticalLayout.addWidget(self.pteEnvironment)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.pbClose = QtWidgets.QPushButton(File)
        self.pbClose.setObjectName("pbClose")
        self.horizontalLayout.addWidget(self.pbClose)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(File)
        QtCore.QMetaObject.connectSlotsByName(File)

    def retranslateUi(self, File):
        _translate = QtCore.QCoreApplication.translate
        File.setWindowTitle(_translate("File", "FSC QGIS plugin - Information"))
        self.pbClose.setText(_translate("File", "Close"))

