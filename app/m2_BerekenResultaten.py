
import sys, os, logging
from datetime import datetime
import arcpy

# importeer utilities
from utl import start_timer, end_timer, blokje_log, print_log, add_field_from_dict, add_field_from_dict_label, fld_exists, join_field, bereken_veld, get_d_velden, bereken_veld_label

# importeer settings
import settings


def bepaal_b_VIEW(fc,wildcard):
    """Bepaal of extra gemaal bron (Spoc_views) gebruikt is in stap 1.
       Dat gebeurt door te controleren of de extra velden zijn aangemaakt"""
    if len(arcpy.ListFields(fc,wildcard))>0:
        return True
    else:
        print_log("geen [{}] gevonden in {}".format(wildcard,fc),"i")
        return False

def controleer_spjoin_plancap(fc):
    """Controleer of spjoin geslaagd is (Join_Count moet in principe overal 1 zijn) voor plancap"""
    i_dubbel, i_leeg, i_None = 0, 0, 0
    with arcpy.da.SearchCursor(fc, (["OID@","VAN_KNOOPN","Join_Count_1"])) as cursor: # 'Join_Count' is overblijfsel van spjoin LIS met POLYGONS, vandaar '_1'.
        for row in cursor:
            OID, VAN_KNOOPN, JOIN_COUNT = row
            if JOIN_COUNT >= 2:
                i_dubbel += 1
            if JOIN_COUNT == 0:
                i_leeg += 1
    del cursor, row
    if i_dubbel > 0: print_log("\n{} plancaps vallen in meerdere hoofdbemalingsgebieden!".format(i_dubbel),"w")
    if i_leeg > 0: print_log("{} plancaps vallen niet in een hoofdbemalingsgebied\n".format(i_leeg),"w")

def vervang_None_door_0_voor_velden_in_lijst(l,POLYGON_LIS):
    """Vervang alle None-waarden met 0 voor velden in lijst"""
    blokje_log("Data voorbereiden en berekeningen uitvoeren...","i")
    print_log("Vervang None met 0 voor alle velden in lijst {}...".format(l),"i")
    l_fields = [fld.name for fld in arcpy.ListFields(POLYGON_LIS)]
    for fld in l:
        if fld in l_fields: #indien veld bestaat...
            with arcpy.da.UpdateCursor(POLYGON_LIS, ([fld])) as cursor:
                for row in cursor:
                    if row[0] == None:
                        row[0] = 0
                        cursor.updateRow(row)
                del cursor, row
        else:
            print_log("veld {} niet gevonden! Kan None-waardes niet omzetten naar 0!".format(fld),"w")

def bereken_onderbemaling(fc):
    """bereken onderbemalingen voor SUM_WAARDE, SUM_BLA, etc..
       Maakt selectie op basis van veld [ONTV_VAN] -> VAN_KNOOPN IN ('ZRE-123424', 'ZRE-234')"""
    # sum values op basis van selectie [ONTV_VAN]
    update_fields = ["VAN_KNOOPN",  # row[0]
                     "K_ONTV_VAN",    # row[1]
                     "AW_15_24_G",  # row[2]
                     "AW_15_24_O",  # row[3] obm
                     "AW_25_50_G",  # row[4]
                     "AW_25_50_O",  # row[5] obm
                     "DWR_GEBIED",  # row[6]
                     "DWR_ONBG",    # row[7] obm
                     "X_WON_GEB",   # row[8]
                     "X_WON_ONBG",  # row[9] obm
                     "X_VE_GEB",    # row[10]
                     "X_VE_ONBG",   # row[11] obm
                     ]

    with arcpy.da.UpdateCursor(fc, (update_fields)) as cursor:
        for row in cursor:
            VAN_KNOOPN, ONTV_VAN = row[0], row[1]
            if not ONTV_VAN in [None,""," "]: # check of sprake is van onderbemaling
                where_clause = "VAN_KNOOPN IN ({})".format(ONTV_VAN)
                row[3] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["AW_15_24_G"],where_clause) if r[0] != None])    # AW_15_24_O = sum(AW_15_24_G)
                row[5] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["AW_25_50_G"],where_clause) if r[0] != None])    # AW_25_50_O = sum(AW_25_50_G)
                row[7] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["DWR_GEBIED"],where_clause) if r[0] != None])    # DWR_ONBG = sum(DWR_GEBIED)
                row[9] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["X_WON_GEB"],where_clause) if r[0] != None])     # X_WON_ONBG = sum(X_WON_GEB)
                row[11]= sum([r[0] for r in arcpy.da.SearchCursor(fc,["X_VE_GEB"],where_clause) if r[0] != None])     # X_VE_ONBG = sum(X_VE_GEB)
                cursor.updateRow(row)
    del cursor, row
    print_log("Onderbemalingen succesvol berekend voor Plancap, drinkwater, woningen en ve's", "i")

