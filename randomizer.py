# Randomization Algorithm
#
# TODO: work out what weights should be (poss make sliders)
# TODO: use tags to limit track selection
# TODO: make oldest not include tracks below threshold

import ConfigParser
import random

import errors
import util

wx = util.wx


class Randomizer:
    """
       Tracks with a |score| >= |scoreThreshold| get played. By default, -10s
       are not played.
    """
    
    def __init__(self, db, trackFactory, loggerFactory, configParser,
                 defaultDefaultScore, defaultScoreThreshold=-9,
                 defaultWeight="(score ** 2) * (time ** 2)"):
        self._safeOperations = ["", "(", ")", "score", "time", "**", "*", "/",
                                "+", "-"]
        self._db = db
        self._trackFactory = trackFactory
        self._logger = loggerFactory.getLogger("NQr.Randomizer", "debug")
        self._configParser = configParser
        self._defaultScoreThreshold = defaultScoreThreshold
        self._defaultWeight = defaultWeight
        self._defaultDefaultScore = defaultDefaultScore
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
                self._logger.error("Unsafe weight algorithm imported: \'" +
                                   rawWeightAlgorithm + "\'.")
                raise errors.UnsafeInputError
        self._setWeightAlgorithm(rawWeightAlgorithm)
        try:
            self._scoreThreshold = self._configParser.getint("Randomizer",
                                                             "scoreThreshold")
        except ConfigParser.NoOptionError:
            self._scoreThreshold = self._defaultScoreThreshold
        try:
            self._configParser.add_section("Database")
        except ConfigParser.DuplicateSectionError:
            pass
        try:
            self._defaultScore = self._configParser.getint("Database",
                                                           "defaultScore")
        except ConfigParser.NoOptionError:
            self._defaultScore = self._defaultDefaultScore
            
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

    def chooseTracks(self, number, exclude, completion, traceCallback=None,
                     tags=None):
        self._logger.debug("Selecting " + str(number) + " track" +
                           util.plural(number) + ".")
        mycompletion = (lambda thisCallback, trackIDs, completion=completion:
                            self._chooseTracksCompletion(trackIDs, completion,
                                                         thisCallback))
        self._chooseTrackIDs(number, exclude, mycompletion, traceCallback, tags)

    def _chooseTracksCompletion(self, trackIDs, completion, traceCallback):
        self._tracks = [] # FIXME: Possibly clears list before posting it.
        for [trackID, weight] in trackIDs:
            errcompletion = util.ErrorCompletion(
                errors.NoTrackError,
                lambda thisCallback, trackID=trackID:
                    self._db.setHistorical(True, trackID,
                                           traceCallback=thisCallback),
                traceCallback)
            self._trackFactory.getTrackFromID(
                self._db, trackID,
                lambda thisCallback, track, weight=weight:
                    self._addTrackToListCallback(track, weight),
                errcompletion=errcompletion, traceCallback=traceCallback)
        self._db.complete(
            lambda thisCallback, completion=completion:
                completion(thisCallback, self._tracks),
            traceCallback=traceCallback)
        
    def _addTrackToListCallback(self, track, weight):
        track.setWeight(weight)
        self._tracks.append(track)
    
    # FIXME: Will throw exception if database is empty?
    def _chooseTrackIDs(self, number, exclude, completion, traceCallback,
                        tags=None):
        mycompletion = (lambda thisCallback, trackWeightList, totalWeight,
                        number=number, completion=completion:
                            self._chooseTrackIDsCompletion(number,
                                                           trackWeightList,
                                                           totalWeight,
                                                           completion,
                                                           thisCallback))
        self._createLists(exclude, mycompletion, traceCallback, tags)

    def _chooseTrackIDsCompletion(self, number, trackWeightList, totalWeight,
                                  completion, traceCallback):
        trackIDs = []
        for n in range(number):
            trackID, weight = self._selectTrackID(trackWeightList, totalWeight,
                                                  trackIDs)
            norm = float(weight) * len(trackWeightList) / totalWeight
            self._logger.debug("Selected " + str(trackID) + " with weight: " +
                               str(weight) + " of a total: " +
                               str(totalWeight) + " (norm " + str(norm) + ").")
            trackIDs.append([trackID, norm])
        completion(traceCallback, trackIDs)
        
    def _selectTrackID(self, trackWeightList, totalWeight, trackIDs):
        selector = random.random() * totalWeight
        for [trackID, weight] in trackWeightList:
            selector -= weight
            if selector < 0:
                if trackID in trackIDs:
                    return self._selectTrackID(trackWeightList, totalWeight,
                                               trackIDs)
                return trackID, weight
        
        
    def _createLists(self, exclude, completion, traceCallback, tags=None):
        multicompletion = util.MultiCompletion(
            3,
            lambda oldest, list, thisCallback, exclude=exclude,
            completion=completion:
                self._createListsCompletion(exclude, oldest, list, completion,
                                            thisCallback),
            traceCallback)
        self._db.getOldestLastPlayed(
            lambda thisCallback, oldest, multicompletion=multicompletion:
                multicompletion(0, oldest),
            traceCallback=traceCallback)
        multicompletion(2, traceCallback)
        if tags is None:
            self._db.getRandomizerList(
                lambda thisCallback, list, multicompletion=multicompletion:
                    multicompletion(1, list),
                traceCallback=traceCallback)
        else:
            # FIXME: Support tags.
