import os, sys

# settings
root_dir        = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
log_dir         = os.path.join(root_dir, 'log')
gdb             = r"G:\GISDATA\QGIS\geodyn_gem\data\shapes"
INP_FIELDS_XLS  = os.path.join(root_dir, 'inp_fields.xls') ##, 'fields$')
INP_FIELDS_XLS_SHEET    = "fields"

# dict d_velden_tmp
# purpose: dict d_velden_tmp is een aanvulling op d_velden (d_velden wordt uit de inp_fields.xlsx gegenereerd).
#         gebruikt in utl-functies add_field_from_dict() en bereken_veld()

d_velden_tmp = {
    # PWN temp
    "SUM_PAR_RESULT_M3U": {"add_fld": "stap2tmp", "field_type" : "DOUBLE", "field_alias" : "SUM_PAR_RESULT_M3U", "expression": "[SUM_PAR_RESULT] / 1000"}, #tmp in STATS_DRINKWATER
    "SUM_ZAK_RESULT_M3U": {"add_fld": "stap2tmp", "field_type" : "DOUBLE", "field_alias" : "SUM_ZAK_RESULT_M3U", "expression": "[SUM_ZAK_RESULT] / 1000"}, #tmp in STATS_DRINKWATER
    "OPP_BEMGEBIED_HA"  : {"add_fld": "stap3tmp", "field_type" : "DOUBLE", "field_alias" : "opp bemalingsgebied ha", "expression": "[SUM_SHAPE_Area]/10000"},
    "PERCENTAGE"        : {"add_fld": "stap4tmp", "field_type" : "DOUBLE", "field_alias" : "percentage", "expression": "[SUM_SHAPE_Area]/[OPP_BEMGEBIED]*100"},
    }

# lijst met velden waarvan de None-waardes omgezet moeten worden naar 0. Omdat 1 + None = None i.p.v. 1 + 0 = 1
l_fld_None_naar_0_omzetten = [
    "X_WON_ONBG", "X_WON_GEB","X_VE_ONBG", "X_VE_GEB", "DWR_GEBIED", "DWR_ONBG",
    "AW_15_24_G", "AW_15_24_O", "AW_25_50_G", "AW_25_50_O", "PAR_RESULT", "ZAK_RESULT",
    ##"AWA_HD_TOT", "AWA_HD_DWA", "AWA_HD_POC", "AWA_TK_TOT", "AWA_TK_DWA", "AWA_TK_POC", # deze op Null laten
    ]

