
import sys, os, logging
from datetime import datetime

# importeer utilities
from utl import start_timer, end_timer, blokje_log, print_log, add_field_from_dict, add_field_from_dict_label, join_field, bereken_veld, rename_fields, get_count, get_d_velden, bereken_veld_label

from Dijkstra import Graph, dijkstra, shortest_path


import processing
##from processing.tools import *
##from qgis.core import QgsVectorLayer, QgsVectorFileWriter, QgsFeature, QgsField, QgsPoint, QgsGeometry, QgsMapLayerRegistry
from qgis.core import *
from PyQt4.QtCore import QVariant

# importeer settings
import settings

gdb                     = settings.gdb
log_dir                 = settings.log_dir
##d_rename_fields         = settings.d_rename_fields  # dictionary met velden om te hernoemen
INP_FIELDS_XLS          = settings.INP_FIELDS_XLS
INP_FIELDS_XLS_SHEET    = settings.INP_FIELDS_XLS_SHEET
INP_POLYGON             = os.path.join(gdb,"medemblik_bemalingsgebieden.shp")
INP_KNOOPPUNTEN         = os.path.join(gdb,"medemblik_MLA_punt.shp")
INP_AFVOERRELATIES      = os.path.join(gdb,"medemblik_MLA_lijn.shp")

# tussenresultaten
KNOOPPUNTEN             = os.path.join(gdb,"KNOOPPUNTEN.shp")         # begin- en eindpunten van afvoerrelaties (lijn-bestand).
EINDKNOOPPUNTEN         = os.path.join(gdb,"EINDKNOOPPUNTEN.shp")     # Alle knooppunten met daarbij het eindpunt
POLYGON_LIS_OVERLAP     = os.path.join(gdb,"POLYGON_LIS_OVERLAP.shp") # bestand met gaten.

# eindresultaat
POLYGON_LIS             = os.path.join(gdb,"POLYGON_LIS.shp")
POLYGON_LIS_SUM         = os.path.join(gdb,"POLYGON_LIS_SUM.shp")

def genereer_knooppunten(iface, INP_POLYGON, INP_AFVOERRELATIES):
    '''Genereert knooppunten op basis van afvoerrelaties (lijn-bestand) waarbij 1 knooppunt per bemalingsgebied is toegestaan.
       Alleen knooppunten die afvoeren naar een andere bemalingsgebied worden meegenomen.
       Van ieder knooppunt wordt het eindpunt bepaald, oftewel het overnamepunt.
       De knooppunten worden ruimtelijk gekoppeld aan bemalingsgebieden.
       resultaat: vlakkenbestand POLYGON_LIS met velden K_LOOST_OP en ONTVANGT_VAN.
       '''
    # niet meer van toepassing
    ##CreatePointsOnLines.Main("hydrovak_split_layer", "PERCENTAGE", "BEGINNING", "NO", "#", 0.5, "NO", "#", "NO", "MiddlePoints") #os.path.join(scratch_gdb,"MiddlePoints"))

    # relaties selecteren die naar ander bemalingsgebied afvoeren. (niet volledig binnen 1 polygoon vallen)
    # processing.alghelp("qgis:selectbylocation")

    # methode 1 layer maken
    # sel_afvoerrelaties = QgsVectorLayer(INP_AFVOERRELATIES, "SEL_AFVOERRELATIES", "ogr")
    # QgsMapLayerRegistry.instance().addMapLayer(sel_afvoerrelaties)

    # methode 2 layer maken
    mapcanvas = iface.mapCanvas()
    layers = mapcanvas.layers()
    for layer in layers:
        print_log("{} == {}".format(layer.source(),INP_AFVOERRELATIES),"i")
        if os.path.basename(layer.source()) == os.path.basename(INP_AFVOERRELATIES):
            sel_afvoerrelaties = layer

    ##sel_afvoerrelaties = layers[0]
    ##sel_afvoerrelaties = QgsVectorLayer(INP_AFVOERRELATIES, "SEL_AFVOERRELATIES", "ogr")
    ##sel_afvoerrelaties = iface.addVectorLayer(INP_AFVOERRELATIES, "selectie", "ogr")

    print_log(sel_afvoerrelaties.source(),"i")

    sel_afvoerrelaties.selectAll()
    processing.runalg("qgis:selectbylocation", sel_afvoerrelaties, INP_POLYGON, u'within', 0, 2)
    print_log("{} features selected".format(sel_afvoerrelaties.selectedFeatureCount()),'i')
    # QgsVectorFileWriter.writeAsVectorFormat(sel_afvoerrelaties,
    #                                         os.path.join(gdb,"exp_selection.shp"), "utf-8",
    #                                         sel_afvoerrelaties.crs(), "ESRI Shapefile", True)

