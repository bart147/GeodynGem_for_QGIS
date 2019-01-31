import os
# qgis imports
import processing
from qgis.core import *
from PyQt4.QtCore import QVariant
# custom imports
from utl import blokje_log, print_log, add_field_from_dict, add_field_from_dict_label, join_field, bereken_veld, bereken_veld_label, add_layer, update_datetime, fields_to_uppercase
import settings


def controleer_spjoin_plancap(layer, fld_join_count):
    """Controleer of spjoin geslaagd is (Join_Count moet in principe overal 1 zijn) voor plancap"""
    i_dubbel, i_leeg = 0, 0

    ##layer.startEditing()
    for i, feature in enumerate(layer.getFeatures()):

        JOIN_COUNT = feature[fld_join_count] if feature[fld_join_count] else 0
        PLAN_ID = feature["PLANID"] if feature["PLANID"] else None
        ##print_log("{} - {}".format(PLAN_ID, JOIN_COUNT), "i")
        if JOIN_COUNT >= 2:
            i_dubbel += 1
            print_log("planid '{}' valt in {} bemalingsgebieden!".format(PLAN_ID, int(JOIN_COUNT)), "i", g_iface)
        if JOIN_COUNT == 0:
            i_leeg += 1
    ##layer.commitChanges()

    if i_dubbel == 1: print_log("{} woningbouwplan valt in meerdere hoofdbemalingsgebieden. Let op: dit woningbouwplan wordt dubbel meegeteld! Zie layer 'plancap overlap' (waar veld \"count\" > 1)".format(i_dubbel), "w")
    if i_dubbel > 1: print_log("{} woningbouwplannen vallen in meerdere hoofdbemalingsgebieden. Let op: deze woningbouwplannen worden dubbel meegeteld! Zie layer 'plancap overlap' (waar veld \"count\" > 1)".format(i_dubbel), "w")
    if i_leeg == 1: print_log("{} woningbouwplan valt niet in een hoofdbemalingsgebied\n".format(i_leeg), "i")
    if i_leeg > 1: print_log("{} woningbouwplannen vallen buiten een hoofdbemalingsgebied\n".format(i_leeg), "i")


def vervang_None_door_0_voor_velden_in_lijst(l,layer):
    """Vervang alle None-waarden met 0 voor velden in lijst"""
    blokje_log("Data voorbereiden en berekeningen uitvoeren...","i")
    print_log("Vervang None met 0 voor alle velden in lijst {}...".format(l),"i")
    layer.startEditing()
    for fld in l:
        for f in layer.getFeatures():
            try:
                if str(f[fld]) in ["NULL", "", " ", "nan"]:
                    layer.changeAttributeValue(f.id(), layer.fieldNameIndex(fld), 0)
            except Exception as e:
                print_log("fout bij omzetten None-waarden naar 0 bij veld {}. {}".format(fld, e), "w", g_iface)
    layer.commitChanges()


def bereken_onderbemaling(layer, d_K_ONTV_VAN):
    """bereken onderbemalingen voor SUM_WAARDE, SUM_BLA, etc..
       Maakt selectie op basis van veld [ONTV_VAN] -> VAN_KNOOPN IN ('ZRE-123424', 'ZRE-234')"""
    # sum values op basis van selectie [ONTV_VAN]
    layer.startEditing()
    for feature in layer.getFeatures():
        VAN_KNOOPN = feature["VAN_KNOOPN"]
        ONTV_VAN = d_K_ONTV_VAN.get(VAN_KNOOPN, "") #feature["K_ONTV_VAN"]
        if not str(ONTV_VAN) in ["NULL", ""," "]: # check of sprake is van onderbemaling
            print_log("VAN_KNOOPN {} ontvangt van {}".format(VAN_KNOOPN,ONTV_VAN),"d")
            where_clause = '"VAN_KNOOPN" IN ({})'.format(ONTV_VAN)
            ##where_clause = '"VAN_KNOOPN" = '+"'MERG10'"
            print_log("where_clause = {}".format(where_clause), "d")
            expr = QgsExpression(where_clause)
            it = layer.getFeatures(QgsFeatureRequest(expr))  # iterator object
            layer.setSelectedFeatures([i.id() for i in it])
            ##print_log("sel = {}".format([i.id() for i in it]),"d")
            AW_15_24_O  = sum([float(f["AW_15_24_G"]) for f in layer.selectedFeatures() if str(f["AW_15_24_G"]) not in ["NULL","nan",""," "]])
            AW_25_50_O  = sum([float(f["AW_25_50_G"]) for f in layer.selectedFeatures() if str(f["AW_25_50_G"]) not in ["NULL","nan",""," "]])
            DWR_ONBG    = sum([float(f["DWR_GEBIED"]) for f in layer.selectedFeatures() if str(f["DWR_GEBIED"]) not in ["NULL","nan",""," "]])
            X_WON_ONBG  = sum([float(f["X_WON_GEB"]) for f in layer.selectedFeatures() if str(f["X_WON_GEB"]) not in ["NULL","nan",""," "]])
            X_VE_ONBG   = sum([float(f["X_VE_GEB"]) for f in layer.selectedFeatures() if str(f["X_VE_GEB"]) not in ["NULL","nan",""," "]])
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("AW_15_24_O"), AW_15_24_O)
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("AW_25_50_O"), AW_25_50_O)
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("DWR_ONBG"), DWR_ONBG)
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("X_WON_ONBG"), X_WON_ONBG)
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("X_VE_ONBG"), X_VE_ONBG)
    layer.commitChanges()
    layer.setSelectedFeatures([])
    print_log("Onderbemalingen succesvol berekend voor Plancap, drinkwater, woningen en ve's", "i")


