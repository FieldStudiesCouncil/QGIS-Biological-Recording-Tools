# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_R6Credentials.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_R6Credentials(object):
    def setupUi(self, R6Credentials):
        R6Credentials.setObjectName("R6Credentials")
        R6Credentials.resize(337, 143)
        font = QtGui.QFont()
        font.setPointSize(8)
        R6Credentials.setFont(font)
        R6Credentials.setModal(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(R6Credentials)
        self.verticalLayout.setObjectName("verticalLayout")
        self.leR6Server = QtWidgets.QLineEdit(R6Credentials)
        self.leR6Server.setObjectName("leR6Server")
        self.verticalLayout.addWidget(self.leR6Server)
        self.leR6User = QtWidgets.QLineEdit(R6Credentials)
        self.leR6User.setObjectName("leR6User")
        self.verticalLayout.addWidget(self.leR6User)
        self.leR6Password = QtWidgets.QLineEdit(R6Credentials)
        self.leR6Password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.leR6Password.setObjectName("leR6Password")
        self.verticalLayout.addWidget(self.leR6Password)
        spacerItem = QtWidgets.QSpacerItem(20, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.bbDialogButtons = QtWidgets.QDialogButtonBox(R6Credentials)
        self.bbDialogButtons.setOrientation(QtCore.Qt.Horizontal)
        self.bbDialogButtons.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.bbDialogButtons.setObjectName("bbDialogButtons")
        self.verticalLayout.addWidget(self.bbDialogButtons)

        self.retranslateUi(R6Credentials)
        self.bbDialogButtons.accepted.connect(R6Credentials.accept)
        self.bbDialogButtons.rejected.connect(R6Credentials.reject)
        QtCore.QMetaObject.connectSlotsByName(R6Credentials)

    def retranslateUi(self, R6Credentials):
        _translate = QtCore.QCoreApplication.translate
        R6Credentials.setWindowTitle(_translate("R6Credentials", "Enter Recorder 6 credentials"))
        self.leR6Server.setPlaceholderText(_translate("R6Credentials", "Enter Recorder 6 server name"))
        self.leR6User.setPlaceholderText(_translate("R6Credentials", "Enter database user name"))
        self.leR6Password.setPlaceholderText(_translate("R6Credentials", "Enter database password"))