#     arcpy.MakeFeatureLayer_management(INP_AFVOERRELATIES,"SEL_AFVOERRELATIES") # layer maken
#     arcpy.SelectLayerByLocation_management ("SEL_AFVOERRELATIES", "COMPLETELY_WITHIN", INP_POLYGON, "#", "NEW_SELECTION")
#     arcpy.SelectLayerByAttribute_management ("SEL_AFVOERRELATIES", "SWITCH_SELECTION")


    # processing.runalg("grass7:v.to.points", sel_afvoerrelaties, "100000",
    #                   0, False, "134943.95,136747.42,530403.39,531629.38", -1, 0.0001, 0, KNOOPPUNTEN)

    # functie voor bepalen begin en eindpunt
    ##line_layer = qgis.utils.iface.activeLayer()

    point_layer = QgsVectorLayer("Point?crs=epsg:28992", "KNOOPPUNTEN", "memory")
    pr = point_layer.dataProvider()
    point_layer.dataProvider().addAttributes(
        [QgsField("VAN_KNOOPN", QVariant.String),
         QgsField("BEGIN_EIND", QVariant.Int)])
    point_layer.updateFields()

    feat = QgsFeature(point_layer.pendingFields())

    for i, feature in enumerate(sel_afvoerrelaties.selectedFeatures()):  #  .getFeatures()
        geom = feature.geometry().asPolyline()
        start_point = QgsPoint(geom[0])
        end_point = QgsPoint(geom[-1])
        feat.setGeometry(QgsGeometry.fromPoint(start_point))
        feat.setAttribute("VAN_KNOOPN", feature['VAN_KNOOPN'])
        feat.setAttribute("BEGIN_EIND", 0)

        pr.addFeatures([feat])
        ##point_layer.changeAttributeValue(i, 0, "hoi")
        ##i += 1
        feat.setGeometry(QgsGeometry.fromPoint(end_point))
        feat.setAttribute("VAN_KNOOPN", feature['VAN_KNOOPN'])
        feat.setAttribute("BEGIN_EIND", 1)
        ##point_layer.changeAttributeValue(i, 1, 99)
        pr.addFeatures([feat])
    ##point_layer.updateFields()


    QgsMapLayerRegistry.instance().addMapLayer(point_layer)

    return point_layer

