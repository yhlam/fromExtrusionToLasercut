import random

import bisect
import rhinoscriptsyntax as rs
import scriptcontext


class ObjBox:
    def __init__(self, id, pt0, vecHor, vecVer):
        self.id = id
        self.pt0 = pt0
        self.vecHor = vecHor
        self.vecVer = vecVer
        self.width = rs.VectorLength(vecHor)
        self.height = rs.VectorLength(vecVer)


def getHeight(objBox):
    return objBox.height


def getWidth(objBox):
    return objBox.width


def addText(objs, textHeight, textLayer):
    for num, obj in enumerate(objs):
        box = rs.BoundingBox(obj)
        center = rs.VectorScale(rs.VectorAdd(box[0], box[2]), 0.5)
        textCenterVector = rs.VectorAdd(rs.VectorScale([1, 0, 0], textHeight / 3), rs.VectorScale([0, 1, 0], textHeight / 2))
        textBase = rs.VectorSubtract(center, textCenterVector)

        text = rs.AddText(str(num), textBase, height=textHeight)
        rs.ObjectLayer(text, layer=textLayer)


def rotatePeriHalf(obj, center, angle):
    rs.EnableRedraw(False)
    objRotated = rs.RotateObjects(obj, center, angle)
    box = rs.BoundingBox(objRotated)
    pt0 = box[0]
    pt1 = box[1]
    pt2 = box[2]
    periHalf = rs.Distance(pt0, pt1) + rs.Distance(pt1, pt2)

    rs.RotateObjects(objRotated, center, angle * (-1))

    return periHalf


def rotateFinal(obj, center, angle):
    rs.EnableRedraw(False)
    objRotated = rs.CopyObjects(obj)
    rs.ObjectLayer(objRotated, layer=tempLayer)
    objRotated = rs.RotateObjects(objRotated, center, angle)
    box = rs.BoundingBox(objRotated)
    pt0 = box[0]
    pt1 = box[1]
    pt2 = box[2]

    distA = rs.Distance(pt0, pt1)
    distB = rs.Distance(pt1, pt2)

    if distB > distA:
        objRotated = rs.RotateObject(objRotated, center, 90)

    box = rs.BoundingBox(objRotated)
    pt0 = box[0]
    pt1 = box[1]
    pt3 = box[3]

    vecHor = rs.VectorSubtract(pt1, pt0)
    vecVer = rs.VectorSubtract(pt3, pt0)

    return [objRotated, pt0, vecHor, vecVer]


def rotateMinBoundingBox(obj):
    box = rs.BoundingBox(obj)
    pt0 = box[0]
    pt1 = box[1]
    pt2 = box[2]

    center = rs.VectorScale(rs.VectorAdd(pt1, pt2), 0.5)

    periHalf = rs.Distance(pt0, pt1) + rs.Distance(pt1, pt2)
    angle = 0

    for i in range(0, 90, 5):
        rotatedPeri = rotatePeriHalf(obj, center, i)
        if rotatedPeri < periHalf:
            periHalf = rotatedPeri
            angle = i

    return rotateFinal(obj, center, angle)