def bereken_onderbemaling2(layer, d_K_ONTV_VAN_n1):
    """bereken onderbemalingen voor SUM_WAARDE..
       Maakt selectie op basis van dict ONTV_VAN 1 niveau diep -> VAN_KNOOPN IN ('ZRE-123424', 'ZRE-234')"""

    layer.startEditing()
    for feature in layer.getFeatures():
        VAN_KNOOPN = feature["VAN_KNOOPN"]
        ONTV_VAN = d_K_ONTV_VAN_n1.get(VAN_KNOOPN,"") #feature["K_ONTV_VAN"]
        if not str(ONTV_VAN) in ["NULL", "", " "]:  # check of sprake is van onderbemaling
            print_log("VAN_KNOOPN = {} ontvangt van {}".format(VAN_KNOOPN, ONTV_VAN), "i")
            where_clause = '"VAN_KNOOPN" IN ({})'.format(ONTV_VAN)
            ##where_clause = '"VAN_KNOOPN" = '+"'MERG10'"
            print_log("where_clause = {}".format(where_clause), "i")
            expr = QgsExpression(where_clause)
            it = layer.getFeatures(QgsFeatureRequest(expr))  # iterator object
            layer.setSelectedFeatures([i.id() for i in it])
            K_INST_TOT_O = sum([float(f["K_INST_TOT"]) for f in layer.selectedFeatures() if
                              str(f["K_INST_TOT"]) not in ["NULL", "nan", "", " "]])    # K_INST_TOT_O = sum(K_INST_TOT)
            POC_O_M3_O = sum([float(f["POC_O_M3_G"]) for f in layer.selectedFeatures() if
                              str(f["POC_O_M3_G"]) not in ["NULL", "nan", "", " "]])    # POC_O_M3_O = sum(POC_O_M3_G)
            print_log("sum IN_DWA_POC = {}".format(K_INST_TOT_O), "d")
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("IN_DWA_POC"), K_INST_TOT_O)
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("POC_O_M3_O"), POC_O_M3_O)
    layer.commitChanges()
    layer.setSelectedFeatures([])
    print_log("Onderbemalingen succesvol berekend voor POC ontwerp en POC beschikbaar", "i")


