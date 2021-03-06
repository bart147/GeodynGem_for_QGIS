import os

# qgis modules
import processing
from qgis.core import *
from PyQt4.QtCore import QVariant

# custom modules
import settings
from utl import blokje_log, print_log, add_field_from_dict, add_field_from_dict_label, join_field, add_layer, fields_to_uppercase
from Dijkstra import Graph, dijkstra

def create_new_inp_polygon(inp_polygon):
    '''Copy shapefile, delete all fields except OBJECTID.
    If OBJECTID does not excist: add field and calculate.'''
    # copy shapefile
    INP_POLYGON_COPY = os.path.join(gdb, "inp_polygon_copy.shp")
    QgsVectorFileWriter.writeAsVectorFormat(inp_polygon, INP_POLYGON_COPY, "utf-8", QgsCoordinateReferenceSystem(28992),
                                            "ESRI Shapefile")
    vl = QgsVectorLayer(INP_POLYGON_COPY, "inp_polygon_copy", "ogr")
    add_layer(vl)

    # remove old fields except OBJECTID
    fields = vl.dataProvider().fields()
    fList = []
    for fld in fields:
        ##if fld.name() <> 'OBJECTID': # condition removed. can cause problems if OBJECTID is not unique
        fList.append(vl.fieldNameIndex( fld.name() )) # hoe index opvragen?

    vl.dataProvider().deleteAttributes(fList)
    vl.updateFields()

    # add new OBJECTID
    if vl.fieldNameIndex('OBJECTID') == -1:
        # add OBJECTID
        fld = QgsField('OBJECTID', QVariant.Int)
        vl.dataProvider().addAttributes([fld])
        vl.updateFields()

        # set OBJECTID
        vl.startEditing()
        for i, feature in enumerate(vl.getFeatures()):
            feature['OBJECTID'] = i
            vl.updateFeature(feature)
            ##pr.changeAttributeValues({feature.id(): {pr.fieldNameMap()['OBJECTID']: 1}})
        vl.commitChanges()

    return vl


def controleer_bemalingsgebieden(inp_polygon, inp_knooppunten):
    '''Controleer of knoopunten in bemalingsgebied liggen.'''

    processing.runalg("qgis:selectbylocation", inp_knooppunten, inp_polygon, u'intersects', 0, 0)
    inp_knooppunten.invertSelection()
    ids = []
    if inp_knooppunten.fields().indexFromName('VAN_KNOOPN') == -1:
        field = 0
    else:
        field = 'VAN_KNOOPN'
    for feature in inp_knooppunten.selectedFeatures():
        ids.append(feature[field])
    if len(ids) == 1:
        print_log("1 rioolgemaal ligt niet in een bemalingsgebied {}".format(ids), "w")
    elif len(ids) > 1:
        print_log("{} rioolgemalen liggen niet in een bemalingsgebied {}".format(len(ids),ids), "w")
    inp_knooppunten.setSelectedFeatures([])


def genereer_knooppunten(iface, inp_polygon, sel_afvoerrelaties):
    '''Genereert knooppunten op basis van afvoerrelaties (lijn-bestand) waarbij 1 knooppunt per bemalingsgebied is toegestaan.
       Alleen knooppunten die afvoeren naar een andere bemalingsgebied worden meegenomen.
       Van ieder knooppunt wordt het eindpunt bepaald, oftewel het overnamepunt.
       De knooppunten worden ruimtelijk gekoppeld aan bemalingsgebieden.
       resultaat: vlakkenbestand POLYGON_LIS met velden K_LOOST_OP en ONTVANGT_VAN.
       '''

    # afvoerrelaties selecteren die niet binnen 1 bemalingsgebied vallen
    sel_afvoerrelaties.selectAll()
    processing.runalg("qgis:selectbylocation", sel_afvoerrelaties, inp_polygon, u'within', 0, 2)
    print_log("{} features selected".format(sel_afvoerrelaties.selectedFeatureCount()),'d')

    point_layer = QgsVectorLayer("Point?crs=epsg:28992", "knooppunten", "memory")
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

    point_layer = add_layer(point_layer)
    ##QgsMapLayerRegistry.instance().addMapLayer(point_layer)

    return point_layer


