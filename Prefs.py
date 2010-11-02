## Preference window
##
## TODO: create validation rules for text controls

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

class PrefsFactory:
    def __init__(self, filename, loggerFactory, modules, configParser):
        self._logger = loggerFactory.getLogger("NQr.Prefs", "debug")
        self._modules = modules
        self._filename = filename
        self._configParser = configParser

    def getPrefsWindow(self, parent):
        return PrefsWindow(parent, self._logger, self._modules,
                           self._configParser, self._filename)

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
                          style=wx.CAPTION|wx.FRAME_NO_TASKBAR|
                          wx.FRAME_FLOAT_ON_PARENT)
        panel = wx.Panel(self)
        self._prefs = wx.Notebook(panel, size=(-1,-1))

        self._pages = {}
        for module in self._modules:
            (prefsPage, prefsPageName) = module.getPrefsPage(self._prefs,
                                                             self._logger)
            self.addPage(prefsPage, prefsPageName)

        closeButton = wx.Button(panel, wx.ID_CLOSE)

        self.Bind(wx.EVT_BUTTON, self._onClose, closeButton)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        ## FIXME: doesn't align right...
        buttonSizer.Add(closeButton, 0, wx.ALIGN_RIGHT)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._prefs, 1, wx.EXPAND)
        mainSizer.Add(buttonSizer, 0)
        panel.SetSizerAndFit(mainSizer)
        panel.SetAutoLayout(True)

    def _onClose(self, e):
        self._logger.debug("Closing preferences window.")
        self.savePrefs()
        self.Close(True)

    def addPage(self, page, pageName, position=None):
        self._logger.debug("Adding preference page.")
        if position == None:
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