def bereken_onderbemaling2(fc):
    """bereken onderbemalingen voor SUM_WAARDE, SUM_BLA, etc..
       Maakt selectie op basis van veld [ONTV_VAN] -> VAN_KNOOPN IN ('ZRE-123424', 'ZRE-234')"""
    # sum values op basis van selectie [ONTV_VAN]

    update_fields = ["VAN_KNOOPN",  # row[0]
                     "K_ONTV_VAN",  # row[1]
                     "POC_B_M3_G",  # row[2]
                     "POC_B_M3_O",  # row[3]
                     "POC_O_M3_G",  # row[4]
                     "POC_O_M3_O",  # row[5]
                     ]

    with arcpy.da.UpdateCursor(fc, (update_fields)) as cursor:
        for row in cursor:
            VAN_KNOOPN, ONTV_VAN = row[0], row[1]
            if not ONTV_VAN in [None,""," "]: # check of sprake is van onderbemaling
                where_clause = "VAN_KNOOPN IN ({})".format(ONTV_VAN)
                row[3] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["POC_B_M3_G"],where_clause) if r[0] != None])    # POC_B_M3_O = sum(POC_B_M3_G)
                row[5] = sum([r[0] for r in arcpy.da.SearchCursor(fc,["POC_O_M3_G"],where_clause) if r[0] != None])    # POC_O_M3_O = sum(POC_O_M3_G)
                cursor.updateRow(row)
    del cursor, row
    print_log("Onderbemalingen succesvol berekend voor POC ontwerp en POC beschikbaar", "i")

def spjoin_bronbestanden_aan_bemalingsgebieden():
    # joining DRINKWATER_BAG to POLYGONS
    print_log("spatialjoin DRINKWATER_BAG to POLYGONS...","i")
    arcpy.SpatialJoin_analysis(INP_DRINKWATER_BAG, POLYGON_LIS, DRINKWATER_POLYGON_LIS, "JOIN_ONE_TO_ONE", "KEEP_ALL")
    print_log("summarize DRINKWATER_BAG per POLYGON...","i")
    arcpy.Statistics_analysis (DRINKWATER_POLYGON_LIS, STATS_DRINKWATER, [["PAR_RESULT","SUM"],["ZAK_RESULT","SUM"]], "VAN_KNOOPN")
    # extra stapje om om te reken van liter/hr naar m3/hr voor part. en zakelijk drinkwater in STAT-tabel.

    add_field_from_dict_label(STATS_DRINKWATER, "stap2tmp", d_velden_tmp)

    bereken_veld(STATS_DRINKWATER, "SUM_PAR_RESULT_M3U", d_velden_tmp)
    bereken_veld(STATS_DRINKWATER, "SUM_ZAK_RESULT_M3U", d_velden_tmp)

    # joining PLANCAP_RIGO to POLYGONS
    print_log("spatialjoin PLANCAP_RIGO to POLYGONS...","i")
    arcpy.SpatialJoin_analysis(INP_PLANCAP_RIGO, POLYGON_LIS, PLANCAP_POLYGON_LIS, "JOIN_ONE_TO_ONE", "KEEP_ALL")
    controleer_spjoin_plancap(PLANCAP_POLYGON_LIS)
    arcpy.AlterField_management(PLANCAP_POLYGON_LIS,"Join_Count_1","","aantal plannen per polygoon") # Join_Count_1 alias aanpassen.
    print_log("summarize PLANCAP_RIGO per POLYGON...","i")
    arcpy.Statistics_analysis (PLANCAP_POLYGON_LIS, STATS_PLANCAP, [["Extra_AFW_2015_tm_2024","SUM"],["Extra_AFW_2025_tm_2050","SUM"]], "VAN_KNOOPN")

    # joining VE to POLYGONS
    print_log("spatialjoin VE_BELASTING to POLYGONS...","i")
    arcpy.SpatialJoin_analysis(INP_VE_BELASTING, POLYGON_LIS, VE_POLYGON_LIS, "JOIN_ONE_TO_ONE", "KEEP_ALL")
    # ## controleer_spjoin_plancap(VE_POLYGON_LIS) # ook check doen voor VE's die niet in Bemalingsgebied vallen. Lijkt me niet nodig.
    print_log("summarize VE_BELASTING per POLYGON...","i")
    arcpy.Statistics_analysis (VE_POLYGON_LIS, STATS_VE, [["GRONDSLAG","SUM"]], "VAN_KNOOPN")


