# GeoDyn voor gemeenten

DISCLAIMER: this plugin is still in development!

GeoDynGemeenten is develop by BKGIS, for the municipality of Medemblik and designed
by Mark Lamers.

Tool for calculating wastewater prognosis based on
- Municipal sewage systems (Kikker riodesk) 
- Residental data (BAG)
- Housing development plans RIGO (https://www.plancapaciteit.nl/)
- Household drinking water consumption

This tool is based on GeoDynWaterschap. GeoDynWaterschap is an ArcGIS 10
toolbox for the Dutch Water Authorities. GeoDynWaterschap is develop by BKGIS, for
the water Authority HHNK and designed by Mark Lamers.

# Manual
https://github.com/bart147/GeodynGem_for_QGIS/blob/master/doc/HandleidingGeoDynGem.pdf

# Installation
- Install the plugin with Plugin Manager in QGIS or download here https://plugins.qgis.org/plugins/GeodynGem/
- Requires QGIS 2.x

# Test data
Some imaginary data for testing can be downloaded from the repo:
https://github.com/bart147/GeodynGem_for_QGIS/blob/master/test_shapefiles

Add the shapefiles or qgis layer file to your QGIS project and open the plugin. 
The right layer for each input should be recognized by the tool interface based on elements in the layer name. For example: "BAG". 