#     # begin-/eindpunten genereren op basis van selectie
#     polyline = "SEL_AFVOERRELATIES"
#     spatial_ref = arcpy.Describe(polyline).spatialReference
#
#     mem_point = arcpy.CreateFeatureclass_management(gdb, KNOOPPUNTEN, "POINT", "", "DISABLED", "DISABLED", polyline)
#     arcpy.AddField_management(mem_point, "LineOID", "LONG")
#     arcpy.AddField_management(mem_point, "BEGIN_EIND", "LONG")
#     arcpy.AddField_management(mem_point, "VAN_KNOOPN", "TEXT")
#
#     result = arcpy.GetCount_management(polyline)
#     features = int(result.getOutput(0))
#
#     search_fields = ["SHAPE@", "OID@", "VAN_KNOOPN"]
#     insert_fields = ["SHAPE@", "LineOID", "BEGIN_EIND", "VAN_KNOOPN"]
#
#     with arcpy.da.SearchCursor(polyline, (search_fields)) as search:
#         with arcpy.da.InsertCursor(mem_point, (insert_fields)) as insert:
#             for row in search:
#                 try:
#                     line_geom = row[0]
# ##                    length = float(line_geom.length)
#                     oid = str(row[1])
#                     van_knoopn = row[2]
#                     start = arcpy.PointGeometry(line_geom.firstPoint)
#                     end = arcpy.PointGeometry(line_geom.lastPoint)
#
#                     insert.insertRow((start, oid, 0, van_knoopn)) # 0 = beginpunt
#                     insert.insertRow((end, oid, 1, van_knoopn))   # 1 = eindpunt
#                 except Exception as e:
#                     arcpy.AddMessage(str(e.message))
#
#     return KNOOPPUNTEN, EINDKNOOPPUNTEN


def koppel_knooppunten_aan_bemalingsgebieden(iface, d_velden, INP_POLYGON, KNOOPPUNTEN):
    # knooppunten koppelen aan bemalingsgebieden / gebieden voorzien van code. (sp.join)
    ##arcpy.MakeFeatureLayer_management(KNOOPPUNTEN,"VAN_KNOOPPUNTEN","BEGIN_EIND = 0") # selectie beginpunten

    expr = QgsExpression("\"BEGIN_EIND\" = {}".format(0))
    it = KNOOPPUNTEN.getFeatures(QgsFeatureRequest(expr)) # iterator object
    KNOOPPUNTEN.setSelectedFeatures([i.id() for i in it])
    print_log("{} selected".format(KNOOPPUNTEN.selectedFeatureCount()), "i")
    processing.runalg("qgis:joinattributesbylocation", INP_POLYGON, KNOOPPUNTEN, u'intersects', 0, 0, '', 1, POLYGON_LIS)
    processing.runalg("qgis:joinattributesbylocation", INP_POLYGON, KNOOPPUNTEN, u'intersects', 0, 1, 'sum', 1, POLYGON_LIS_SUM)

    ## arcpy.SpatialJoin_analysis(INP_POLYGON, "VAN_KNOOPPUNTEN", POLYGON_LIS, "JOIN_ONE_TO_ONE", "KEEP_ALL")

    polygon_lis_sum = QgsVectorLayer(POLYGON_LIS_SUM, "polygon_lis_sum", "ogr")
    polygon_lis = QgsVectorLayer(POLYGON_LIS, "polygon_lis", "ogr")
    polygon_lis.dataProvider().addAttributes([QgsField('count', QVariant.Int)])
    polygon_lis.updateFields()

    QgsMapLayerRegistry.instance().addMapLayer(polygon_lis)
    QgsMapLayerRegistry.instance().addMapLayer(polygon_lis_sum)

    # join field met summary gegevens
    join_field(input_table=polygon_lis,
               join_table=polygon_lis_sum,
               field_to_calc="count",
               field_to_copy="count",
               joinfield_input_table="OBJECTID",
               joinfield_join_table="OBJECTID")

    QgsMapLayerRegistry.instance().removeMapLayer(polygon_lis_sum)

    # controleer spjoin
    controleer_spjoin(polygon_lis,"count")

    print_log("Bepaal in welk bemalingsgebied het eindpunt van afvoerrelatie ligt...",'i')

    # hier eindpunten bepalen...
    #
    #
    #
    #
    # expr = QgsExpression("\"BEGIN_EIND\" = {}".format(0))
    # it = KNOOPPUNTEN.getFeatures(QgsFeatureRequest(expr))  # iterator object
    # KNOOPPUNTEN.setSelectedFeatures([i.id() for i in it])
    # print_log("{} selected".format(KNOOPPUNTEN.selectedFeatureCount()), "i")
    # processing.runalg("qgis:joinattributesbylocation", INP_POLYGON, KNOOPPUNTEN, u'intersects', 0, 0, '', 1,
    #                   POLYGON_LIS)
    #
    #
    #
    #


    # eindpunten voorzien van bemalingsgebied (sp.join)
    # arcpy.MakeFeatureLayer_management(KNOOPPUNTEN,"SEL_EINDKNOOPPUNTEN","BEGIN_EIND = 1") # 0 = beginpunt, 1 = eindpunt
    # arcpy.SpatialJoin_analysis("SEL_EINDKNOOPPUNTEN", POLYGON_LIS, EINDKNOOPPUNTEN, "JOIN_ONE_TO_ONE", "KEEP_ALL")
    #
    # # invullen veld LOOST_OP met code bemalingsgebied.
    # add_field_from_dict_label(POLYGON_LIS, "st1a", d_velden)
    # join_field(POLYGON_LIS, EINDKNOOPPUNTEN, "K_LOOST_OP", "VAN_KNOOPN_1", "VAN_KNOOPN", "VAN_KNOOPN")
    #
    # # Eindbemalingsgebied /overnamepunt bepalen
    # arcpy.MakeFeatureLayer_management(POLYGON_LIS,"SEL_POLYGON_LIS","Join_Count > 0 ") # selectie beginpunten
    # where_clause = "Join_Count > 0 AND K_LOOST_OP IS NULL"

    return POLYGON_LIS, POLYGON_LIS_OVERLAP