def bepaal_verhard_oppervlak():
    arcpy.FeatureClassToFeatureClass_conversion(INP_VERHARD_OPP, gdb, EXP_VERHARD_OPP)
    print_log("Intersect {}...".format(";".join([POLYGON_LIS,EXP_VERHARD_OPP])),"i")
    arcpy.Intersect_analysis(
        in_features=";".join([POLYGON_LIS,EXP_VERHARD_OPP]),
        out_feature_class=VERHARD_OPP_INTERSECT,
        join_attributes= "ALL", #"ONLY_FID",
        cluster_tolerance="#",
        output_type="INPUT")

# niet nodig indien join_attributes= "ALL" van Intersect
##    print_log("join fields...", "i")
##    arcpy.AddField_management(VERHARD_OPP_INTERSECT, "VAN_KNOOPN", "TEXT")
##    arcpy.AddField_management(VERHARD_OPP_INTERSECT, "AANGESL_OP", "TEXT")
##    join_field(VERHARD_OPP_INTERSECT, POLYGON_LIS, "VAN_KNOOPN", "VAN_KNOOPN", "FID_{}".format(POLYGON_LIS), 'pk')
##    join_field(VERHARD_OPP_INTERSECT, EXP_VERHARD_OPP, "AANGESL_OP", "AANGESL_OP", "FID_{}".format(EXP_VERHARD_OPP), 'pk')

    print_log("summerize stats...", "i")
    arcpy.Statistics_analysis(
        in_table=VERHARD_OPP_INTERSECT,
        out_table=STATS_VERHARD_OPP,
        statistics_fields="SHAPE_Area SUM",
        case_field="VAN_KNOOPN;AANGESL_OP")

    # Opp in ha berekenen
    arcpy.AddField_management(STATS_VERHARD_OPP, "OPP_BEMGEBIED", "DOUBLE")
    join_field(STATS_VERHARD_OPP, POLYGON_LIS, "OPP_BEMGEBIED", "SHAPE_Area", "VAN_KNOOPN", "VAN_KNOOPN")
    add_field_from_dict(STATS_VERHARD_OPP, "OPP_BEMGEBIED_HA", d_velden_tmp)
    bereken_veld(STATS_VERHARD_OPP, "OPP_BEMGEBIED_HA", d_velden_tmp)
    add_field_from_dict(POLYGON_LIS, "HA_BEM_G", d_velden)
    join_field(POLYGON_LIS, STATS_VERHARD_OPP, "HA_BEM_G", "OPP_BEMGEBIED_HA", "VAN_KNOOPN", "VAN_KNOOPN")

