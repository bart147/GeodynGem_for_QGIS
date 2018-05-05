import os
# qgis imports
import processing
from qgis.core import *
# custom imports
from utl import blokje_log, print_log, add_field_from_dict, add_field_from_dict_label, join_field, bereken_veld, bereken_veld_label, add_layer
import settings

def bepaal_b_VIEW(fc,wildcard):
    """Bepaal of extra gemaal bron (Spoc_views) gebruikt is in stap 1.
       Dat gebeurt door te controleren of de extra velden zijn aangemaakt"""
    if len(arcpy.ListFields(fc,wildcard))>0:
        return True
    else:
        print_log("geen [{}] gevonden in {}".format(wildcard,fc),"i")
        return False


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
            print_log("planid '{}' valt in {} bemalingsgebieden!".format(PLAN_ID, JOIN_COUNT), "w", g_iface)
        if JOIN_COUNT == 0:
            i_leeg += 1
    ##layer.commitChanges()

    if i_dubbel == 1: print_log("\n{} plancap valt in meerdere hoofdbemalingsgebieden!".format(i_dubbel), "w")
    if i_dubbel > 1: print_log("\n{} plancaps vallen in meerdere hoofdbemalingsgebieden!".format(i_dubbel), "w")
    if i_leeg == 1: print_log("{} plancaps valt niet in een hoofdbemalingsgebied\n".format(i_leeg), "w")
    if i_leeg > 1: print_log("{} plancaps vallen niet in een hoofdbemalingsgebied\n".format(i_leeg), "w")


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


def bereken_onderbemaling(layer):
    """bereken onderbemalingen voor SUM_WAARDE, SUM_BLA, etc..
       Maakt selectie op basis van veld [ONTV_VAN] -> VAN_KNOOPN IN ('ZRE-123424', 'ZRE-234')"""
    # sum values op basis van selectie [ONTV_VAN]
    layer.startEditing()
    for feature in layer.getFeatures():
        VAN_KNOOPN = feature["VAN_KNOOPN"]
        ONTV_VAN = feature["K_ONTV_VAN"]
        if not str(ONTV_VAN) in ["NULL", ""," "]: # check of sprake is van onderbemaling
            print_log("K_ONTV_VAN = {}".format(ONTV_VAN),"i")
            where_clause = '"VAN_KNOOPN" IN ({})'.format(ONTV_VAN)
            ##where_clause = '"VAN_KNOOPN" = '+"'MERG10'"
            print_log("where_clause = {}".format(where_clause), "i")
            expr = QgsExpression(where_clause)
            it = layer.getFeatures(QgsFeatureRequest(expr))  # iterator object
            layer.setSelectedFeatures([i.id() for i in it])
            print_log("sel = {}".format([i.id() for i in it]),"i")
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

    # with arcpy.da.UpdateCursor(fc, (update_fields)) as cursor:
    #     for row in cursor:
    #         VAN_KNOOPN, ONTV_VAN = row[0], row[1]
    #         if not ONTV_VAN in [None,""," "]: # check of sprake is van onderbemaling
    #             where_clause = "VAN_KNOOPN IN ({})".format(ONTV_VAN)
    #             row[3] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["AW_15_24_G"],where_clause) if r[0] != None])    # AW_15_24_O = sum(AW_15_24_G)
    #             row[5] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["AW_25_50_G"],where_clause) if r[0] != None])    # AW_25_50_O = sum(AW_25_50_G)
    #             row[7] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["DWR_GEBIED"],where_clause) if r[0] != None])    # DWR_ONBG = sum(DWR_GEBIED)
    #             row[9] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["X_WON_GEB"],where_clause) if r[0] != None])     # X_WON_ONBG = sum(X_WON_GEB)
    #             row[11]= sum([r[0] for r in arcpy.da.SearchCursor(fc,["X_VE_GEB"],where_clause) if r[0] != None])     # X_VE_ONBG = sum(X_VE_GEB)
    #             cursor.updateRow(row)
    # del cursor, row
    # print_log("Onderbemalingen succesvol berekend voor Plancap, drinkwater, woningen en ve's", "i")