def lis2graph(POLYGON_LIS):
    """Maakt Graph met LIS-netwerk en bepaalt onderbemalingen.
       Vult [ONTV_VAN] en [X_OBEMAL].
       Gebruikt [LOOST_OP] en [VAN_KNOOPN] als edge (relation) en VAN_KNOOPN als node"""
    # graph aanmaken
    graph = Graph()
    graph_rev = Graph()

    # Cursur velden
    search_fields = ["VAN_KNOOPN", "K_LOOST_OP"]
    update_fields = ["VAN_KNOOPN", "K_ONTV_VAN", "X_OBEMAL", "X_OPPOMP", "K_KNP_EIND"]

    print_log ("netwerk opslaan als graph...","i")
    with arcpy.da.SearchCursor(POLYGON_LIS, (search_fields)) as cursor: # sql_clause=(None, 'ORDER BY {}'.format("VAN_KNOOPN")))
        for row in cursor:
            VAN_KNOOPN, LOOST_OP = row
            graph.add_node(VAN_KNOOPN)
            graph_rev.add_node(VAN_KNOOPN)
            if LOOST_OP != None:
                graph.add_edge(VAN_KNOOPN, LOOST_OP, 1) # richting behouden voor bovenliggende gebied
                graph_rev.add_edge(LOOST_OP, VAN_KNOOPN, 1) # richting omdraaien voor onderliggende gebied
    del cursor, row

    print_log ("onderbemaling bepalen voor rioolgemalen en zuiveringen...","i")
    where_clause = "Join_Count > 0"
    with arcpy.da.UpdateCursor(POLYGON_LIS, (update_fields), where_clause) as cursor: # sql_clause=(None, 'ORDER BY {}'.format("VAN_KNOOPN")))
        for row in cursor:
            VAN_KNOOPN = row[0]
            nodes = dijkstra(graph, VAN_KNOOPN)[0]
            ##arcpy.AddMessage("nodes for {}: {}".format(VAN_KNOOPN,nodes))
            K_KNP_EIND, X_OPPOMP  = [(key, value) for key, value in sorted(nodes.iteritems(), key=lambda (k,v): (v,k))][-1]
            ##arcpy.AddMessage("endnode for {}: {},{}".format(VAN_KNOOPN,K_KNP_EIND, X_OPPOMP))
            d_edges = dijkstra(graph_rev,VAN_KNOOPN)[1]  # {'B': 'A', 'C': 'B', 'D': 'C'}
            l_onderliggende_gemalen = str(list(d_edges)) # [u'ZRE-123',u'ZRE-234']
            l_onderliggende_gemalen = l_onderliggende_gemalen.replace("u'","'").replace("[","").replace("]","")
            row[1] = l_onderliggende_gemalen             # ONTV_VAN = 'ZRE-1','ZRE-2'
            row[2] = len(list(d_edges))                  # X_OBEMAL = 2 (aantal onderbemalingen)
            row[3] = X_OPPOMP + 1                        # X_OPPOMP = 1 (aantal keer oppompen tot rwzi) met shortestPath ('RWZI','ZRE-4')
            row[4] = K_KNP_EIND                          # eindbemalingsgebied / overnamepunt. bepaald uit netwerk.
            cursor.updateRow(row)
    del cursor, row

    return POLYGON_LIS