##    # bereken percentages
##    add_field_from_dict(STATS_VERHARD_OPP, "PERCENTAGE", d_velden_tmp)
##    bereken_veld(STATS_VERHARD_OPP, "PERCENTAGE", d_velden_tmp)

    add_field_from_dict_label(POLYGON_LIS, "st3a", d_velden)

    # velden overhalen uit STATS_VERHARD_OPP per type
    for aansluiting in ["GEM", "HWA", "NAG", "OBK", "VGS"]:
        expression = "AANGESL_OP = '{}'".format(aansluiting)
        stat_name = "{}_{}".format(STATS_VERHARD_OPP,aansluiting)
        fld_ha    = "HA_{}_G".format(aansluiting)
        fld_pi    = "PI_{}_G".format(aansluiting)
        arcpy.TableToTable_conversion(STATS_VERHARD_OPP, gdb, stat_name, expression)
        join_field(POLYGON_LIS, stat_name, fld_ha, "OPP_BEMGEBIED_HA", "VAN_KNOOPN", "VAN_KNOOPN")
        # percentages worden achteraf berekend ##join_field(POLYGON_LIS, stat_name, fld_pi, "PERCENTAGE", "VAN_KNOOPN", "VAN_KNOOPN")



def main(POLYGON_LIS):
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
    # ##########################################################################
    # 1.) export input INP_POLYGON_LIS to result POLYGON_LIS
    arcpy.FeatureClassToFeatureClass_conversion(INP_POLYGON_LIS, gdb, POLYGON_LIS)

    # ##########################################################################
    # 2.) Spatial joins tussen POLYGON_LIS en de externe gegevens bronnen
    if INP_SKIP_SPJOIN:
        blokje_log("Skip SpatialJoin met externe inputs en gebruik bestaande STAT-tabellen.","i")
    else:
        blokje_log("Start SpatialJoin externe bronnen met hoofdbemalingsgebieden... (5 tot 25 minuten)","i")
        spjoin_bronbestanden_aan_bemalingsgebieden()

    blokje_log("Velden toevoegen en voorbereiden voor berekening onderbemaling...", "i")

    # ##########################################################################
    # 3.) Velden toevoegen en gegevens overnemen
    add_field_from_dict_label(POLYGON_LIS, "st2a", d_velden)

    # join stat_fields to POLYGON_LIS
    join_field(POLYGON_LIS, STATS_DRINKWATER, "PAR_RESULT", "SUM_PAR_RESULT_M3U", "VAN_KNOOPN", "VAN_KNOOPN")
    join_field(POLYGON_LIS, STATS_DRINKWATER, "ZAK_RESULT", "SUM_ZAK_RESULT_M3U", "VAN_KNOOPN", "VAN_KNOOPN")
    join_field(POLYGON_LIS, STATS_DRINKWATER, "X_WON_GEB", "FREQUENCY", "VAN_KNOOPN", "VAN_KNOOPN")
    join_field(POLYGON_LIS, STATS_PLANCAP, "AW_15_24_G", "SUM_Extra_AFW_2015_tm_2024", "VAN_KNOOPN", "VAN_KNOOPN")
    join_field(POLYGON_LIS, STATS_PLANCAP, "AW_25_50_G", "SUM_Extra_AFW_2025_tm_2050", "VAN_KNOOPN", "VAN_KNOOPN")
    join_field(POLYGON_LIS, STATS_VE, "X_VE_GEB", "SUM_GRONDSLAG", "VAN_KNOOPN", "VAN_KNOOPN")

    # bereken drinkwater per gebied (input voor onderbemalingen)
    bereken_veld(POLYGON_LIS, "DWR_GEBIED", d_velden)

    # ##########################################################################
    # 4.) Bereken onderbemaling voor DRINKWATER en PLANCAP en VE's
    blokje_log("bereken onderbemalingen voor drinkwater, plancap en ve's...","i")
    bereken_onderbemaling(POLYGON_LIS)

    vervang_None_door_0_voor_velden_in_lijst(l_src_None_naar_0_omzetten, POLYGON_LIS)

    # ##########################################################################
    # 6.) berekeningen uitvoeren
    # bereken dwa prognose & drinkwater per gebied
    # "bereken": "b2a"
    bereken_veld_label(POLYGON_LIS, "04_ber", d_velden)
    bereken_veld_label(POLYGON_LIS, "04a_ber", d_velden)

    # Vergelijk geschat en gemeten zonder
    # "bereken": "b2b"
    bereken_veld_label(POLYGON_LIS, "05_ber", d_velden)

    # bereken verhard opp
    blokje_log("Bepaal verhard oppervlak binnen bemalingsgebieden...","i")
    bepaal_verhard_oppervlak()

    vervang_None_door_0_voor_velden_in_lijst(
        ["HA_GEM_G", "HA_VGS_G", "HA_HWA_G","HA_OPW_G", "HA_NAG_G", "HA_OBK_G"],
        POLYGON_LIS)

    # bereken velden afhankelijk van verhard opp
    bereken_veld_label(POLYGON_LIS, '06_ber', d_velden)
    bereken_veld_label(POLYGON_LIS, '07_ber', d_velden)
    bereken_veld_label(POLYGON_LIS, '08_ber', d_velden)
    bereken_veld_label(POLYGON_LIS, '08a_ber', d_velden)

    # bepaal onderbemaling2 afhankelijk van verhard opp
    bereken_onderbemaling2(POLYGON_LIS)
    vervang_None_door_0_voor_velden_in_lijst(
            ["POC_B_M3_O", "POC_O_M3_O","POC_B_M3_G", "POC_O_M3_G"], POLYGON_LIS)
    bereken_veld_label(POLYGON_LIS, '10_ber', d_velden)

