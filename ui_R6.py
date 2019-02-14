# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_r6.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_R6(object):
    def setupUi(self, R6):
        R6.setObjectName("R6")
        R6.resize(974, 606)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("images/R6.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        R6.setWindowIcon(icon)
        self.lbR6Select = QtWidgets.QLabel(R6)
        self.lbR6Select.setEnabled(False)
        self.lbR6Select.setGeometry(QtCore.QRect(40, 200, 491, 34))
        self.lbR6Select.setObjectName("lbR6Select")
        self.butR6Match = QtWidgets.QPushButton(R6)
        self.butR6Match.setGeometry(QtCore.QRect(580, 60, 301, 57))
        self.butR6Match.setObjectName("butR6Match")
        self.butGetR6Data = QtWidgets.QPushButton(R6)
        self.butGetR6Data.setEnabled(False)
        self.butGetR6Data.setGeometry(QtCore.QRect(460, 360, 187, 57))
        self.butGetR6Data.setObjectName("butGetR6Data")
        self.cmbSpToMap = QtWidgets.QComboBox(R6)
        self.cmbSpToMap.setEnabled(False)
        self.cmbSpToMap.setGeometry(QtCore.QRect(40, 260, 861, 40))
        self.cmbSpToMap.setObjectName("cmbSpToMap")
        self.leR6SpToMatch = QtWidgets.QLineEdit(R6)
        self.leR6SpToMatch.setGeometry(QtCore.QRect(190, 70, 351, 40))
        self.leR6SpToMatch.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.leR6SpToMatch.setObjectName("leR6SpToMatch")
        self.cbIncSpBelow = QtWidgets.QCheckBox(R6)
        self.cbIncSpBelow.setEnabled(False)
        self.cbIncSpBelow.setGeometry(QtCore.QRect(50, 360, 281, 37))
        self.cbIncSpBelow.setObjectName("cbIncSpBelow")
        self.butCancel = QtWidgets.QPushButton(R6)
        self.butCancel.setGeometry(QtCore.QRect(460, 450, 187, 57))
        self.butCancel.setObjectName("butCancel")

        self.retranslateUi(R6)
        QtCore.QMetaObject.connectSlotsByName(R6)

    def retranslateUi(self, R6):
        _translate = QtCore.QCoreApplication.translate
        R6.setWindowTitle(_translate("R6", "Get Recorder 6 data"))
        self.lbR6Select.setText(_translate("R6", "Select the taxon to map from the list:"))
        self.butR6Match.setText(_translate("R6", "Match taxon name..."))
        self.butGetR6Data.setText(_translate("R6", "Get R6 data"))
        self.cbIncSpBelow.setText(_translate("R6", "Include taxa below"))
        self.butCancel.setText(_translate("R6", "Cancel"))

