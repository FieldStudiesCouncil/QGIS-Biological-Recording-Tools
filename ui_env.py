# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_env.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Env(object):
    def setupUi(self, Env):
        Env.setObjectName("Env")
        Env.resize(523, 521)
        self.verticalLayout = QtWidgets.QVBoxLayout(Env)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabWidget = QtWidgets.QTabWidget(Env)
        self.tabWidget.setEnabled(True)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setEnabled(True)
        self.tab.setObjectName("tab")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.tab)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.pteEnvironment = QtWidgets.QPlainTextEdit(self.tab)
        self.pteEnvironment.setEnabled(True)
        self.pteEnvironment.setObjectName("pteEnvironment")
        self.verticalLayout_3.addWidget(self.pteEnvironment)
        self.groupBox = QtWidgets.QGroupBox(self.tab)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.leExternalEnvFile = QtWidgets.QLineEdit(self.groupBox)
        self.leExternalEnvFile.setObjectName("leExternalEnvFile")
        self.horizontalLayout.addWidget(self.leExternalEnvFile)
        self.pbExternalEnvFile = QtWidgets.QPushButton(self.groupBox)
        self.pbExternalEnvFile.setObjectName("pbExternalEnvFile")
        self.horizontalLayout.addWidget(self.pbExternalEnvFile)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.pbSaveToNewEnvFile = QtWidgets.QPushButton(self.groupBox)
        self.pbSaveToNewEnvFile.setMaximumSize(QtCore.QSize(96, 16777215))
        self.pbSaveToNewEnvFile.setObjectName("pbSaveToNewEnvFile")
        self.verticalLayout_2.addWidget(self.pbSaveToNewEnvFile)
        self.verticalLayout_3.addWidget(self.groupBox)
        self.tabWidget.addTab(self.tab, "")
        self.tab2 = QtWidgets.QWidget()
        self.tab2.setObjectName("tab2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.tab2)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pteExample = QtWidgets.QPlainTextEdit(self.tab2)
        self.pteExample.setEnabled(True)
        self.pteExample.setObjectName("pteExample")
        self.horizontalLayout_2.addWidget(self.pteExample)
        self.tabWidget.addTab(self.tab2, "")
        self.verticalLayout.addWidget(self.tabWidget)
        self.bbButtons = QtWidgets.QDialogButtonBox(Env)
        self.bbButtons.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.bbButtons.setObjectName("bbButtons")
        self.verticalLayout.addWidget(self.bbButtons)

        self.retranslateUi(Env)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Env)

    def retranslateUi(self, Env):
        _translate = QtCore.QCoreApplication.translate
        Env.setWindowTitle(_translate("Env", "FSC QGIS plugin - Environment"))
        self.groupBox.setTitle(_translate("Env", "External environment file"))
        self.pbExternalEnvFile.setToolTip(_translate("Env", "<html><head/><body><p>Set from an \'external\' environment file. The internal environment file is lost whenever the plugin is updated. To avoid the nuisance caused by this, you can keep your environment file somewhere safe on your computer and just link to it from here.</p></body></html>"))
        self.pbExternalEnvFile.setText(_translate("Env", "Browse"))
        self.pbSaveToNewEnvFile.setToolTip(_translate("Env", "<html><head/><body><p>You can use this button to save the current environment to a new external file. (This is only required to create a new external file - if you are already using an external file, changes to the environment are automatically saved there.)</p></body></html>"))
        self.pbSaveToNewEnvFile.setText(_translate("Env", "Save to new"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("Env", "Your environment"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab2), _translate("Env", "Example environment"))