def spjoin_bronbestanden_aan_bemalingsgebieden(polygon_lis, inp_drinkwater_bag, inp_ve_belasting, inp_plancap, inp_polygon,
                                                   PLANCAP_OVERLAP, STATS_DRINKWATER, STATS_VE, STATS_PLANCAP):
    # joining DRINKWATER_BAG to POLYGONS
    print_log("spatialjoin DRINKWATER_BAG to POLYGONS...","i")
    processing.runalg("qgis:joinattributesbylocation", inp_polygon, inp_drinkwater_bag, u'intersects', 0, 1, 'sum', 1, STATS_DRINKWATER)
    stats_drinkwater = QgsVectorLayer(STATS_DRINKWATER, "stats_drinkwater", "ogr")
    stats_drinkwater = add_layer(stats_drinkwater)

    # extra stapje om om te reken van liter/hr naar m3/hr voor part. en zakelijk drinkwater in STAT-tabel.
    add_field_from_dict_label(stats_drinkwater, "stap2tmp", d_velden_tmp)
    bereken_veld(stats_drinkwater, "SUMPAR_M3U", d_velden_tmp)
    bereken_veld(stats_drinkwater, "SUMZAK_M3U", d_velden_tmp)

    # check for overlap between PLANCAP_RIGO and inp_polygon
    print_log("spatialjoin PLANCAP_RIGO to POLYGONS...","i")
    processing.runalg("qgis:joinattributesbylocation", inp_plancap, inp_polygon, u'intersects', 0, 1, 'sum', 1, PLANCAP_OVERLAP)
    plancap_overlap = QgsVectorLayer(PLANCAP_OVERLAP, "plancap_overlap", "ogr")
    plancap_overlap = add_layer(plancap_overlap, False)
    controleer_spjoin_plancap(plancap_overlap, "count")

    # joining PLANCAP_RIGO to POLYGONS
    processing.runalg("qgis:joinattributesbylocation", inp_polygon, inp_plancap, u'intersects', 0, 1, 'sum', 1, STATS_PLANCAP)
    stats_plancap = QgsVectorLayer(STATS_PLANCAP, "stats_plancap", "ogr")
    stats_plancap = add_layer(stats_plancap)

    # joining VE to POLYGONS
    if inp_ve_belasting.name() == "no data":
        stats_ve = None
        print_log("'no data' geselecteerd als input voor vervuilingseenheden. Berekeningen met VE's worden overgeslagen", "w", g_iface)
    else:
        print_log("spatialjoin VE_BELASTING to POLYGONS...","i")
        processing.runalg("qgis:joinattributesbylocation", inp_polygon, inp_ve_belasting, u'intersects', 0, 1, 'sum', 1, STATS_VE)
        stats_ve = QgsVectorLayer(STATS_VE, "stats_ve", "ogr")
        stats_ve = add_layer(stats_ve)

    return stats_drinkwater, stats_ve, stats_plancap


def bepaal_verhard_oppervlak(polygon_lis, inp_verhard_opp, VERHARD_OPP_INTERSECT):

    layers = [polygon_lis]
    if inp_verhard_opp.name() == "no data":
        verhard_opp_intersect = None
        print_log("'no data' geselecteerd als input voor verhard oppervlak opgegeven. Berekeningen verhard opp. worden overgeslagen", "w", g_iface)
    else:
        print_log("Intersect {}...".format(";".join([polygon_lis.name(),inp_verhard_opp.name()])),"i")
        # eerst totaal verhard opp (ha) bepalen per bemalingsgebied
        if not INP_SKIP_SPJOIN:
            processing.runalg("saga:intersect", inp_verhard_opp, polygon_lis, True, VERHARD_OPP_INTERSECT)
        verhard_opp_intersect = QgsVectorLayer(VERHARD_OPP_INTERSECT, "verhard_opp_intersect", "ogr")
        verhard_opp_intersect = add_layer(verhard_opp_intersect)
        layers.append(verhard_opp_intersect)
        add_field_from_dict(verhard_opp_intersect, "HA_BEM_G", d_velden_tmp)

    # opp ha berekenen
    for layer in layers:
        print_log("opp ha berekenen voor {}...".format(layer.name()),"i")
        ##d = QgsDistanceArea()
        provider = layer.dataProvider()
        updateMap = {}
        fieldIdx = provider.fields().indexFromName('HA_BEM_G')

        for f in provider.getFeatures():
            opp_ha = f.geometry().area()/10000
            ##opp_ha = d.measurePolygon(f.geometry().asPolygon()[0])/10000
            updateMap[f.id()] = {fieldIdx: opp_ha}

        provider.changeAttributeValues(updateMap)

    # toevoegen velden voor PI's
    ##add_field_from_dict_label(polygon_lis, "st3a", d_velden)

    if verhard_opp_intersect == None:
        return      # berekeningen overslaan

    print_log("bereken stats totaal opp ...", "i")
    STATS_VERHARD_OPP_TOT = os.path.join(gdb, "STATS_VERHARD_OPP_TOT.csv")
    if not INP_SKIP_SPJOIN:
        processing.runalg("qgis:statisticsbycategories", VERHARD_OPP_INTERSECT, "HA_BEM_G", "VAN_KNOOPN", STATS_VERHARD_OPP_TOT)
    stats_verh_opp_tot = QgsVectorLayer(STATS_VERHARD_OPP_TOT, "stats_verh_opp_totaal", "ogr")
    stats_verh_opp_tot = add_layer(stats_verh_opp_tot)

    # overhalen verhard opp (ha) naar eindresultaat
    join_field(polygon_lis, stats_verh_opp_tot, "HA_VER_G", "sum", "VAN_KNOOPN", "category")

    # per categorie verhard opp (ha) bepalen per bemalingsgebied
    for aansluiting in ["GEM", "HWA", "NAG", "OBK", "VGS"]:
        STAT_NAME = os.path.join(gdb, "{}_{}.csv".format("STATS_VERHARD_OPP", aansluiting))
        where_clause = "\"AANGESL_OP\" = '{}'".format(aansluiting)
        expr = QgsExpression(where_clause)
        it = verhard_opp_intersect.getFeatures(QgsFeatureRequest(expr))
        verhard_opp_intersect.setSelectedFeatures([i.id() for i in it])
        if verhard_opp_intersect.selectedFeatureCount() == 0:
            print_log("geen aansluiting op '{}' gevonden voor verhard opp".format(aansluiting),"w")
            continue
        processing.runalg("qgis:statisticsbycategories", verhard_opp_intersect, "HA_BEM_G", "VAN_KNOOPN", STAT_NAME)
        layer = QgsVectorLayer(STAT_NAME, "{}_{}".format("stats_verh_opp", aansluiting), "ogr")
        layer = add_layer(layer)

        # velden overhalen naar eindresultaat en PI berekenen
        fld_ha = "HA_{}_G".format(aansluiting)
        join_field(polygon_lis, layer, fld_ha, "sum", "VAN_KNOOPN", "category")
        # fld_pi = "PI_{}_G".format(aansluiting)
        # bereken_veld(polygon_lis, fld_pi, d_velden)


