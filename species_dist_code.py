from qgis.core import *
from qgis.core import QgsVectorFileWriter, QgsWkbTypes
from qgis.utils import iface  
from qgis.PyQt import QtGui
import os, processing, glob

#ESRI base layer
base_map=qgis.utils.iface.addRasterLayer("http://server.arcgisonline.com/arcgis/rest/services/ESRI_Imagery_World_2D/MapServer?f=json&pretty=true","ArcGIS_base_map")


#set variables
#all records in input must have coordinate values 
#each record needs to have genus and species, not just genus
filepath = "/Users/Maggie/Dropbox/RMIT/GIS_programming/MajorProject/"
data_name="Pseudemoia_ALA"
csv = data_name +".csv"
shp = data_name +".shp"
#convert csv to shp 
#code modified from https://howtoinqgis.wordpress.com/2017/04/24/how-to-convert-a-csv-file-to-a-shapefile-in-qgis-using-python
Input_Table = filepath + csv
# set the name for the field containing the longitude
lon_field = 'Longitude' 
# set the name for the field containing the latitude
lat_field = 'Latitude' 
#ok if records have slightly different crs (ex. WGS84 and GDA94)
crs = 4283
Output_Layer = filepath + shp
 
spatRef = QgsCoordinateReferenceSystem(crs, QgsCoordinateReferenceSystem.EpsgCrsId)
 
inp_tab = QgsVectorLayer(Input_Table, "Input_Table", "ogr")

fields = inp_tab.fields()

#creates the vector layer into which the data will be saved
outLayer = QgsVectorFileWriter(Output_Layer, None, fields, QgsWkbTypes.Point, spatRef, "ESRI Shapefile")

pt = QgsPointXY()
outFeature = QgsFeature()

#puts data in the shape file using the info in the csv file
for feat in inp_tab.getFeatures():
    attrs = feat.attributes()
    pt.setX(float(feat[lon_field]))
    pt.setY(float(feat[lat_field]))
    outFeature.setAttributes(attrs)
    outFeature.setGeometry(QgsGeometry.fromPointXY(pt))
    outLayer.addFeature(outFeature)
del outLayer

#split layer into one layer per species
processing.run('qgis:splitvectorlayer', 
    {
        "INPUT": Output_Layer,
        "FIELD": "Species",
        "OUTPUT": filepath + "species"
    }
)


#create grid
#note: grid is approximately 20km
grid="20km_grid.shp"

processing.run(
    'qgis:creategrid', 
    {
        "TYPE": 2,
        "EXTENT": Output_Layer,
        "HSPACING": 0.18,
        "VSPACING": 0.18,
        "CRS": 'ProjectCrs',
        "OUTPUT": filepath + grid
    }
)


#where the species files are located
Species_files=filepath + "species/"
#select only shapefile layers that contain the word Species
species = "Species_*.gpkg" 
os.chdir(Species_files)
species_path = Species_files + species

#set of all the files to process
layers = glob.glob(species_path)

for layer in layers:  
    #count points in each grid cell
    processing.run(
        'qgis:countpointsinpolygon', 
        {
            "POLYGONS": filepath + grid,
            "POINTS": layer,
            "WEIGHT": None,
            "CLASSIFIED": None,
            "FIELD": 'NumPoints',
            "OUTPUT": layer[:-5] + "_distribution_map.shp"
        }
    )
    #create vector layer from output
    species_name=layer[:-5]
    species_name=species_name.split('Species_')[1]
    dist_map=QgsVectorLayer(layer[:-5] + "_distribution_map.shp", species_name, "ogr")
    TargetField = 'NumPoints'
    RangeList = []
    #Assign range of pts and colour to each group, add groups as needed
    #Change min and max depending on dataset
    Min1 = 0.1
    Max1 = 5.1
    Label1 = 'Low'
    Colour1 = QtGui.QColor('yellow')
    Symbol1 = QgsSymbol.defaultSymbol(dist_map.geometryType())
    Symbol1.setColor(Colour1)
    Symbol1.setOpacity(1)
    Range1 = QgsRendererRange(Min1, Max1, Symbol1, Label1)
    RangeList.append(Range1)
    Min2 = 5.9
    Max2 = 20.1
    Label2 = 'Medium'
    Colour2 = QtGui.QColor('orange')
    Symbol2 = QgsSymbol.defaultSymbol(dist_map.geometryType())
    Symbol2.setColor(Colour2)
    Symbol2.setOpacity(1)
    Range2 = QgsRendererRange(Min2, Max2, Symbol2, Label2)
    RangeList.append(Range2)
    Min3 = 20.9
    Max3 = 1000
    Label3 = 'High'
    Colour3 = QtGui.QColor('red')
    Symbol3 = QgsSymbol.defaultSymbol(dist_map.geometryType())
    Symbol3.setColor(Colour3)
    Symbol3.setOpacity(1)
    Range3 = QgsRendererRange(Min3, Max3, Symbol3, Label3)
    RangeList.append(Range3)
    Renderer = QgsGraduatedSymbolRenderer('', RangeList)
    Renderer.setClassAttribute(TargetField)
    dist_map.setRenderer(Renderer)
    QgsProject.instance().addMapLayer(dist_map)
    
#Save project
QgsProject.instance().write(filepath+data_name+".qgz")