def bereken_onderbemaling2(layer):
    """bereken onderbemalingen voor SUM_WAARDE, SUM_BLA, etc..
       Maakt selectie op basis van veld [ONTV_VAN] -> VAN_KNOOPN IN ('ZRE-123424', 'ZRE-234')"""
    # sum values op basis van selectie [ONTV_VAN]

    layer.startEditing()
    for feature in layer.getFeatures():
        VAN_KNOOPN = feature["VAN_KNOOPN"]
        ONTV_VAN = feature["K_ONTV_VAN"]
        if not str(ONTV_VAN) in ["NULL", "", " "]:  # check of sprake is van onderbemaling
            print_log("K_ONTV_VAN = {}".format(ONTV_VAN), "i")
            where_clause = '"VAN_KNOOPN" IN ({})'.format(ONTV_VAN)
            ##where_clause = '"VAN_KNOOPN" = '+"'MERG10'"
            print_log("where_clause = {}".format(where_clause), "i")
            expr = QgsExpression(where_clause)
            it = layer.getFeatures(QgsFeatureRequest(expr))  # iterator object
            layer.setSelectedFeatures([i.id() for i in it])
            print_log("sel = {}".format([i.id() for i in it]), "i")
            POC_B_M3_O = sum([float(f["POC_B_M3_G"]) for f in layer.selectedFeatures() if
                              str(f["POC_B_M3_G"]) not in ["NULL", "nan", "", " "]])    # POC_B_M3_O = sum(POC_B_M3_G)
            POC_O_M3_O = sum([float(f["POC_O_M3_G"]) for f in layer.selectedFeatures() if
                              str(f["POC_O_M3_G"]) not in ["NULL", "nan", "", " "]])    # POC_O_M3_O = sum(POC_O_M3_G)

            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("POC_B_M3_O"), POC_B_M3_O)
            layer.changeAttributeValue(feature.id(), layer.fieldNameIndex("POC_O_M3_O"), POC_O_M3_O)
    layer.commitChanges()
    layer.setSelectedFeatures([])
    print_log("Onderbemalingen succesvol berekend voor POC ontwerp en POC beschikbaar", "i")


    # update_fields = ["VAN_KNOOPN",  # row[0]
    #                  "K_ONTV_VAN",  # row[1]
    #                  "POC_B_M3_G",  # row[2]
    #                  "POC_B_M3_O",  # row[3]
    #                  "POC_O_M3_G",  # row[4]
    #                  "POC_O_M3_O",  # row[5]
    #                  ]
    #
    # with arcpy.da.UpdateCursor(fc, (update_fields)) as cursor:
    #     for row in cursor:
    #         VAN_KNOOPN, ONTV_VAN = row[0], row[1]
    #         if not ONTV_VAN in [None,""," "]: # check of sprake is van onderbemaling
    #             where_clause = "VAN_KNOOPN IN ({})".format(ONTV_VAN)
    #             row[3] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["POC_B_M3_G"],where_clause) if r[0] != None])    # POC_B_M3_O = sum(POC_B_M3_G)
    #             row[5] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["POC_O_M3_G"],where_clause) if r[0] != None])    # POC_O_M3_O = sum(POC_O_M3_G)
    #             cursor.updateRow(row)
    # del cursor, row
    # print_log("Onderbemalingen succesvol berekend voor POC ontwerp en POC beschikbaar", "i")