##    # ##########################################################################
##    # 7.) resultaat omzetten naar template (if "template" Exists)
##    if arcpy.Exists("template"):
##        print_log("resultaat omzetten naar template...", "i")
##        RESULT_REORDERED = os.path.basename(POLYGON_LIS) + "_REORDERED"
##        arcpy.FeatureClassToFeatureClass_conversion("template",gdb, RESULT_REORDERED)
##        arcpy.Append_management(POLYGON_LIS, RESULT_REORDERED, "NO_TEST")
##        arcpy.Delete_management(POLYGON_LIS)
##        arcpy.Rename_management(RESULT_REORDERED,POLYGON_LIS)
##    else:
##         print_log("geen template aanwezig dus de volgorde van velden is niet optimaal", "w")


    # ##########################################################################
    # 8.) add results to map
    blokje_log("eindresultaat toevoegen aan mxd", "i")
    MXD = arcpy.mapping.MapDocument("CURRENT")
    DF = arcpy.mapping.ListDataFrames(MXD)[0]
    for fc in[POLYGON_LIS]:
        layername = "eindresultaat: {}".format(fc)
        arcpy.MakeFeatureLayer_management(fc, layername)
        layer = arcpy.mapping.Layer(layername)
        arcpy.mapping.AddLayer(DF, layer, "AUTO_ARRANGE") # AUTO_ARRANGE

if __name__ == '__main__':

    # setting for development: skip spatial join. boolean
    INP_SKIP_SPJOIN             = True                  # skipp spatial join


    # laod from settings

    gdb                         = settings.gdb          # workspace
    log_dir                     = settings.log_dir      # log_dir
    l_src_None_naar_0_omzetten  = settings.l_fld_None_naar_0_omzetten # velden waarvan waardes worden omgezet van None naar 0
    INP_FIELDS_XLS              = settings.INP_FIELDS_XLS
    d_velden                    = get_d_velden(INP_FIELDS_XLS)  # dict for fields
    d_velden_tmp                = settings.d_velden_tmp         # tijdelijke velden
    ##d_velden.update(d_velden_tmp)                               # update met dict_tmp
