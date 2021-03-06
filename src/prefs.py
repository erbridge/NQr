# Preference window
#
# TODO: Create validation rules for all text controls.

import os

import util

wx = util.wx


class PrefsFactory:

    def __init__(self, filename, loggerFactory, modules, configParser):
        self._logger = loggerFactory.getLogger("NQr.Prefs", "debug")
        self._modules = modules
        self._filename = filename
        self._configParser = configParser

    def getPrefsWindow(self, parent):
        return PrefsWindow(parent, self._logger, self._modules,
                           self._configParser, self._filename)

    def restoreDefaults(self, filename=None):
        if filename is None:
            filename = self._filename + ".backup"
        os.rename(self._filename, filename)

    def writePrefs(self):
        with open(self._filename, 'w') as file:
            self._configParser.write(file)


class PrefsWindow(wx.Frame):

    def __init__(self, parent, logger, modules, configParser, filename):
        self._logger = logger
        self._gui = parent
        self._modules = modules
        if self._modules[0] != parent:
            self._modules.insert(0, parent)
        self._configParser = configParser
        self._filename = filename

        wx.Frame.__init__(self, parent, title="Preferences",
                          style=wx.CAPTION | wx.FRAME_NO_TASKBAR |
                          wx.FRAME_FLOAT_ON_PARENT)
        panel = wx.Panel(self)
        self._prefs = wx.Notebook(panel, size=(-1, -1))

        self._pages = {}
        for module in self._modules:
            (prefsPage, prefsPageName) = module.getPrefsPage(self._prefs,
                                                             self._logger)
            self.addPage(prefsPage, prefsPageName)

        saveButton = wx.Button(panel, wx.ID_SAVE)
        cancelButton = wx.Button(panel, wx.ID_CANCEL)

        self.Bind(wx.EVT_BUTTON, self._onSave, saveButton)
        self.Bind(wx.EVT_BUTTON, self._onCancel, cancelButton)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        # FIXME: Doesn't align right...
        buttonSizer.Add(saveButton, 0, wx.ALIGN_RIGHT)
        buttonSizer.Add(cancelButton, 0, wx.ALIGN_RIGHT)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._prefs, 1, wx.EXPAND)
        mainSizer.Add(buttonSizer, 0)
        panel.SetSizerAndFit(mainSizer)
        panel.SetAutoLayout(True)

    def _onSave(self, e):
        self.savePrefs()
        self._onCancel(e)

    def _onCancel(self, e):
        self._logger.debug("Closing preferences window.")
        self.Close(True)

    def addPage(self, page, pageName, position=None):
        self._logger.debug("Adding preference page.")
        if position is None:
            position = len(self._pages)
        self._pages[pageName] = page
        self._prefs.InsertPage(position, page, pageName)

    def savePrefs(self):
        self._logger.info("Saving preferences.")
        for page in self._pages.values():
            page.savePrefs()
        with open(self._filename, 'w') as file:
            self._configParser.write(file)
        for module in self._modules:
            module.loadSettings()