def spjoin_bronbestanden_aan_bemalingsgebieden(polygon_lis, inp_drinkwater_bag, inp_ve_belasting, inp_plancap, inp_polygon,
                                                   PLANCAP_OVERLAP, STATS_DRINKWATER, STATS_VE, STATS_PLANCAP):
    # joining DRINKWATER_BAG to POLYGONS
    print_log("spatialjoin DRINKWATER_BAG to POLYGONS...","i")
    processing.runalg("qgis:joinattributesbylocation", inp_polygon, inp_drinkwater_bag, u'intersects', 0, 1, 'sum', 1, STATS_DRINKWATER)
    stats_drinkwater = QgsVectorLayer(STATS_DRINKWATER, "stats_drinkwater", "ogr")
    add_layer(stats_drinkwater)

    # extra stapje om om te reken van liter/hr naar m3/hr voor part. en zakelijk drinkwater in STAT-tabel.
    add_field_from_dict_label(stats_drinkwater, "stap2tmp", d_velden_tmp)
    bereken_veld(stats_drinkwater, "SUMPAR_M3U", d_velden_tmp)
    bereken_veld(stats_drinkwater, "SUMZAK_M3U", d_velden_tmp)

    # check for overlap between PLANCAP_RIGO and inp_polygon
    print_log("spatialjoin PLANCAP_RIGO to POLYGONS...","i")
    processing.runalg("qgis:joinattributesbylocation", inp_plancap, inp_polygon, u'intersects', 0, 1, 'sum', 1, PLANCAP_OVERLAP)
    plancap_overlap = QgsVectorLayer(PLANCAP_OVERLAP, "plancap_overlap", "ogr")
    add_layer(plancap_overlap)
    controleer_spjoin_plancap(plancap_overlap, "count")

    # joining PLANCAP_RIGO to POLYGONS
    processing.runalg("qgis:joinattributesbylocation", inp_polygon, inp_plancap, u'intersects', 0, 1, 'sum', 1, STATS_PLANCAP)
    stats_plancap = QgsVectorLayer(STATS_PLANCAP, "stats_plancap", "ogr")
    add_layer(stats_plancap)

    # joining VE to POLYGONS
    print_log("spatialjoin VE_BELASTING to POLYGONS...","i")
    processing.runalg("qgis:joinattributesbylocation", inp_polygon, inp_ve_belasting, u'intersects', 0, 1, 'sum', 1, STATS_VE)
    stats_ve = QgsVectorLayer(STATS_VE, "stats_ve", "ogr")
    add_layer(stats_ve)

    return stats_drinkwater, stats_ve, stats_plancap

def bepaal_verhard_oppervlak(polygon_lis, inp_verhard_opp, VERHARD_OPP_INTERSECT):
    print_log("Intersect {}...".format(";".join([polygon_lis.name(),inp_verhard_opp.name()])),"i")

    # eerst totaal verhard opp (ha) bepalen per bemalingsgebied
    if not INP_SKIP_SPJOIN:
        processing.runalg("saga:intersect", inp_verhard_opp, polygon_lis, True, VERHARD_OPP_INTERSECT)
    verhard_opp_intersect = QgsVectorLayer(VERHARD_OPP_INTERSECT, "verhard_opp_intersect", "ogr")
    add_layer(verhard_opp_intersect)
    add_field_from_dict(verhard_opp_intersect, "HA_BEM_G", d_velden_tmp)

    # opp ha berekenen
    for layer in [verhard_opp_intersect, polygon_lis]:
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

    print_log("bereken stats totaal opp ...", "i")
    STATS_VERHARD_OPP_TOT = os.path.join(gdb, "STATS_VERHARD_OPP_TOT.csv")
    if not INP_SKIP_SPJOIN:
        processing.runalg("qgis:statisticsbycategories", VERHARD_OPP_INTERSECT, "HA_BEM_G", "VAN_KNOOPN", STATS_VERHARD_OPP_TOT)
    stats_verh_opp_tot = QgsVectorLayer(STATS_VERHARD_OPP_TOT, "stats_verh_opp_totaal", "ogr")
    add_layer(stats_verh_opp_tot)

    # toevoegen velden voor PI's
    add_field_from_dict_label(polygon_lis, "st3a", d_velden)

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
        add_layer(layer)

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


