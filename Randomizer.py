## Randomization Algorithm
##
## TODO: work out what weights should be (poss make sliders)
## TODO: use tags to limit track selection

import ConfigParser
from Errors import *
from Time import roughAge
from Util import plural, MultiCompletion
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
                 defaultWeight="(score ** 2) * (time ** 2)"):
        self._safeOperations = ["", "(", ")", "score", "time", "**", "*", "/",
                                "+", "-"]
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
                if self._isSafeAlgorithmPart(part):
                    continue
                self._logger.error("Unsafe weight algorithm imported: \'"\
                                   +rawWeightAlgorithm+"\'.")
                raise UnsafeInputError
        self._setWeightAlgorithm(rawWeightAlgorithm)
        try:
            self._scoreThreshold = self._configParser.getint("Randomizer",
                                                             "scoreThreshold")
        except ConfigParser.NoOptionError:
            self._scoreThreshold = self._defaultScoreThreshold
            
    def _isSafeAlgorithmPart(self, part):
        if part not in self._safeOperations:
            try:
                float(part)
                return True
            except ValueError:
                pass
            newPart = ""
            for index in range(len(part)):
                newPart += part[index]
                if newPart not in self._safeOperations:
                    try:
                        float(newPart)
                        newPart = ""
                    except ValueError:
                        pass
                    continue
                newPart = ""
            if newPart != "":
                return False
        return True
    
    def _completeTracks(self, completion):
        completion(self._tracks)
        
    def _addTrackToListCallback(self, track, weight):
        track.setWeight(weight)
        self._tracks.append(track)

    def _chooseTracksCompletion(self, trackIDs, completion):
        self._tracks = [] # FIXME: possibly clears list before posting it
        for [trackID, weight] in trackIDs:
            try:
                self._trackFactory.getTrackFromID(
                    self._db, trackID,
                    lambda track: self._addTrackToListCallback(track, weight))
            except NoTrackError: # FIXME: probably doesn't work
                self._db.setHistorical(True, trackID)
        self._db.complete(lambda result: self._completeTracks(completion))

    def chooseTracks(self, number, exclude, completion, tags=None):
        self._logger.debug("Selecting "+str(number)+" track"+plural(number)+".")
        mycompletion = lambda trackIDs: self._chooseTracksCompletion(trackIDs,
                                                                     completion)
        self._chooseTrackIDs(number, exclude, mycompletion, tags)

    def _chooseTrackIDsCompletion(self, number, trackWeightList, totalWeight,
                                  completion):
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
        completion(trackIDs)
    
    ## will throw exception if database is empty?
    def _chooseTrackIDs(self, number, exclude, completion, tags=None):
##        print time.time()
        mycompletion = lambda trackWeightList, totalWeight: \
                            self._chooseTrackIDsCompletion(number,
                                                           trackWeightList,
                                                           totalWeight,
                                                           completion)
        self._createLists(exclude, mycompletion, tags)
        
    def _getTimeAndScoreCompletion(self, trackID, time, score, oldest):
        if time == None:
            time = oldest
        if score < self._scoreThreshold + 11:
            score = 0
        weight = self.getWeight(score, time)
        self._trackWeightList.append([trackID, weight])
        self._totalWeight += weight

    def _createListsCompletion(self, exclude, oldest, rawTrackIDList,
                               completion):
        if rawTrackIDList == []:
            self._logger.error("No tracks in database.")
            raise EmptyDatabaseError
        self._logger.info("Oldest is "+str(oldest)+" seconds old ("\
                          +roughAge(oldest)+" old).")
        self._trackWeightList = []
        self._totalWeight = 0
        for (trackID, ) in rawTrackIDList:
            # |exclude| is probably the list of currently enqueued but
            # unplayed tracks.
            if trackID in exclude:
                continue
            multicompletion = MultiCompletion(
                2, lambda time, score: self._getTimeAndScoreCompletion(trackID,
                                                                       time,
                                                                       score,
                                                                       oldest))
            self._db.getSecondsSinceLastPlayedFromID(
                trackID, lambda time: multicompletion.put(0, time))
            self._db.getScoreValueFromID(
                trackID, lambda score: multicompletion.put(1, score+11))
            ## creates a positive score
#            if time == None:
#                time = oldest
#            if score < self._scoreThreshold + 11:
#                score = 0
#            weight = self.getWeight(score, time)
#            trackWeightList.append([trackID, weight])
#            totalWeight += weight
        self._db.complete(lambda: completion(self._trackWeightList,
                                                  self._totalWeight))
        
    def _createLists(self, exclude, completion, tags=None):
        self._logger.debug("Creating weighted list of tracks.")
        mycompletion = MultiCompletion(2,
            lambda rawTrackIDList, oldest: \
            self._createListsCompletion(exclude, oldest, rawTrackIDList,
                                        completion))
        trackListCompletion = lambda rawTrackIDList: \
                              mycompletion.put(0, rawTrackIDList)
        oldestCompletion = lambda oldest: mycompletion.put(1, oldest)
        
        self._db.getOldestLastPlayed(oldestCompletion)
        if tags == None:
            self._db.getAllTrackIDs(trackListCompletion)
        else:
            self._db.getAllTrackIDsWithTags(trackListCompletion, tags)
        
    def _setWeightAlgorithm(self, rawWeightAlgorithm):
        self._weightAlgorithm = eval("lambda score, time: "+rawWeightAlgorithm)

    def getWeight(self, score, time):
##        weight = time ** (score/50.)
##        weight = score**2 * time**2
##        weight = score * time
        return self._weightAlgorithm(score, time)

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
        weightAlgorithmSizer.Add(weightLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM
                                 |wx.ALIGN_CENTER_VERTICAL, 3)

        self._weightControl = wx.TextCtrl(
            self, -1, self._settings["weightAlgorithm"], size=(-1, -1))
        # TODO(ben): make this expand to fill the space (doesn't on at
        # least FreeBSD)
        weightAlgorithmSizer.Add(self._weightControl, 1)

        self._weightSizer.Add(weightAlgorithmSizer, 0)

        weightHelpBox = wx.StaticBox(self, -1,
                                     "Acceptable Input:")
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
        self._configParser.set("Randomizer", name, str(value))

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
