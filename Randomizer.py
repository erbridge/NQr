## Randomization Algorithm
## TODO: work out time factor if track has never been played: poss use time
##       since added to database?
## TODO: work out what weights should be (poss make sliders)
## TODO: getWeights from a text option (convert into python code) allowing
##       length of list etc.

##from Database import Database
import random
import time

## tracks with a score >= scoreThreshold get played
## by default, -10s are not played
class Randomizer:
    def __init__(self, db, trackFactory, scoreThreshold=-9):
        self.db = db
        self.trackFactory = trackFactory
        self.scoreThreshold = scoreThreshold

## will throw exception if databse is empty?
    def chooseTrackID(self):
##        print time.time()
        (trackWeightList, totalWeight) = self.createLists()
        selector = random.random() * totalWeight
        for [trackID, weight] in trackWeightList:
            selector -= weight
            if selector < 0:
##                print time.time()
                return trackID

    def chooseTrack(self):
        trackID = self.chooseTrackID()
        track = self.trackFactory.getTrackFromID(self.db, trackID)
        return track

    def createLists(self):
        rawTrackIDList = self.db.getAllTrackIDs()
        if rawTrackIDList == None:
            print "The database is empty."
            return None
        trackWeightList = []
        totalWeight = 0
        for (trackID, ) in rawTrackIDList:
            time = self.db.getSecondsSinceLastPlayedFromID(trackID)
            score = self.db.getScoreValueFromID(trackID) + 11 ## creates a positive score
            if time == None:
                time = 5 * (len(trackWeightList) + 1)
            if score < self.scoreThreshold + 11:
                score = 0
            weight = self.getWeight(score, time)
            trackWeightList.append([trackID, weight])
            totalWeight += weight
        return trackWeightList, totalWeight

#### poss "reverse(sorted(" makes operation slower, not faster
##    def chooseTrackID(self):
####        print time.time()
##        (trackIDList, weightList) = self.createLists()
##        selector = random.random() * sum(weightList)
##        for weight, trackID in reversed(sorted(zip(weightList, trackIDList))):
##            selector -= weight
##            if selector < 0:
####                print time.time()
##                return trackID
##
##    def createLists(self):
##        rawTrackIDList = self.db.getAllTrackIDs()
##        if rawTrackIDList == None:
##            print "The database is empty."
##            return None
##        trackIDList = []
##        for (trackID, ) in rawTrackIDList:
##            trackIDList.append(trackID)
##        weightList = []
####        totalWeight = 0
##        for trackID in trackIDList:
##            time = self.db.getSecondsSinceLastPlayedFromID(trackID)
##            score = self.db.getScoreValueFromID(trackID) + 11 ## creates a positive score
##            if time == None:
##                time = 5 * (len(trackIDList) + 1)
##            if score < self.scoreThreshold + 11:
##                score = 0
##            weight = self.getWeight(score, time)
##            weightList.append(weight)
####            totalWeight += weight
##        return trackIDList, weightList##, totalWeight

    def getWeight(self, score, time):
        weight = time^(score/50)
##        weight = score * time
        return weight

##d = Database(None)
##r = Randomizer(d, None)
##r.chooseTrackID()