def main(iface, layers, workspace, d_velden_):
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
    inp_knooppunten, inp_afvoerrelaties, inp_drinkwater_bag, inp_ve_belasting, inp_plancap, inp_verhard_opp, inp_polygon = layers
    for layer in layers:
        print_log(layer.name(), "i")

    # tussenresultaten
    POLYGON_LIS             = os.path.join(gdb, "eindresultaat.shp")
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

    # ##########################################################################
    # 1.) export input INP_POLYGON_LIS to result POLYGON_LIS
    tussenresultaat = QgsVectorLayer(os.path.join(gdb,"POLYGON_LIS.shp"), "tussenresultaat", "ogr")
    QgsVectorFileWriter.writeAsVectorFormat(tussenresultaat, POLYGON_LIS, "utf-8", None, "ESRI Shapefile")
    polygon_lis = QgsVectorLayer(POLYGON_LIS, "eindresultaat", "ogr")
    add_layer(polygon_lis)

    # ##########################################################################
    # 2.) Velden toevoegen en gegevens overnemen
    add_field_from_dict_label(polygon_lis, "st2a", d_velden)

    # ##########################################################################
    # 3.) Spatial joins tussen POLYGON_LIS en de externe gegevens bronnen
    if INP_SKIP_SPJOIN:
        blokje_log("Skip SpatialJoin met externe inputs en gebruik bestaande STAT-tabellen.","i")
        stats_drinkwater    = QgsVectorLayer(STATS_DRINKWATER, "stats_drinkwater", "ogr")
        stats_ve            = QgsVectorLayer(STATS_VE, "stats_ve", "ogr")
        stats_plancap       = QgsVectorLayer(STATS_PLANCAP, "stats_plancap", "ogr")
        for layer in [stats_drinkwater, stats_ve, stats_plancap]:
            add_layer(layer)
    else:
        blokje_log("Start SpatialJoin externe bronnen met hoofdbemalingsgebieden... (5 tot 25 minuten)","i")
        stats_drinkwater, stats_ve, stats_plancap = spjoin_bronbestanden_aan_bemalingsgebieden(
                polygon_lis, inp_drinkwater_bag, inp_ve_belasting, inp_plancap, inp_polygon,
                PLANCAP_OVERLAP, STATS_DRINKWATER, STATS_VE, STATS_PLANCAP)

    blokje_log("Velden toevoegen en voorbereiden voor berekening onderbemaling...", "i")

    # join stat_fields to POLYGON_LIS
    join_field(polygon_lis, stats_drinkwater, "PAR_RESULT", "SUMPAR_M3U", "OBJECTID", "OBJECTID")
    join_field(polygon_lis, stats_drinkwater, "ZAK_RESULT", "SUMZAK_M3U", "OBJECTID", "OBJECTID")
    join_field(polygon_lis, stats_drinkwater, "X_WON_GEB", "count", "OBJECTID", "OBJECTID")
    join_field(polygon_lis, stats_plancap, "AW_15_24_G", "sumExtra_A", "OBJECTID", "OBJECTID") # SUM_Extra_AFW_2015_tm_2024
    join_field(polygon_lis, stats_plancap, "AW_25_50_G", "sumExtra_1", "OBJECTID", "OBJECTID") # SUM_Extra_AFW_2025_tm_2050
    join_field(polygon_lis, stats_ve, "X_VE_GEB", "sumGRONDSL", "OBJECTID", "OBJECTID")

    # bereken drinkwater per gebied (input voor onderbemalingen)
    bereken_veld(polygon_lis, "DWR_GEBIED", d_velden)

    # ##########################################################################
    # 4.) Bereken onderbemaling voor DRINKWATER en PLANCAP en VE's
    blokje_log("bereken onderbemalingen voor drinkwater, plancap en ve's...","i")
    bereken_onderbemaling(polygon_lis)

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
    bereken_onderbemaling2(polygon_lis)
    vervang_None_door_0_voor_velden_in_lijst(
            ["POC_B_M3_O", "POC_O_M3_O","POC_B_M3_G", "POC_O_M3_G"], polygon_lis)
    bereken_veld_label(polygon_lis, '10_ber', d_velden)
    bereken_veld_label(polygon_lis, '11_ber', d_velden)
