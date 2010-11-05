## Randomization Algorithm
##
## TODO: work out what weights should be (poss make sliders)
## TODO: use tags to limit track selection

import ConfigParser
from Errors import *
from Time import roughAge
from Util import plural
import random
import time

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

## tracks with a score >= scoreThreshold get played
## by default, -10s are not played
class Randomizer:
    def __init__(self, db, trackFactory, loggerFactory, configParser,
                 defaultScoreThreshold=-9,
                 defaultWeight="score ** 2 * time ** 2"):
        self._safeOperations = ["", "score", "time", "**", "*", "/", "+", "-"]
        self._db = db
        self._trackFactory = trackFactory
        self._logger = loggerFactory.getLogger("NQr.Randomizer", "debug")
        self._configParser = configParser
        self._defaultScoreThreshold = defaultScoreThreshold
        self._defaultWeight = defaultWeight
        self.loadSettings()

    def getPrefsPage(self, parent, logger):
        return PrefsPage(
            parent, self._configParser, logger, self._defaultScoreThreshold,
            self._defaultWeight), "Randomizer"

    def loadSettings(self):
        try:
            self._configParser.add_section("Randomizer")
        except ConfigParser.DuplicateSectionError:
            pass
        try:
            rawWeightAlgorithm = self._configParser.get("Randomizer", 
                                                        "weightAlgorithm")
        except ConfigParser.NoOptionError:
            rawWeightAlgorithm = self._defaultWeight
        for part in rawWeightAlgorithm.split(" "):
            if part not in self._safeOperations:
                try:
                    float(part)
                    continue
                except ValueError:
                    pass
                self._logger.error("Unsafe weight algorithm imported: \'"\
                                   +rawWeightAlgorithm+"\'.")
                raise UnsafeInputError
        self._weightAlgorithm = rawWeightAlgorithm
        try:
            self._scoreThreshold = self._configParser.getint("Randomizer",
                                                             "scoreThreshold")
        except ConfigParser.NoOptionError:
            self._scoreThreshold = self._defaultScoreThreshold

    def chooseTrack(self):
        track = self.chooseTracks(1)[0]
        return track

    def chooseTracks(self, number, exclude):
        self._logger.debug("Selecting "+str(number)+" track"+plural(number)+".")
        trackIDs = self._chooseTrackIDs(number, exclude)
        tracks = []
        for [trackID, weight] in trackIDs:
            try:
                track = self._trackFactory.getTrackFromID(self._db, trackID)
                track.setWeight(weight)
                tracks.append(track)
            except NoTrackError:
                self._db.setHistorical(True, track)
        return tracks

## will throw exception if database is empty?
    def _chooseTrackIDs(self, number, exclude):
##        print time.time()
        (trackWeightList, totalWeight) = self.createLists(exclude)
        trackIDs = []
        for n in range(number):
##            poss should be here so tracks enqueued have times reset each time.
##            would be much slower though.
##            (trackWeightList, totalWeight) = self.createLists()
            selector = random.random() * totalWeight
            for [trackID, weight] in trackWeightList:
                selector -= weight
                if selector < 0:
                    norm = float(weight) * len(trackWeightList) / totalWeight
                    self._logger.info("Selected "+str(trackID)+" with weight: "\
                                      +str(weight)+" of a total: "\
                                      +str(totalWeight)+" (norm "+str(norm)\
                                      +").")
                    trackIDs.append([trackID, norm])
                    break
        return trackIDs

    def createLists(self, exclude):
        self._logger.debug("Creating weighted list of tracks.")
        oldest = self._db.getOldestLastPlayed()
        self._logger.info("Oldest is "+str(oldest)+" seconds old ("\
                          +roughAge(oldest)+" old).")
        rawTrackIDList = self._db.getAllTrackIDs()
        if rawTrackIDList == []:
            self._logger.error("No tracks in database.")
            raise EmptyDatabaseError
        trackWeightList = []
        totalWeight = 0
        for (trackID, ) in rawTrackIDList:
            # |exclude| is probably the list of currently enqueued but
            # unplayed tracks.
            if trackID in exclude:
                continue
            time = self._db.getSecondsSinceLastPlayedFromID(trackID)
            score = self._db.getScoreValueFromID(trackID) + 11
            ## creates a positive score
            if time == None:
                time = oldest
            if score < self._scoreThreshold + 11:
                score = 0
            weight = self.getWeight(score, time)
            trackWeightList.append([trackID, weight])
            totalWeight += weight
        return trackWeightList, totalWeight

    def getWeight(self, score, time):
        weight = eval(self._weightAlgorithm) # slow?
##        weight = time ** (score/50.)
##        weight = score**2 * time**2
##        weight = score * time
        return weight