def koppel_knooppunten_aan_bemalingsgebieden(iface, d_velden, inp_polygon, knooppunten, inp_knooppunten):
    # knooppunten koppelen aan bemalingsgebieden / gebieden voorzien van code. (sp.join)

    # beginpunten selecteren (sel1)
    expr = QgsExpression("\"BEGIN_EIND\" = {}".format(0))
    it = knooppunten.getFeatures(QgsFeatureRequest(expr)) # iterator object
    knooppunten.setSelectedFeatures([i.id() for i in it])

    print_log("{} selected".format(knooppunten.selectedFeatureCount()), "d")
    # bug 26L error. executing algoritm spatial join #5: export selection to prevent
    QgsVectorFileWriter.writeAsVectorFormat(knooppunten, os.path.join(gdb,"knooppunten_sel1.shp"), "utf-8",
                                            knooppunten.crs(), "ESRI Shapefile", True)
    knooppunten_sel1 = QgsVectorLayer(os.path.join(gdb,"knooppunten_sel1.shp"), "knooppunten_sel1", "ogr")
    add_layer(knooppunten_sel1)

    # eindpunten selecteren (sel2)
    expr = QgsExpression("\"BEGIN_EIND\" = {}".format(1))
    it = knooppunten.getFeatures(QgsFeatureRequest(expr))  # iterator object
    knooppunten.setSelectedFeatures([i.id() for i in it])
    print_log("{} selected".format(knooppunten.selectedFeatureCount()), "d")
    # bug 26L error. executing algoritm spatial join #5: export selection to prevent
    QgsVectorFileWriter.writeAsVectorFormat(knooppunten, os.path.join(gdb, "knooppunten_sel2.shp"), "utf-8",
                                            knooppunten.crs(), "ESRI Shapefile", True)
    knooppunten_sel2 = QgsVectorLayer(os.path.join(gdb, "knooppunten_sel2.shp"), "knooppunten_sel2", "ogr")
    add_layer(knooppunten_sel2)

    # bemalingsgebieden selecteren die alleen eindpunten bevatten, maar geen beginpunten (eindpunt / rwzi)
    # 1.) selecteer bemalingsgebieden met eindpunten
    processing.runalg("qgis:selectbylocation", inp_polygon, knooppunten_sel2, ['intersects'], 0, 0)
    # 2.) verwijder van selectie alles gebieden met beginpunten
    processing.runalg("qgis:selectbylocation", inp_polygon, knooppunten_sel1, ['intersects'], 0, 2)
    # exporteer als eindgebieden
    EINDGEBIEDEN = os.path.join(gdb, "eindgebieden.shp")
    QgsVectorFileWriter.writeAsVectorFormat(inp_polygon, EINDGEBIEDEN, "utf-8",
                                            inp_polygon.crs(), "ESRI Shapefile", True)
    eindgebieden = QgsVectorLayer(EINDGEBIEDEN, "eindgebieden", "ogr")
    add_layer(eindgebieden)

    # nu bepalen wat de (juiste) ontbrekende knooppunten zijn om toe te voegen (moet eindpunt zijn van afvoerrelatie)
    # 1.) bepaal eindknooppunten van eindgebieden
    processing.runalg("qgis:selectbylocation", knooppunten_sel2, eindgebieden, ['intersects'], 0, 0)
    # 2.) bepaal welke knooppunten dit zijn in kikker bestand voor juiste code VANKNOOPN
    processing.runalg("qgis:selectbylocation", inp_knooppunten, knooppunten_sel2, ['intersects'], 1, 0)

    # extra knooppunten eindgebied toevoegen aan sel1 (beginpunten)
    pr = knooppunten_sel1.dataProvider()
    feat = QgsFeature(knooppunten_sel1.pendingFields())
    for feature in inp_knooppunten.selectedFeatures():
        feat.setGeometry(feature.geometry())
        feat.setAttribute("VAN_KNOOPN", feature['VAN_KNOOPN'])
        pr.addFeatures([feat])

    # remove selections
    inp_knooppunten.setSelectedFeatures([])
    inp_polygon.setSelectedFeatures([])
    knooppunten_sel1.setSelectedFeatures([])

    # create polygon lis
    processing.runalg("qgis:joinattributesbylocation", inp_polygon, knooppunten_sel1, u'intersects', 0, 0, '', 1, POLYGON_LIS)
    processing.runalg("qgis:joinattributesbylocation", inp_polygon, knooppunten_sel1, u'intersects', 0, 1, 'sum', 1, POLYGON_LIS_SUM)

    polygon_lis_sum = QgsVectorLayer(POLYGON_LIS_SUM, "polygon_kikker_sum", "ogr")
    polygon_lis = QgsVectorLayer(POLYGON_LIS, "polygon_kikker", "ogr")
    polygon_lis.dataProvider().addAttributes([QgsField('count', QVariant.Int)])
    polygon_lis.updateFields()

    polygon_lis = add_layer(polygon_lis)
    ##fields_to_uppercase(polygon_lis)  # created for sqlite usage which defaults to lowercase...
    polygon_lis_sum = add_layer(polygon_lis_sum)

    # join field met summary gegevens
    join_field(input_table=polygon_lis,
               join_table=polygon_lis_sum,
               field_to_calc="count",
               field_to_copy="count",
               joinfield_input_table="OBJECTID",
               joinfield_join_table="OBJECTID")

    print_log("Bepaal in welk bemalingsgebied het eindpunt van afvoerrelatie ligt...",'i')

    knooppunten_sel2.setSelectedFeatures([])
    processing.runalg("qgis:joinattributesbylocation", knooppunten_sel2, polygon_lis, u'intersects', 0, 0, '', 1, EINDKNOOPPUNTEN)

    eindknooppunten = QgsVectorLayer(EINDKNOOPPUNTEN, "eindknooppunten", "ogr")
    eindknooppunten = add_layer(eindknooppunten)
    ##QgsMapLayerRegistry.instance().addMapLayer(eindknooppunten)

    # invullen veld LOOST_OP met code bemalingsgebied.
    add_field_from_dict_label(polygon_lis, "st1a", d_velden)
    join_field(polygon_lis, eindknooppunten, "K_LOOST_OP", "VAN_KNOO_1", "VAN_KNOOPN", "VAN_KNOOPN")

    return polygon_lis


