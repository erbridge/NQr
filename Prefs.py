import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

class PrefsFactory:
    def __init__(self, filename, loggerFactory, modules):
        self._logger = loggerFactory.getLogger("NQr.Prefs", "debug")
        self._modules = modules
        self._filename = filename

    def getPrefsWindow(self, parent):
        return PrefsWindow(parent, self._logger, self._modules)

class PrefsWindow(wx.Frame):
    def __init__(self, parent, logger, modules):
        self._logger = logger

        wx.Frame.__init__(self, parent, title="Preferences",
                          style=wx.CAPTION|wx.FRAME_NO_TASKBAR|
                          wx.FRAME_FLOAT_ON_PARENT)
        panel = wx.Panel(self)
        self._prefs = wx.Notebook(panel, size=(400,400))

        self._pages = {}
        for module in modules:
            (prefsPage, prefsPageName) = module.getPrefsPage(self._prefs)
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
        self.Close(True)

    def addPage(self, page, pageName, position=None):
        self._logger.debug("Adding preference page.")
        if position == None:
            position = len(self._pages)
        self._pages[pageName] = page
        self._prefs.InsertPage(position, page, pageName)

    def getNotebook(self):
        return self._prefs