def slabMulti(id, index, lasercutLayer):
    rs.EnableRedraw(False)

    extru = rs.coercegeometry(id)

    pathStart = extru.PathStart
    pathEnd = extru.PathEnd

    start_curve = extru.Profile3d(0, 0)
    baseCrv = scriptcontext.doc.Objects.AddCurve(start_curve)
    rs.ObjectLayer(baseCrv, layer=lasercutLayer)

    dist = rs.Distance(pathStart, pathEnd)
    num = int(dist // 4000)

    box = rs.BoundingBox(id)
    vecCopyUni = rs.VectorSubtract(box[0], box[3])

    groupName = "group" + str(index)
#    rs.AddGroup(groupName)

    item = []

    text = rs.AddText(str(index), box[3], height=textHeight)
#    rs.AddObjectToGroup(text, groupName)
    item += [text]

    for i in range(num):
        vecCopy = rs.VectorScale(vecCopyUni, i)
        crvCopied = rs.CopyObject(baseCrv, vecCopy)
#        rs.AddObjectToGroup(crvCopied, groupName)
        item += [crvCopied]

    return item



###########################################################################################
###########################################################################################
###########################################################################################



objs = rs.GetObjects("Select all extrusion", rs.filter.extrusion)
textHeight = 10000
materialWidth = 300000
#   numGroup = 3
lasercutPt0 = rs.GetPoint("Select the pt0 for the lasercut")

# use a randomNum to make sure no just existing layer
randomNum = str(random.randrange(0, 100000, 1))

textLayer = "textIndex " + randomNum
rs.AddLayer(textLayer)

tempLayer = "temptemptemp " + randomNum
rs.AddLayer(tempLayer)

lasercutLayer = "lasercutLayer " + randomNum
rs.AddLayer(lasercutLayer)





# addText
# add text number to individual extrusion to indicate the number
addText(objs, textHeight, textLayer)


# individula rotate
# rotate each extrusion to fit a min lateral rectangle
objList = []
for item in objs:
    id, pt0, vecHor, vecVer = rotateMinBoundingBox(item)
    item = ObjBox(id, pt0, vecHor, vecVer)

    objList.append(item)



# slabMulti
# adding suitable amount of slabs for each extrusion, and rotate the slabs to a min lateral rectangle
slabHeightList = []
for i, item in enumerate(objList):

    slabGroup = slabMulti(item.id, i, lasercutLayer)
    box = rs.BoundingBox(slabGroup)
    pt0 = box[0]
    pt1 = box[1]
    pt3 = box[3]
    center = rs.VectorScale(rs.VectorAdd(pt1, pt3), 0.5)


    width = rs.VectorLength(rs.VectorSubtract(pt1, pt0))
    height = rs.VectorLength(rs.VectorSubtract(pt3, pt0))



    if width < height:
        slabGroup = rs.RotateObjects(slabGroup, center, 90)
        box = rs.BoundingBox(slabGroup)
        pt0 = box[0]
        pt1 = box[1]
        pt3 = box[3]


    #objBox obj
    slabGroup = ObjBox(slabGroup, pt0, rs.VectorSubtract(pt1, pt0), rs.VectorSubtract(pt3, pt0))


    slabHeightList.append(slabGroup)




slabHeightList = sorted(slabHeightList, key=getHeight, reverse=True)

print "slabHeightList"
for item in slabHeightList:
    print item, item.height


# dict{rowRemain} is a dict of {rowNum: remaining space}
rowRemain = {0: materialWidth}
# list[SortedRowRemainKeyList] is an ascending sorted list of [value of rowRemain]
SortedRowRemainValueList = [materialWidth]
# list[SortedRowRemainKeyList] is a sorted list of [key of rowRemain]
# --- corresponding to SortedRowRemainValueList
SortedRowRemainKeyList = [0]
# objBox(topRowHighestObj) is a float showing the height of the top row
topRowHighestObj = slabHeightList[0]

# dict[rowPt0] is a dict of {rowNum: pt0 of remaining space}  pt0 = [x, y, z]
rowPt0 = {0: lasercutPt0}

for objBox in slabHeightList:
    if objBox.width > materialWidth:
        #put it elsewhere
        pass
    elif objBox.width > SortedRowRemainValueList[len(SortedRowRemainValueList) - 1]:
        #find existing top row's starting pt0
        existingPt0 = [lasercutPt0[0], rowPt0[len(rowPt0) - 1][1], lasercutPt0[2]]
        #find the pt0 for placing this objBox
        newRowPt0 = rs.VectorAdd(existingPt0, topRowHighestObj.vecVer)
        #add a new row
        rowRemain[len(rowRemain)] = materialWidth
        #move the slabs to new row's pt0
        vecTran = rs.VectorSubtract(newRowPt0, objBox.pt0)
        rs.MoveObjects(objBox.id, vecTran)
        #change dict{rowRemain}
        rowRemain[len(rowRemain) - 1] -= objBox.width
        SortedRowRemainValueList = sorted(rowRemain.values())
        SortedRowRemainKeyList = sorted(rowRemain, key=rowRemain.__getitem__)
        #change dict{rowPt0}
        rowPt0[len(rowPt0)] = rs.VectorAdd(newRowPt0, objBox.vecHor)
        #change objBox(topRowHighestObj)
        topRowHighestObj = objBox
    else:
        # find its suitable position in dict{rowRemain}
        indexInSortedList = bisect.bisect_left(SortedRowRemainValueList, objBox.width)
        rowNum = SortedRowRemainKeyList[indexInSortedList]
        # move the slabs to that row according to dict{rowPt0}
        vecTran = rs.VectorSubtract(rowPt0[rowNum], objBox.pt0)
        rs.MoveObjects(objBox.id, vecTran)
        # change dict{rowRemain}
        rowRemain[rowNum] -= objBox.width
        SortedRowRemainValueList = sorted(rowRemain.values())
        SortedRowRemainKeyList = sorted(rowRemain, key=rowRemain.__getitem__)
        # change dict{rowPt0}
        rowPt0[rowNum] = rs.VectorAdd(rowPt0[rowNum], objBox.vecHor)