def lis2graph(layer):
    """Maakt Graph met LIS-netwerk en bepaalt onderbemalingen.
       Vult [ONTV_VAN] en [X_OBEMAL].
       Gebruikt [LOOST_OP] en [VAN_KNOOPN] als edge (relation) en VAN_KNOOPN als node"""
    # graph aanmaken
    graph = Graph()
    graph_rev = Graph()
    d_K_ONTV_VAN = {}    # alle onderliggende gemalen
    d_K_ONTV_VAN_n1 = {} # alle onderliggende gemalen op 1 niveau diep ivm optellen overcapaciteit


    print_log ("netwerk opslaan als graph...","i")
    for feature in layer.getFeatures():  # .getFeatures()
        VAN_KNOOPN = feature["VAN_KNOOPN"]
        LOOST_OP = feature["K_LOOST_OP"]
        graph.add_node(VAN_KNOOPN)
        graph_rev.add_node(VAN_KNOOPN)
        if LOOST_OP != None:
            graph.add_edge(VAN_KNOOPN, LOOST_OP, 1)  # richting behouden voor bovenliggende gebied
            graph_rev.add_edge(LOOST_OP, VAN_KNOOPN, 1)  # richting omdraaien voor onderliggende gebied
    edges_as_tuple = list(graph.distances)  # lijst met tuples: [('A', 'B'), ('C', 'B')]

    print_log("onderbemaling bepalen voor rioolgemalen en zuiveringen...", "i")
    where_clause = "Join_Count > 0"
    layer.startEditing()
    for i, feature in enumerate(layer.getFeatures()):  # .getFeatures()
        if not feature["count"] >= 1: continue
        VAN_KNOOPN = feature["VAN_KNOOPN"]
        nodes = dijkstra(graph, VAN_KNOOPN)[0]
        print_log("nodes for {}: {}".format(VAN_KNOOPN,nodes), 'd')
        K_KNP_EIND, X_OPPOMP = [(key, value) for key, value in sorted(nodes.iteritems(), key=lambda (k, v): (v, k))][-1]
        print_log("endnode for {}: {},{}".format(VAN_KNOOPN,K_KNP_EIND, X_OPPOMP),'d')
        d_edges = dijkstra(graph_rev, VAN_KNOOPN)[1]  # {'B': 'A', 'C': 'B', 'D': 'C'}
        l_onderliggende_gemalen = str(list(d_edges))  # [u'ZRE-123',u'ZRE-234']
        l_onderliggende_gemalen = l_onderliggende_gemalen.replace("u'", "'").replace("[", "").replace("]", "")
        layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("K_ONTV_VAN"), l_onderliggende_gemalen) # K_ONTV_VAN = 'ZRE-1','ZRE-2'
        layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("X_OBEMAL"), len(list(d_edges)))        # X_OBEMAL = 2 (aantal onderbemalingen)
        layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("X_OPPOMP"),  X_OPPOMP + 1)             # X_OPPOMP = 1 (aantal keer oppompen tot rwzi) met shortestPath ('RWZI','ZRE-4')
        layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("K_KNP_EIND"), K_KNP_EIND)              # eindbemalingsgebied / overnamepunt. bepaald uit netwerk.
        d_K_ONTV_VAN[VAN_KNOOPN] = l_onderliggende_gemalen

        # onderbemalingen 1 niveau diep
        l_onderliggende_gemalen_n1 = [start for start, end in edges_as_tuple if end == VAN_KNOOPN]  # dus start['A', 'C'] uit tuples[('A', 'B'),('C', 'B')] als end == 'B'
        d_K_ONTV_VAN_n1[VAN_KNOOPN] =  str(l_onderliggende_gemalen_n1).replace("u'", "'").replace("[", "").replace("]", "") # naar str() en verwijder u'tjes en haken
    layer.commitChanges()

    return [d_K_ONTV_VAN, d_K_ONTV_VAN_n1]