def setColumnVisibility( layer, columnName, visible ):
    config = layer.attributeTableConfig()
    columns = config.columns()
    for column in columns:
        if column.name == columnName:
            column.hidden = not visible
            break
    config.setColumns( columns )
    layer.setAttributeTableConfig( config )


def main(iface, layers, workspace, d_velden_, l_K_ONTV_VAN, inp_polygon):
    """Hoofdmenu:
    1.) Kopie maken INPUT_POLYGON_LIS
    2.) Spatial joins tussen POLYGON_LIS en de externe gegevens bronnen.
    3.) Velden toevoegen en gegevens overnemen
    4.) Bereken onderbemaling voor DRINKWATER, PLANCAP en VE's
    5.) alle None vervangen door 0
    6.) berekeningen uitvoeren
    7.) resultaat omzetten naar template (als "template" bestaat)
    8.) add results to map
    """
    global g_iface, INP_SKIP_SPJOIN, gdb, l_src_None_naar_0_omzetten, d_velden_tmp, d_velden
    d_velden = d_velden_
    g_iface = iface

    INP_SKIP_SPJOIN = False

    # laod from settings
    gdb = workspace
    l_src_None_naar_0_omzetten = settings.l_fld_None_naar_0_omzetten  # velden waarvan waardes worden omgezet van None naar 0
    d_velden_tmp = settings.d_velden_tmp  # tijdelijke velden

    # layers
    inp_knooppunten, inp_afvoerrelaties, inp_drinkwater_bag, inp_ve_belasting, inp_plancap, inp_verhard_opp, old_inp_polygon = layers
    for i, layer in enumerate(layers):
        print_log("input {}:\t{}".format(i, layer.name()), "d")

    # tussenresultaten
    EINDRESULTAAT           = os.path.join(gdb, "eindresultaat.shp")
    POLYGON_LIS             = os.path.join(gdb, "POLYGON_LIS.shp")
    DRINKWATER_POLYGON_LIS  = os.path.join(gdb, "SpJoin_DRINKWATER2POLYGON_LIS.shp")
    PLANCAP_POLYGON_LIS     = os.path.join(gdb, "SpJoin_PLANCAP2POLYGON_LIS.shp")
    VE_POLYGON_LIS          = os.path.join(gdb, "SpJoin_VE2POLYGON_LIS.shp")
    PLANCAP_OVERLAP         = os.path.join(gdb, "PLANCAP_OVERLAP.shp")
    STATS_DRINKWATER        = os.path.join(gdb, "STATS_DRINKWATER.shp")
    STATS_PLANCAP           = os.path.join(gdb, "STATS_PLANCAP.shp")
    STATS_VE                = os.path.join(gdb, "STATS_VE.shp")
    EXP_VERHARD_OPP         = os.path.join(gdb, "EXP_VERHARD_OPP.shp")
    VERHARD_OPP_INTERSECT   = os.path.join(gdb, "VERHARD_OPP_INTERSECT.shp")
    STATS_VERHARD_OPP       = os.path.join(gdb, "STATS_VERHARD_OPP.shp")
    INP_POLYGON_COPY        = os.path.join(gdb, "inp_polygon_copy.shp")


    # ##########################################################################
    # 1.) export input INP_POLYGON_LIS to result POLYGON_LIS
    tussenresultaat = QgsVectorLayer(POLYGON_LIS, "tussenresultaat", "ogr")
    if EINDRESULTAAT:
        QgsVectorFileWriter.deleteShapeFile(EINDRESULTAAT)
    QgsVectorFileWriter.writeAsVectorFormat(tussenresultaat, EINDRESULTAAT, "utf-8", tussenresultaat.crs(), "ESRI Shapefile")
    ##QgsVectorFileWriter.writeAsVectorFormat(tussenresultaat, os.path.join(gdb,"eindresultaat"), "utf-8", tussenresultaat.crs(), "SQLite", False, None ,["SPATIALITE=YES"])

    # ##########################
    ##EINDRESULTAAT = os.path.join(gdb,'eindresultaat.sqlite')
    polygon_lis = QgsVectorLayer(EINDRESULTAAT, "eindresultaat", "ogr")
    polygon_lis = add_layer(polygon_lis)

    fields_to_uppercase(polygon_lis)

    # ##########################################################################
    # 2.) Velden toevoegen en gegevens overnemen
    add_field_from_dict_label(polygon_lis, "st2a", d_velden)
    # copy VAN_KNOOPN -> K_KNP_NR
    bereken_veld(polygon_lis, "K_KNP_NR", {"K_KNP_NR":{"expression":"[VAN_KNOOPN]"}})
    # overige velden kikker toevoegen (uitgegrijst omdat nog geen geschikt bronveld is gevonden in Kikker #
    ##join_field(polygon_lis, inp_knooppunten, "K_BERG_VL", "BERGV_KNP_", "VAN_KNOOPN", "VAN_KNOOPN") # Verloren berging stelsel (m3)
    ##join_field(polygon_lis, inp_knooppunten, "K_BR_RZ_M3", "BERG_STR_M", "VAN_KNOOPN", "VAN_KNOOPN")  # Berging randvoorziening (G) (m3)

    # ##########################################################################
    # 3.) Spatial joins tussen polygon_lis en de externe gegevens bronnen
    if INP_SKIP_SPJOIN:
        blokje_log("Skip SpatialJoin met externe inputs en gebruik bestaande STAT-tabellen.","i")
        stats_drinkwater    = QgsVectorLayer(STATS_DRINKWATER, "stats_drinkwater", "ogr")
        stats_ve            = QgsVectorLayer(STATS_VE, "stats_ve", "ogr")
        stats_plancap       = QgsVectorLayer(STATS_PLANCAP, "stats_plancap", "ogr")
        stats_drinkwater    = add_layer(stats_drinkwater)
        stats_ve            = add_layer(stats_ve)
        stats_plancap       = add_layer(stats_plancap)
        # for layer in [stats_drinkwater, stats_ve, stats_plancap]:
        #     layer = add_layer(layer)
    else:
        blokje_log("Start SpatialJoin externe bronnen met hoofdbemalingsgebieden... (1 tot 5 minuten)","i")
        stats_drinkwater, stats_ve, stats_plancap = spjoin_bronbestanden_aan_bemalingsgebieden(
                polygon_lis, inp_drinkwater_bag, inp_ve_belasting, inp_plancap, inp_polygon,
                PLANCAP_OVERLAP, STATS_DRINKWATER, STATS_VE, STATS_PLANCAP)

    blokje_log("Velden toevoegen en voorbereiden voor berekening onderbemaling...", "i")

    # join stat_fields to polygon_lis
    join_field(polygon_lis, stats_drinkwater, "PAR_RESULT", "SUMPAR_M3U", "OBJECTID", "OBJECTID")
    join_field(polygon_lis, stats_drinkwater, "ZAK_RESULT", "SUMZAK_M3U", "OBJECTID", "OBJECTID")
    join_field(polygon_lis, stats_drinkwater, "X_WON_GEB", "count", "OBJECTID", "OBJECTID")
    join_field(polygon_lis, stats_plancap, "AW_15_24_G", "sumExtra_A", "OBJECTID", "OBJECTID") # SUM_Extra_AFW_2015_tm_2024
    join_field(polygon_lis, stats_plancap, "AW_25_50_G", "sumExtra_1", "OBJECTID", "OBJECTID") # SUM_Extra_AFW_2025_tm_2050
    if stats_ve:
        join_field(polygon_lis, stats_ve, "X_VE_GEB", "sumGRONDSL", "OBJECTID", "OBJECTID")

    # bereken drinkwater per gebied (input voor onderbemalingen) en LEDIG_U (ledigingstijd)
    bereken_veld_label(polygon_lis, "02_ber", d_velden)

    # ##########################################################################
    # 4.) Bereken onderbemaling voor DRINKWATER en PLANCAP en VE's
    blokje_log("bereken onderbemalingen voor drinkwater, plancap en ve's...","i")
    bereken_onderbemaling(polygon_lis, l_K_ONTV_VAN[0])

    vervang_None_door_0_voor_velden_in_lijst(l_src_None_naar_0_omzetten, polygon_lis)

    # ##########################################################################
    # 6.) berekeningen uitvoeren
    # bereken dwa prognose & drinkwater per gebied
    # "bereken": "b2a"
    bereken_veld_label(polygon_lis, "04_ber", d_velden)
    bereken_veld_label(polygon_lis, "04a_ber", d_velden)

    # Vergelijk geschat en gemeten zonder
    # "bereken": "b2b"
    bereken_veld_label(polygon_lis, "05_ber", d_velden)

    # bereken verhard opp
    blokje_log("Bepaal verhard oppervlak binnen bemalingsgebieden...","i")
    bepaal_verhard_oppervlak(polygon_lis, inp_verhard_opp, VERHARD_OPP_INTERSECT)

    vervang_None_door_0_voor_velden_in_lijst(
        ["HA_GEM_G", "HA_VGS_G", "HA_HWA_G","HA_OPW_G", "HA_NAG_G", "HA_OBK_G"],
        polygon_lis)

    # bereken velden afhankelijk van verhard opp
    bereken_veld_label(polygon_lis, '07_ber', d_velden)
    bereken_veld_label(polygon_lis, '08_ber', d_velden)

    # bepaal onderbemaling2 afhankelijk van verhard opp
    blokje_log("bereken onderbemalingen voor pompovercapaciteit ontwerp en berekend...", "i")
    bereken_onderbemaling2(polygon_lis, l_K_ONTV_VAN[1])

    vervang_None_door_0_voor_velden_in_lijst(
            ##["POC_B_M3_O", "POC_O_M3_O","POC_B_M3_G", "POC_O_M3_G"], polygon_lis)
            ["POC_O_M3_O", "POC_O_M3_G", "IN_DWA_POC"], polygon_lis)
    bereken_veld_label(polygon_lis, '10_ber', d_velden)
    bereken_veld_label(polygon_lis, '11_ber', d_velden)

    # update_datetime UPDATED
    update_datetime(polygon_lis, "UPDATED")

    # delete fields
    del_fld_names = ['BEGIN_EIND', 'VAN_KNOOPN', 'count']
    del_fld_index = [polygon_lis.fieldNameIndex(fld) for fld in del_fld_names if polygon_lis.fieldNameIndex(fld) != -1]
    print_log("deleting fields {} with index {}".format(del_fld_names, del_fld_index))
    polygon_lis.dataProvider().deleteAttributes(del_fld_index)
    polygon_lis.updateFields()

    # add field aliasses
    for fld in d_velden:
        index = polygon_lis.fieldNameIndex(fld)
        if index != -1:
            try:
                print_log("update {} with alias '{}'".format(fld, d_velden[fld]["field_alias"]), "d")
            except Exception as e:
                print_log(e, "d")  # UnicodeEncodeError?...
            polygon_lis.addAttributeAlias(index, d_velden[fld]["field_alias"])