def controleer_spjoin(layer,fld_join_count):
    """Controleer of spjoin geslaagd is (Join_Count moet in principe overal 1 zijn).
       Vult VAN_KNOOPN voor lege polygonen met 'LEEG-<OBJID>'."""
    i_dubbel, i_leeg = 0, 0

    layer.startEditing()
    for i, feature in enumerate(layer.getFeatures()):

        JOIN_COUNT = feature[fld_join_count] if feature[fld_join_count] else 0
        VAN_KNOOPN = feature["VAN_KNOOPN"] if feature["VAN_KNOOPN"] else None
        print_log("{} - {}".format(VAN_KNOOPN,JOIN_COUNT), "i")
        if JOIN_COUNT >= 2:
            i_dubbel += 1
            print_log("polygon '{}' bevat {} objecten!".format(VAN_KNOOPN,JOIN_COUNT), "i")
        if JOIN_COUNT == 0:
            i_leeg += 1
            feature.setAttribute("VAN_KNOOPN", "LEEG-{}".format(i))
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("VAN_KNOOPN"), "LEEG-{}".format(i))
    layer.commitChanges()

    if i_dubbel == 1: print_log("\n{} polygoon bevat 2 of meer LIS-objecten".format(i_dubbel),"w")
    if i_dubbel > 1: print_log("\n{} polygonen bevatten 2 of meer LIS-objecten".format(i_dubbel),"w")
    if i_leeg == 1: print_log("{} polygoon is leeg\n".format(i_leeg),"w")
    if i_leeg > 1: print_log("{} polygonen zijn leeg\n".format(i_leeg),"w")
    if i_leeg >= 1: print_log("lege polygonen voorzien van VAN_KNOOPN-> 'LEEG-<OBJID>'","i")


def controleer_hoofdbemalingsgebieden(POLYGON_LIS, POLYGON_LIS_OVERLAP):
    """Controleer of hoofdbemalingsgebieden overlappen."""
    # Intersect_analysis (in_features, out_feature_class, {join_attributes}, {cluster_tolerance}, {output_type})
    arcpy.Intersect_analysis (POLYGON_LIS, POLYGON_LIS_OVERLAP)
    return get_count(POLYGON_LIS_OVERLAP)


