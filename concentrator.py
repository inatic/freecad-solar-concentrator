import Part
import FreeCAD

doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument()

# PARABOLA

## Parameters
focalDistance = 1000
parameter1 = -1500
parameter2 = 1500

parabola = Part.Parabola()
parabola.Center = FreeCAD.Vector(0,0,0)
parabola.Axis = FreeCAD.Vector(0,1,0)
parabola.XAxis = FreeCAD.Vector(0,0,1)
parabola.Focal = focalDistance
edge = parabola.toShape(parameter1, parameter2) 
objectParabola = doc.addObject('Part::Feature', 'Parabola')
objectParabola.Shape = edge
objectFocus = doc.addObject('Part::Feature', 'Focus')
pipe = Part.Face(Part.Wire(Part.makeCircle(50, parabola.Focus, parabola.Axis))).extrude(parabola.Axis*20)
objectFocus.Shape = pipe

# TRUSS

## Parameters
subdivisions = 9
topMountOffset = 25
bracketOffset = 25
upperChordOffset = bracketOffset + 50
lowerChordOffset = bracketOffset + 250
bottomMountOffset = 50

bracketSpacing = edge.Length/subdivisions

normalMembers = []
for i in range(0, subdivisions + 1):
    bracketPosition = i*bracketSpacing
    parameter = edge.getParameterByLength(bracketPosition)
    normal = edge.normalAt(parameter).normalize()
    pointOnParabola = edge.valueAt(parameter)
    topMountPoint = pointOnParabola + topMountOffset*normal
    bracketMountPoint = pointOnParabola - bracketOffset*normal
    upperChordMountPoint = pointOnParabola - upperChordOffset*normal
    lowerChordMountPoint = pointOnParabola - lowerChordOffset*normal
    bottomMountPoint = lowerChordMountPoint - bottomMountOffset*normal
    normalMembers.append( (topMountPoint, bracketMountPoint, upperChordMountPoint, lowerChordMountPoint, bottomMountPoint) )

upperChords = []
for i in range(0,len(normalMembers)-1):
    upperChordPoint0 = normalMembers[i][2]
    upperChordPoint1 = normalMembers[i+1][2]
    upperChords.append((upperChordPoint0, upperChordPoint1))

lowerChords = []
for i in range(0,len(normalMembers)-1):
    lowerChordPoint0 = normalMembers[i][3]
    lowerChordPoint1 = normalMembers[i+1][3]
    lowerChords.append((lowerChordPoint0, lowerChordPoint1))

diagonals = []
for i in range(0,len(normalMembers)-1):
  if (i % 2) == 0:
    diagonalPoint0 = normalMembers[i][2]
    diagonalPoint1 = normalMembers[i+1][3]
  else:
    diagonalPoint0 = normalMembers[i][3]
    diagonalPoint1 = normalMembers[i+1][2]
  diagonals.append((diagonalPoint0,diagonalPoint1))

# COLLECTOR SUPPORT

## Parameters
collectorOffset = 150
supportTopWidth = 30
webMembers = 5

collectorSupportMembers = []

num = len(normalMembers)
if num % 2 == 0:
  # even number of members
  indexMember1 = int(num/2 - 1)
  indexMember2 = int(num/2)
else:
  # odd number of members
  indexMember1 = int((num+1)/2 - 2)
  indexMember2 = int((num+1)/2)

supportBase1 = normalMembers[indexMember1][0]
supportBase2 = normalMembers[indexMember2][0]

uDirection = (parabola.Focus - parabola.Center).normalize()
vDirection = (supportBase1 - supportBase2).normalize()
supportTop1 = parabola.Focus - collectorOffset*uDirection + (supportTopWidth/2)*vDirection
supportTop2 = parabola.Focus - collectorOffset*uDirection - (supportTopWidth/2)*vDirection

collectorSupportMembers.append([supportBase1, supportTop1])
collectorSupportMembers.append([supportBase2, supportTop2])
collectorSupportMembers.append([supportTop1, supportTop2])

dir1 = (supportTop1 - supportBase1).normalize()
dir2 = (supportTop2 - supportBase2).normalize()
sideMemberLength = (supportTop1 - supportBase1).Length
webMemberStep = sideMemberLength / webMembers

for i in range(1, webMembers):
  if i % 2 == 0:
    height1 = (i-1) * webMemberStep
    height2 = i * webMemberStep
  else:
    height2 = (i-1) * webMemberStep
    height1 = i * webMemberStep
  point1 = supportBase1 + height1*dir1
  point2 = supportBase2 + height2*dir2
  collectorSupportMembers.append([point1, point2])

# BARS