##    print_log(d_velden,"i")
    # create data folder (if not exists)
    if not os.path.exists(os.path.dirname(gdb)): os.makedirs(os.path.dirname(gdb))
    # create database (if not exists)
    if not arcpy.Exists(gdb): arcpy.CreateFileGDB_management(os.path.dirname(gdb),os.path.basename(gdb))

    # set env
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = gdb

    # INPUTS toolbox
    INP_POLYGON_LIS         = sys.argv[1]
    INP_DRINKWATER_BAG      = sys.argv[2] # LIS.GEODYN_DRINKWATER_BAG
    INP_PLANCAP_RIGO        = sys.argv[3]
    INP_VE_BELASTING        = sys.argv[4]
    INP_VERHARD_OPP         = sys.argv[5]

    # tussenresultaten
    DRINKWATER_POLYGON_LIS  = "SpJoin_DRINKWATER2POLYGON_LIS"
    PLANCAP_POLYGON_LIS     = "SpJoin_PLANCAP2POLYGON_LIS"
    VE_POLYGON_LIS          = "SpJoin_VE2POLYGON_LIS"
    STATS_DRINKWATER        = "STATS_DRINKWATER"
    STATS_PLANCAP           = "STATS_PLANCAP"
    STATS_VE                = "STATS_VE"
    EXP_VERHARD_OPP         = 'EXP_VERHARD_OPP'
    VERHARD_OPP_INTERSECT   = "VERHARD_OPP_INTERSECT"
    STATS_VERHARD_OPP       = "STATS_VERHARD_OPP"
##    STATS_VERHARD_OPP_GEM   = "STATS_VERHARD_OPP_GEM"
##    STATS_VERHARD_OPP_HWA   = "STATS_VERHARD_OPP_HWA"
##    STATS_VERHARD_OPP_NAG   = "STATS_VERHARD_OPP_NAG"
##    STATS_VERHARD_OPP_OBK   = "STATS_VERHARD_OPP_OBK"
##    STATS_VERHARD_OPP_VGS   = "STATS_VERHARD_OPP_VGS"

    # eindresultaat
    POLYGON_LIS             = sys.argv[6]

    # logging
    LOGGING_LEVEL = logging.INFO # toggle between INFO / DEBUG
    if not os.path.exists(log_dir): os.mkdir(log_dir)
    strftime = datetime.strftime(datetime.now(),"%Y%m%d-%H.%M")
    logFileName = 'GeoDyn_{}.log'.format(strftime)
    logFile = os.path.join(log_dir,logFileName)
    logging.basicConfig(filename=logFile, level=LOGGING_LEVEL)
    logging.getLogger().setLevel(LOGGING_LEVEL)

    # start timer
    fTimeStart = start_timer()

##    # print belangrijke informatie
##    b_VIEW = bepaal_b_VIEW(INP_POLYGON_LIS,"K_INST_TOT") # True als veld "K_INST_TOT" bestaat
##    if b_VIEW:
##        print_log("WINCCOA = True","i")
##    else:
##        print_log("WINCCOA = False. Berekeningen met gegevens uit WINCCOA worden overgeslagen","w")

    print_log("\nworkspace = {}".format(gdb),"i")
    print_log("logfile = {}".format(logFile),"i")
    print_log("py-file: {}".format(sys.argv[0]),"i")
    if INP_SKIP_SPJOIN: print_log("let op SKIP_SPJOIN = True! Spatial join wordt geskipped!. Zet of False om alles opnieuw te berekenen", "w")
    for i, src in enumerate(sys.argv[1:]):
        if arcpy.Exists(src):
            desc = arcpy.Describe(src)
            path = desc.catalogPath
            del desc
        else:
            path = gdb
        print_log("layer {0}: {1}, path: {2}".format(i+1,src,path),"i")


    # check of template bestaat
    if not arcpy.Exists("template"):
        print_log("Geen template gevonden. Controleer of feature class 'template' voorkomt in data.gdb","w")


    # run main
    main(POLYGON_LIS)


    # end timer
    end_timer(fTimeStart)
