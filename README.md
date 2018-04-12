# Geodyn voor gemeenten

Tool for calculating wastewater prognoses based on
- municipal sewage systems (Kikker riodesk) 
- residental data (BAG)
- housing development plans RIGO (https://www.plancapaciteit.nl/)

# Installation
- Install the plugin from QGIS repository https://plugins.qgis.org/plugins/GeodynGem/

in settings.py set your output folder for results:
```
gdb = r"path\to\folder\for\results" 
```

# Test
Some imaginary sewage data for testing kan be downloaded from this repo:
https://github.com/bart147/GeodynGem_for_QGIS/blob/master/test_shapefiles/test_shapefiles.zip

Add the shapefiles to your QGIS project and open the plugin. 
The right layer for each input should be recognized by the tool interface based on elements in the layer name. For example: "BAG". 