def controleer_spjoin(layer,fld_join_count):
    """Controleer of spjoin geslaagd is (Join_Count moet in principe overal 1 zijn).
       Vult VAN_KNOOPN voor lege bemalingsgebieden met 'LEEG-<OBJID>'."""
    i_dubbel, i_leeg = 0, 0

    layer.startEditing()
    for i, feature in enumerate(layer.getFeatures()):
        JOIN_COUNT = feature[fld_join_count] if feature[fld_join_count] else 0
        VAN_KNOOPN = feature["VAN_KNOOPN"] if feature["VAN_KNOOPN"] else None
        print_log("{} - {}".format(VAN_KNOOPN,JOIN_COUNT), "d")
        if JOIN_COUNT == 0 and VAN_KNOOPN != None: # uitzondering: rwzi later aangevuld
            ##feature.setAttribute("count", 1)
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("count"), 1)
            JOIN_COUNT = 1
        if JOIN_COUNT >= 2:
            i_dubbel += 1
            print_log("bemalingsgebied '{}' bevat {} rioolgemalen!".format(VAN_KNOOPN,JOIN_COUNT), "i")
        if JOIN_COUNT == 0:
            i_leeg += 1
            ##feature.setAttribute("VAN_KNOOPN", "LEEG-{}".format(i))
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("VAN_KNOOPN"), "LEEG-{}".format(i))
    layer.commitChanges()

    if i_dubbel == 1: print_log("{} bemalingsgebied bevat 2 of meer rioolgemalen, zie veld 'count' in eindresultaat".format(i_dubbel),"w")
    if i_dubbel > 1: print_log("{} bemalingsgebieden bevatten 2 of meer rioolgemalen, zie veld 'count' in eindresultaat".format(i_dubbel),"w")
    if i_leeg == 1: print_log("{} bemalingsgebied is leeg\n".format(i_leeg),"w")
    if i_leeg > 1: print_log("{} bemalingsgebieden zijn leeg\n".format(i_leeg),"w")
    if i_leeg >= 1: print_log("lege bemalingsgebieden voorzien van VAN_KNOOPN-> 'LEEG-<OBJID>'","i")


def controleer_hoofdbemalingsgebieden(polygon_lis):
    """Controleer of hoofdbemalingsgebieden overlappen."""
    # Intersect_analysis (in_features, out_feature_class, {join_attributes}, {cluster_tolerance}, {output_type})
    ##arcpy.Intersect_analysis (POLYGON_LIS, POLYGON_LIS_OVERLAP)
    processing.runalg("saga:polygonselfintersection", polygon_lis, "VAN_KNOOPN", POLYGON_LIS_OVERLAP)
    polygon_lis_overlap = QgsVectorLayer(POLYGON_LIS_OVERLAP, "bemalingsgebieden overlap", "ogr")
    ##QgsMapLayerRegistry.instance().addMapLayer(polygon_lis_overlap)

    expr = QgsExpression("\"VAN_KNOOPN\" {}".format("IS NULL"))
    it = polygon_lis_overlap.getFeatures(QgsFeatureRequest(expr))  # iterator object
    polygon_lis_overlap.setSelectedFeatures([i.id() for i in it])
    if polygon_lis_overlap.selectedFeatureCount() > 0:
        polygon_lis_overlap = add_layer(polygon_lis_overlap, False)
        print_log("{} bemalingsgebieden met overlap! Zie selectie in layer 'bemalingsgebieden overlap'".format(polygon_lis_overlap.selectedFeatureCount()*2),'w',iface=g_iface)
        for feature in polygon_lis_overlap.selectedFeatures():
            print_log("\toverlap tussen bemalingsgebieden {}".format(feature["ID"]),"i")
    else:
        print_log("geen overlap gevonden tussen bemalingsgebieden", "i")
        QgsMapLayerRegistry.instance().removeMapLayer(polygon_lis_overlap.name())

    return polygon_lis_overlap