def main(iface):
    """Hoofdmenu:
        1.) Knooppunten kopieren en velden toevoegen.
            Koppel KNOOPPUNTEN aan RIOLERINGSGEBIEDEN
        2.) Dijkstra.Graph maken o.b.v. [KNOOPNR] en [LOOST_OP]. bepaal "X_OBEMAL", "X_OPPOMP", "K_KNP_EIND", "ONTV_VAN"
        3.) Controleer overlap HOOFDBEMALINGSGEBIEDEN
        4.) Add results to map
        """

    # laod from settings
    gdb = settings.gdb
    log_dir = settings.log_dir
    INP_FIELDS_XLS = settings.INP_FIELDS_XLS
    INP_FIELDS_XLS_SHEET = settings.INP_FIELDS_XLS_SHEET
    INP_POLYGON = os.path.join(gdb, "medemblik_bemalingsgebieden.shp")
    INP_KNOOPPUNTEN = os.path.join(gdb, "medemblik_MLA_punt.shp")
    INP_AFVOERRELATIES = os.path.join(gdb, "medemblik_MLA_lijn.shp")

    # ##########################################################################
    # 1.) Knooppunten exporteren, velden toevoegen.
    # relaties selecteren die naar ander bemalingsgebied afvoeren. (niet volledig binnen 1 polygoon vallen)
    # knooppunten selecteren die op ander bemalingsgebied afvoeren (op basis van selectie afvoerrelaties)
    # knooppunten koppelen aan bemalingsgebieden / gebieden voorzien van code. (sp.join)
    # eindpunten genereren van afvoerrelatie (line_to_point, select if not intersect with knooppunt)
    # eindpunten voorzien van bemalingsgebied (sp.join)
    # invullen veld LOOST_OP met code bemalingsgebied.

    blokje_log("Veld-info ophalen...","i")
    d_velden = get_d_velden(INP_FIELDS_XLS, 0)
    for fld in d_velden:
        print_log("{}\n{}".format(fld,d_velden[fld]),"i")


    blokje_log("Knooppunten genereren...","i")
    # genereer knooppunten uit afvoerrelaties
    ##KNOOPPUNTEN, EINDKNOOPPUNTEN = genereer_knooppunten(INP_POLYGON, INP_AFVOERRELATIES)
    point_layer = genereer_knooppunten(iface, INP_POLYGON, INP_AFVOERRELATIES)

    blokje_log("Knooppunten koppelen aan bemalingsgebieden...","i")
    POLYGON_LIS, POLYGON_LIS_OVERLAP = koppel_knooppunten_aan_bemalingsgebieden(iface, d_velden, INP_POLYGON, point_layer)

    # # ##########################################################################
    # # 2.) Graph vullen met LIS [LOOST_OP], onderbemaling bepalen en wegschrijven in [ONTV_VAN]
    #
    # blokje_log("Bepaal onderbemaling en aantal keer oppompen...","i")
    # POLYGON_LIS = lis2graph(POLYGON_LIS)
    #
    # # ##########################################################################
    # # 3.) Controleer overlap HOOFDBEMALINGSGEBIEDEN
    # blokje_log("Controleer topologie bemalingsgebieden...","i")
    # controleer_spjoin(POLYGON_LIS,"Join_Count")
    # aantal_overlaps = controleer_hoofdbemalingsgebieden(POLYGON_LIS, POLYGON_LIS_OVERLAP)
    #
    # # ##########################################################################
    # # 4.) Velden overnemen uit Kikker
    # blokje_log("Overige velden overnemen uit knooppunten Kikker...","i")
    # add_field_from_dict_label(POLYGON_LIS, "st1b", d_velden)
    # join_field(POLYGON_LIS,INP_KNOOPPUNTEN,"K_KNP_NR",   "VAN_KNOOPN",  "VAN_KNOOPN", "VAN_KNOOPN")
    # join_field(POLYGON_LIS,INP_KNOOPPUNTEN,"K_BEM_GEB",  "NAAM",        "VAN_KNOOPN", "VAN_KNOOPN")
    # join_field(POLYGON_LIS,INP_KNOOPPUNTEN,"K_INST_TOT", "CAP_INST_M",  "VAN_KNOOPN", "VAN_KNOOPN")
    # join_field(POLYGON_LIS,INP_KNOOPPUNTEN,"K_BR_ST_M3", "BERGING_M3",  "VAN_KNOOPN", "VAN_KNOOPN")
    # join_field(POLYGON_LIS,INP_KNOOPPUNTEN,"K_OSH",      "LAAGSTE_OS",  "VAN_KNOOPN", "VAN_KNOOPN")
    #
    # # ##########################################################################
    # # 5.) Add results to map
    # blokje_log("Tussenresultaten toevoegen aan mxd...","i")
    # MXD = arcpy.mapping.MapDocument("CURRENT")
    # DF = arcpy.mapping.ListDataFrames(MXD)[0]
    # results_to_add = [
    #     (POLYGON_LIS,"eindresultaat stap 1"),
    #     (KNOOPPUNTEN,"tussenresultaat"),
    #     (EINDKNOOPPUNTEN,"tussenresultaat"),
    #     ]
    # if aantal_overlaps > 0:
    #     results_to_add.append(POLYGON_LIS_OVERLAP)
    #     print_log("hoofdbemalingsgebieden overlappen op {} plekken!".format(aantal_overlaps/2),"w")
    #     print_log("{} wordt toegevoegd als tussenresultaat".format(POLYGON_LIS_OVERLAP),"i")
    # for fc,besch in results_to_add:
    #     layername = "{}: {}".format(besch,fc)
    #     arcpy.MakeFeatureLayer_management(fc, layername)
    #     layer = arcpy.mapping.Layer(layername)
    #     arcpy.mapping.AddLayer(DF, layer, "TOP") # AUTO_ARRANGE, BOTTOM