#            self._db.getRandomizerListFromTags(
#                tags,
#                lambda list, multicompletion=multicompletion: multicompletion(
#                    1, list))
            pass

    # FIXME: EmptyDatabaseError needs to be caught.
    def _createListsCompletion(self, exclude, oldest, list, completion,
                               traceCallback):
        self._logger.debug("Creating weighted list of tracks.")
        if not list:
            self._logger.error("No tracks in database.")
            raise errors.EmptyDatabaseError(trace=util.getTrace(traceCallback))
        self._logger.debug("Oldest track was played " + str(oldest) +
                           " seconds ago (" + util.roughAge(oldest) + " ago).")
        trackWeightList = []
        totalWeight = 0
        for (trackID, time, score, unscored) in list:
            # |exclude| is probably the list of currently enqueued but
            # unplayed tracks.
            if trackID in exclude:
                continue
            if time is None:
                time = oldest
            if unscored:
                score = self._defaultScore
            if score < self._scoreThreshold:
                score = 0
            else:
                score += 11 # creates a positive score
            weight = self.getWeight(score, time)
            trackWeightList.append([trackID, weight])
            totalWeight += weight
        completion(traceCallback, trackWeightList, totalWeight)
        
    def _setWeightAlgorithm(self, rawWeightAlgorithm):
        self._weightAlgorithm = eval("lambda score, time: " +
                                     rawWeightAlgorithm)

    def getWeight(self, score, time):
##        weight = time ** (score/50.)
##        weight = score**2 * time**2
##        weight = score * time
        return self._weightAlgorithm(score, time)


class PrefsPage(util.BasePrefsPage):
    
    def __init__(self, parent, configParser, logger,
                 defaultScoreThreshold, defaultWeight):
        util.BasePrefsPage.__init__(self, parent, configParser, logger,
                                    "Randomizer", defaultScoreThreshold,
                                    defaultWeight)
        
        self._initCreateWeightSizer()
        self._initCreateThresholdSizer()

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._weightSizer, 0)
        mainSizer.Add(self._thresholdSizer, 0)

        self.SetSizer(mainSizer)

    def _initCreateWeightSizer(self):
        self._weightSizer = wx.BoxSizer(wx.VERTICAL)

        weightAlgorithmSizer = wx.BoxSizer(wx.HORIZONTAL)

        weightLabel = wx.StaticText(self, wx.NewId(), "Weight Algorithm: ")
        weightAlgorithmSizer.Add(weightLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM
                                 |wx.ALIGN_CENTER_VERTICAL, 3)

        self._weightControl = wx.TextCtrl(
            self, wx.NewId(), self._settings["weightAlgorithm"], size=(-1, -1))
        # TODO(ben): Make this expand to fill the space (doesn't on at
        #            least FreeBSD).
        weightAlgorithmSizer.Add(self._weightControl, 1)

        self._weightSizer.Add(weightAlgorithmSizer, 0)

        weightHelpBox = wx.StaticBox(self, wx.NewId(),
                                     "Acceptable Input:")
        weightHelpSizer = wx.StaticBoxSizer(weightHelpBox, wx.HORIZONTAL)
        weightHelpFont = wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL)

        weightHelpVariablesBox = wx.StaticBox(self, wx.NewId(), "Variables:")
        weightHelpVariablesSizer = wx.StaticBoxSizer(weightHelpVariablesBox)

        weightHelpVariablesText = ("score = track score + 11        \n" +
                                   "time  = seconds since last play ")
        weightHelpVariables = wx.StaticText(self, wx.NewId(),
                                            weightHelpVariablesText)
        weightHelpVariables.SetFont(weightHelpFont)
        weightHelpVariablesSizer.Add(weightHelpVariables, 0)
        weightHelpSizer.Add(weightHelpVariablesSizer, 0, wx.RIGHT, 1)

        weightHelpOperatorsBox = wx.StaticBox(self, wx.NewId(), "Operators:")
        weightHelpOperatorsSizer = wx.StaticBoxSizer(weightHelpOperatorsBox)

        weightHelpOperatorsText = ("** = to the power of \n" +
                                   "*  = multiplied by   \n" +
                                   "/  = divided by      \n" +
                                   "+  = plus            \n" +
                                   "-  = minus           ")
        weightHelpOperators = wx.StaticText(self, wx.NewId(),
                                            weightHelpOperatorsText)
        weightHelpOperators.SetFont(weightHelpFont)
        weightHelpOperatorsSizer.Add(weightHelpOperators, 0)
        weightHelpSizer.Add(weightHelpOperatorsSizer, 0)

        self._weightSizer.Add(weightHelpSizer, 1)

        self.Bind(wx.EVT_TEXT, self._onWeightChange, self._weightControl)

    def _initCreateThresholdSizer(self):
        self._thresholdSizer = wx.BoxSizer(wx.HORIZONTAL)

        thresholdLabel = wx.StaticText(self, wx.NewId(), "Minimum Play Score: ")
        self._thresholdSizer.Add(thresholdLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)

        self._thresholdControl = wx.TextCtrl(
            self, wx.NewId(), str(self._settings["scoreThreshold"]),
            size=(25,-1))
        self._thresholdSizer.Add(self._thresholdControl, 0)

        self.Bind(wx.EVT_TEXT, self._onThresholdChange,
                  self._thresholdControl)

    def _onWeightChange(self, e):
        weight = self._weightControl.GetLineText(0)
        if weight != "":
            self._settings["weightAlgorithm"] = weight

    def _onThresholdChange(self, e):
        if util.validateNumeric(self._thresholdControl):
            threshold = self._thresholdControl.GetLineText(0)
            if threshold != "":
                self._settings["scoreThreshold"] = int(threshold)

    def _setDefaults(self, defaultScoreThreshold, defaultWeight):
        self._defaultScoreThreshold = defaultScoreThreshold
        self._defaultWeight = defaultWeight

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
