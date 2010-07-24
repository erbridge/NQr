## Randomization Algorithm
## TODO: work out time factor if track has never been played: poss use time
##       since added to database?

from Database import Database
import random

class Randomizer:
    def __init__(self, db=Database()):
        self.db = db

    def chooseTrackID(self):
        (trackIDList, weightList, totalWeight) = self.createLists()
        selector = random.random() * totalWeight
        for weight, trackID in reversed(sorted(zip(weightList, trackIDList))):
            selector -= weight
            if selector < 0:
                return trackID

    def createLists(self):
        rawTrackIDList = self.db.getAllTrackIDs()
        if rawTrackIDList == None:
            print "The database is empty."
            return None
        trackIDList = []
        for (trackID, ) in rawTrackIDList:
            trackIDList.append(trackID)
        weightList = []
        totalWeight = 0
        for trackID in trackIDList:
            time = self.db.getSecondsSinceLastPlayedFromID(trackID)
            score = self.db.getScoreValueFromID(trackID) + 10 ## creates a positive score
            if time == None:
                time = 5 * (len(trackIDList) + 1)
            weight = self.setWeight(score, time)
            weightList.append(weight)
            totalWeight += weight
        return trackIDList, weightList, totalWeight

    def setWeight(self, score, time):
        weight = score * time
        return weight