def main(iface, layers, workspace, d_velden):
    ''' 1.) Knooppunten exporteren, velden toevoegen.
    # relaties selecteren die naar ander bemalingsgebied afvoeren. (niet volledig binnen 1 bemalingsgebied vallen)
    # knooppunten selecteren die op ander bemalingsgebied afvoeren (op basis van selectie afvoerrelaties)
    # knooppunten koppelen aan bemalingsgebieden / gebieden voorzien van code. (sp.join)
    # eindpunten genereren van afvoerrelatie (line_to_point, select if not intersect with knooppunt)
    # eindpunten voorzien van bemalingsgebied (sp.join)
    # invullen veld LOOST_OP met code bemalingsgebied. '''

    global g_iface, gdb, KNOOPPUNTEN, EINDKNOOPPUNTEN, POLYGON_LIS_OVERLAP, POLYGON_LIS, POLYGON_LIS_SUM, log_dir

    g_iface = iface
    gdb = workspace

    # tussenresultaten
    KNOOPPUNTEN = os.path.join(gdb, "knooppunten.shp")  # begin- en eindpunten van afvoerrelaties (lijn-bestand).
    EINDKNOOPPUNTEN = os.path.join(gdb, "EINDKNOOPPUNTEN.shp")  # Alle knooppunten met daarbij het eindpunt
    POLYGON_LIS_OVERLAP = os.path.join(gdb, "POLYGON_LIS_OVERLAP.shp")  # bestand met gaten.

    # eindresultaat
    POLYGON_LIS = os.path.join(gdb, "POLYGON_LIS.shp")
    POLYGON_LIS_SUM = os.path.join(gdb, "POLYGON_LIS_SUM.shp")

    # laod from settings
    log_dir = settings.log_dir
    ##INP_FIELDS_XLS = settings.INP_FIELDS_XLS
    ##INP_FIELDS_XLS_SHEET = settings.INP_FIELDS_XLS_SHEET
    INP_FIELDS_CSV = settings.INP_FIELDS_CSV

    inp_knooppunten, inp_afvoerrelaties, inp_drinkwater_bag, inp_ve_belasting, inp_plancap, inp_verhard_opp, inp_polygon = layers

    for i, layer in enumerate(layers):
        print_log("input {}:\t{}".format(i, layer.name()), "d")

    print_log("inp_afvoerrelatie = {}".format(inp_afvoerrelaties.name()),"i")

    # inp_polygon kopieren naar lege shapefile met objectid
    inp_polygon = create_new_inp_polygon(inp_polygon)

    # bemalingsgebieden controleren
    controleer_bemalingsgebieden(inp_polygon, inp_knooppunten)

    blokje_log("Knooppunten genereren...","i")
    # genereer knooppunten uit afvoerrelaties
    point_layer = genereer_knooppunten(iface, inp_polygon, inp_afvoerrelaties)

    blokje_log("Knooppunten koppelen aan bemalingsgebieden...","i")
    polygon_lis = koppel_knooppunten_aan_bemalingsgebieden(iface, d_velden, inp_polygon, point_layer, inp_knooppunten)

    ##return None, None
    # ##########################################################################
    # 2.) Graph vullen met LIS [LOOST_OP], onderbemaling bepalen en wegschrijven in [ONTV_VAN]

    blokje_log("Bepaal onderbemaling en aantal keer oppompen...","i")
    l_K_ONTV_VAN = lis2graph(polygon_lis)

    # ##########################################################################
    # 3.) Controleer overlap HOOFDBEMALINGSGEBIEDEN
    blokje_log("Controleer topologie bemalingsgebieden...","i")
    controleer_spjoin(polygon_lis,"count")
    polygon_lis_overlap = controleer_hoofdbemalingsgebieden(polygon_lis)

    # ##########################################################################
    # 4.) Velden overnemen uit Kikker
    blokje_log("Overige velden overnemen uit knooppunten Kikker...","i")
    ##add_field_from_dict_label(polygon_lis, "st1b", d_velden)
    join_field(polygon_lis,inp_knooppunten,"K_BEM_GEB",  "NAAM",        "VAN_KNOOPN", "VAN_KNOOPN")
    join_field(polygon_lis,inp_knooppunten,"K_INST_TOT", "CAP_INST_M",  "VAN_KNOOPN", "VAN_KNOOPN")
    join_field(polygon_lis,inp_knooppunten,"K_BR_ST_M3", "BERGING_M3",  "VAN_KNOOPN", "VAN_KNOOPN")
    join_field(polygon_lis,inp_knooppunten,"K_OSH",      "LAAGSTE_OS",  "VAN_KNOOPN", "VAN_KNOOPN")

    return l_K_ONTV_VAN, inp_polygon