class PrefsPage(wx.Panel):
    def __init__(self, parent, configParser, logger, defaultScoreThreshold,
                 defaultWeight):
        wx.Panel.__init__(self, parent)
        self._logger = logger
        self._defaultScoreThreshold = defaultScoreThreshold
        self._defaultWeight = defaultWeight
        self._settings = {}
        self._configParser = configParser
        try:
            self._configParser.add_section("Randomizer")
        except ConfigParser.DuplicateSectionError:
            pass
        self._loadSettings()
        self._initCreateWeightSizer()
        self._initCreateThresholdSizer()

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._weightSizer, 0)
        mainSizer.Add(self._thresholdSizer, 0)

        self.SetSizer(mainSizer)

    def _initCreateWeightSizer(self):
        self._weightSizer = wx.BoxSizer(wx.VERTICAL)

        weightAlgorithmSizer = wx.BoxSizer(wx.HORIZONTAL)

        weightLabel = wx.StaticText(self, -1, "Weight Algorithm: ")
        weightAlgorithmSizer.Add(weightLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)

        self._weightControl = wx.TextCtrl(
            self, -1, self._settings["weightAlgorithm"], size=(-1,-1))
        weightAlgorithmSizer.Add(self._weightControl, 1)

        self._weightSizer.Add(weightAlgorithmSizer, 0)

        weightHelpBox = wx.StaticBox(self, -1,
                                     "Acceptable Input (separate with spaces):")
        weightHelpSizer = wx.StaticBoxSizer(weightHelpBox, wx.HORIZONTAL)
        weightHelpFont = wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL)

        weightHelpVariablesBox = wx.StaticBox(self, -1, "Variables:")
        weightHelpVariablesSizer = wx.StaticBoxSizer(weightHelpVariablesBox)

        weightHelpVariablesText = "score = track score + 11        \n"\
            +"time  = seconds since last play "
        weightHelpVariables = wx.StaticText(self, -1, weightHelpVariablesText)
        weightHelpVariables.SetFont(weightHelpFont)
        weightHelpVariablesSizer.Add(weightHelpVariables, 0)
        weightHelpSizer.Add(weightHelpVariablesSizer, 0, wx.RIGHT, 1)

        weightHelpOperatorsBox = wx.StaticBox(self, -1, "Operators:")
        weightHelpOperatorsSizer = wx.StaticBoxSizer(weightHelpOperatorsBox)

        weightHelpOperatorsText = "** = to the power of \n"\
            +"*  = multiplied by   \n"\
            +"/  = divided by      \n"\
            +"+  = plus            \n"\
            +"-  = minus           "
        weightHelpOperators = wx.StaticText(self, -1, weightHelpOperatorsText)
        weightHelpOperators.SetFont(weightHelpFont)
        weightHelpOperatorsSizer.Add(weightHelpOperators, 0)
        weightHelpSizer.Add(weightHelpOperatorsSizer, 0)

        self._weightSizer.Add(weightHelpSizer, 1)

        self.Bind(wx.EVT_TEXT, self._onWeightChange, self._weightControl)

    def _initCreateThresholdSizer(self):
        self._thresholdSizer = wx.BoxSizer(wx.HORIZONTAL)

        thresholdLabel = wx.StaticText(self, -1, "Minimum Play Score: ")
        self._thresholdSizer.Add(thresholdLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)

        self._thresholdControl = wx.TextCtrl(
            self, -1, str(self._settings["scoreThreshold"]), size=(25,-1))
        self._thresholdSizer.Add(self._thresholdControl, 0)

        self.Bind(wx.EVT_TEXT, self._onThresholdChange,
                  self._thresholdControl)

    def _onWeightChange(self, e):
        weight = self._weightControl.GetLineText(0)
        if weight != "":
            self._settings["weightAlgorithm"] = weight

    def _onThresholdChange(self, e):
        threshold = self._thresholdControl.GetLineText(0)
        if threshold != "":
            self._settings["scoreThreshold"] = int(threshold)

    def savePrefs(self):
        self._logger.debug("Saving randomizer preferences.")
        for (name, value) in self._settings.items():
            self.setSetting(name, value)

    def setSetting(self, name, value):
        self._configParser.set("Randomizer", name, value)

    def _loadSettings(self):
        try:
            weight = self._configParser.get("Randomizer", "weightAlgorithm")
            self._settings["weightAlgorithm"] = weight
        except ConfigParser.NoOptionError:
            self._settings["weightAlgorithm"] = self._defaultWeight
        try:
            threshold = self._configParser.getint("Randomizer",
                                                  "scoreThreshold")
            self._settings["scoreThreshold"] = threshold
        except ConfigParser.NoOptionError:
            self._settings["scoreThreshold"] = self._defaultScoreThreshold