if __name__ == '__main__':

    # Prepare the environment for standalone outside qgis
    import sys
    from qgis.core import *
    from PyQt4.QtGui import *

    QgsApplication.setPrefixPath("C:/OSGeo4W64/apps/qgis", True)
    app = QApplication([], True)
    QgsApplication.initQgis()

    # Prepare processing framework
    sys.path.append('C:/OSGEO4~1/apps/qgis/python/plugins') # Folder where Processing is located '/home/user/.qgis2/python/plugins'
    from processing.core.Processing import Processing

    Processing.initialize()
    from processing.tools import *

    # Exit applications
    QgsApplication.exitQgis()
    QApplication.exit()



    # # laod from settings
    gdb                     = settings.gdb
    log_dir                 = settings.log_dir
    ##d_rename_fields         = settings.d_rename_fields  # dictionary met velden om te hernoemen
    INP_FIELDS_XLS          = settings.INP_FIELDS_XLS
    INP_FIELDS_XLS_SHEET    = settings.INP_FIELDS_XLS_SHEET
    INP_POLYGON             = os.path.join(gdb,"medemblik_bemalingsgebieden.shp")
    INP_KNOOPPUNTEN         = os.path.join(gdb,"medemblik_MLA_punt.shp")
    INP_AFVOERRELATIES      = os.path.join(gdb,"medemblik_MLA_lijn.shp")

    # tussenresultaten
    KNOOPPUNTEN             = "KNOOPPUNTEN"         # begin- en eindpunten van afvoerrelaties (lijn-bestand).
    EINDKNOOPPUNTEN         = "EINDKNOOPPUNTEN"     # Alle knooppunten met daarbij het eindpunt
    POLYGON_LIS_OVERLAP     = "POLYGON_LIS_OVERLAP" # bestand met gaten.

    # eindresultaat
    POLYGON_LIS             = "POLYGON_LIS"

    # create data folder (if not exists)
    if not os.path.exists(gdb): os.makedirs(gdb)

    # set env

    # logging
    LOGGING_LEVEL = logging.INFO
    if not os.path.exists(log_dir): os.mkdir(log_dir)
    strftime = datetime.strftime(datetime.now(),"%Y%m%d-%H.%M")
    logFileName = 'GeoDyn_{}.log'.format(strftime)
    logFile = os.path.join(log_dir,logFileName)
    logging.basicConfig(filename=logFile, level=LOGGING_LEVEL)
    logging.getLogger().setLevel(LOGGING_LEVEL)

    # start timer
    fTimeStart = start_timer()

    # print belangrijke informatie
    print_log("\nworkspace = {}".format(gdb),"i")
    print_log("logfile = {}".format(logFile),"i")
    print_log("py-file: {}".format(sys.argv[0]),"i")

    # run main
    main()


    # end timer
    end_timer(fTimeStart)


