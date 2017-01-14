# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_env.ui'
#
# Created: Sat Jan 14 14:58:59 2017
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

class Ui_Env(object):
    def setupUi(self, Env):
        Env.setObjectName(_fromUtf8("Env"))
        Env.resize(523, 521)
        self.verticalLayout = QtGui.QVBoxLayout(Env)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.tabWidget = QtGui.QTabWidget(Env)
        self.tabWidget.setEnabled(True)
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab = QtGui.QWidget()
        self.tab.setEnabled(True)
        self.tab.setObjectName(_fromUtf8("tab"))
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.tab)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.pteEnvironment = QtGui.QPlainTextEdit(self.tab)
        self.pteEnvironment.setEnabled(True)
        self.pteEnvironment.setObjectName(_fromUtf8("pteEnvironment"))
        self.verticalLayout_3.addWidget(self.pteEnvironment)
        self.groupBox = QtGui.QGroupBox(self.tab)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.leExternalEnvFile = QtGui.QLineEdit(self.groupBox)
        self.leExternalEnvFile.setObjectName(_fromUtf8("leExternalEnvFile"))
        self.horizontalLayout.addWidget(self.leExternalEnvFile)
        self.pbExternalEnvFile = QtGui.QPushButton(self.groupBox)
        self.pbExternalEnvFile.setObjectName(_fromUtf8("pbExternalEnvFile"))
        self.horizontalLayout.addWidget(self.pbExternalEnvFile)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.pbSaveToNewEnvFile = QtGui.QPushButton(self.groupBox)
        self.pbSaveToNewEnvFile.setMaximumSize(QtCore.QSize(96, 16777215))
        self.pbSaveToNewEnvFile.setObjectName(_fromUtf8("pbSaveToNewEnvFile"))
        self.verticalLayout_2.addWidget(self.pbSaveToNewEnvFile)
        self.verticalLayout_3.addWidget(self.groupBox)
        self.tabWidget.addTab(self.tab, _fromUtf8(""))
        self.tab2 = QtGui.QWidget()
        self.tab2.setObjectName(_fromUtf8("tab2"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.tab2)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.pteExample = QtGui.QPlainTextEdit(self.tab2)
        self.pteExample.setEnabled(True)
        self.pteExample.setObjectName(_fromUtf8("pteExample"))
        self.horizontalLayout_2.addWidget(self.pteExample)
        self.tabWidget.addTab(self.tab2, _fromUtf8(""))
        self.verticalLayout.addWidget(self.tabWidget)
        self.bbButtons = QtGui.QDialogButtonBox(Env)
        self.bbButtons.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.bbButtons.setObjectName(_fromUtf8("bbButtons"))
        self.verticalLayout.addWidget(self.bbButtons)

        self.retranslateUi(Env)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Env)

    def retranslateUi(self, Env):
        Env.setWindowTitle(_translate("Env", "FSC Tom.bio - Environment", None))
        self.groupBox.setTitle(_translate("Env", "External environment file", None))
        self.pbExternalEnvFile.setToolTip(_translate("Env", "<html><head/><body><p>Set from an \'external\' environment file. The internal environment file is lost whenever the plugin is updated. To avoid the nuisance caused by this, you can keep your environment file somewhere safe on your computer and just link to it from here.</p></body></html>", None))
        self.pbExternalEnvFile.setText(_translate("Env", "Browse", None))
        self.pbSaveToNewEnvFile.setToolTip(_translate("Env", "<html><head/><body><p>You can use this button to save the current environment to a new external file. (This is only required to create a new external file - if you are already using an external file, changes to the environment are automatically saved there.)</p></body></html>", None))
        self.pbSaveToNewEnvFile.setText(_translate("Env", "Save to new", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("Env", "Your environment", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab2), _translate("Env", "Example environment", None))