class Bar:
    def __init__(self, holes, wAxis, wAxisOffset, lengthExtension, width, thickness, holeDiameter, name):
        self.holes = holes
        self.wAxis = wAxis
        self.wAxisOffset = wAxisOffset
        self.lengthExtension = lengthExtension
        self.width = width
        self.thickness = thickness
        self.holeDiameter = holeDiameter
        self.name = name
        self.offsetHoles = [hole + self.wAxisOffset*self.wAxis for hole in self.holes]
        # Local coordinate system
        firstHole = self.offsetHoles[0]
        lastHole = self.offsetHoles[-1]
        self.u = (lastHole - firstHole).normalize()
        self.w = self.wAxis
        self.v = self.w.cross(self.u)

    def getLength(self):
        return (self.holes[-1] - self.holes[0]).Length + self.lengthExtension*2

    def getHolePositions(self):
        positions = []
        firstHole = self.offsetHoles[0]
        lastHole = self.offsetHoles[-1]
        barStart = firstHole - (self.lengthExtension)*self.u
        for hole in self.offsetHoles:
            distanceFromStart = (hole - barStart).Length
            positions.append(distanceFromStart)
        return positions

    def getLine(self):
        line = Part.makeLine(self.holes[0],self.holes[-1])
        return line

    def getShape(self):
        firstHole = self.offsetHoles[0]
        lastHole = self.offsetHoles[-1]
        # Points
        holeDistance = (lastHole - firstHole).Length
        v1 = firstHole + (self.width/2)*self.v - (self.lengthExtension)*self.u                 
        v2 = v1 + holeDistance*self.u + 2*(self.lengthExtension)*self.u
        v3 = v2 - self.width*self.v
        v4 = firstHole - (self.width/2)*self.v - (self.lengthExtension)*self.u 
        # Face
        line1 = Part.Edge(Part.LineSegment(v1, v2))
        line2 = Part.Edge(Part.LineSegment(v2, v3))
        line3 = Part.Edge(Part.LineSegment(v3, v4))
        line4 = Part.Edge(Part.LineSegment(v4, v1))
        wire = Part.Wire([line1, line2, line3, line4])
        face = Part.Face(wire)
        # Cut holes
        for hole in self.offsetHoles:
            circle = Part.Face(Part.Wire(Part.makeCircle(self.holeDiameter/2, hole, self.w))) 
            face = face.cut(circle)
        solid = face.extrude(self.thickness*self.w)
        return solid

## Parameters
barWidth = 20
barThickness = 5
holeDiameter = 8
lengthExtension = 15        # check minimum edge distance for hole (in steel this is typically 1.2*diameter)

bars = []
for i in range(0, len(normalMembers)):
    name = 'Normal' + str(i+1)
    bar = Bar(normalMembers[i], parabola.Axis, 0, lengthExtension, barWidth, barThickness, holeDiameter, name)
    bars.append(bar)

for i in range(0,len(upperChords)):
    if (i % 2) == 0:
        offset = -barThickness
    else:
        offset = barThickness
    name = 'UpperChord' + str(i+1)
    bar = Bar(upperChords[i], parabola.Axis, offset, lengthExtension, barWidth, barThickness, holeDiameter, name)
    bars.append(bar)

for i in range(0,len(lowerChords)):
    if (i % 2) == 0:
        offset = -barThickness
    else:
        offset = barThickness
    name = 'LowerChord' + str(i+1)
    bar = Bar(lowerChords[i], parabola.Axis, offset, lengthExtension, barWidth, barThickness, holeDiameter, name)
    bars.append(bar)

for i in range(0,len(diagonals)):
    if (i % 2) == 0:
        offset = -2*barThickness
    else:
        offset = 2*barThickness
    name = 'Diagonal' + str(i+1)
    bar = Bar(diagonals[i], parabola.Axis, offset, lengthExtension, barWidth, barThickness, holeDiameter, name)
    bars.append(bar)

for i in range(0, len(collectorSupportMembers)):
    name = 'CollectorSupport' + str(i+1)
    offset = 0
    if i in [0,1]:
      offset = 5 
    elif i == 2:
      offset = -5
    elif i % 2 == 1:
      offset = 10
    bar = Bar(collectorSupportMembers[i], parabola.Axis, offset, lengthExtension, barWidth, barThickness, holeDiameter, name)
    bars.append(bar)

## ADD BAR SHAPES TO DOCUMENT

for bar in bars:
    #line = bars.getLine()
    #Part.show(line)
    shape = bar.getShape()
    name = bar.name
    obj = doc.addObject('Part::Feature', name)
    obj.Shape = shape

# CUTLIST

sheet = doc.addObject('Spreadsheet::Sheet', 'Cutlist')
row = 1

sheet.set('A' + str(row),'Truss Members')
sheet.setStyle('A' + str(row), 'bold', 'add')
row+=1

sheet.set('A' + str(row),'Name')
sheet.set('B' + str(row),'Length (mm)')
sheet.set('C' + str(row),'Hole (mm)')
sheet.set('D' + str(row),'Hole (mm)')
sheet.set('E' + str(row),'Hole (mm)')
sheet.recompute()

row+=1

totalBarLength = 0
for bar in bars:
    sheet.set('A'+str(row), bar.name)
    length = bar.getLength()
    totalBarLength += length 
    sheet.set('B'+str(row), str(round(length,2)))
    holePositions = bar.getHolePositions()
    for j in range(0, len(holePositions)):
        column = chr(67+j)
        sheet.set(str(column)+str(row), str(round(holePositions[j],2)))
    row+=1

row+=1
sheet.set('A'+str(row), 'Total Length')
sheet.set('B'+str(row), str(totalBarLength))

sheet.setAlignment('B1:B'+str(row) , 'center', 'keep')
sheet.setAlignment('C1:C'+str(row) , 'center', 'keep')
sheet.setAlignment('D1:D'+str(row) , 'center', 'keep')
sheet.setAlignment('E1:E'+str(row) , 'center', 'keep')
sheet.recompute()
