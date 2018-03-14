
import sys, os, logging
from datetime import datetime
import arcpy

# importeer utilities
from utl import start_timer, end_timer, blokje_log, print_log, add_field_from_dict, fld_exists, join_field, bereken_veld

# importeer settings
import settings

def main(INP_EINDRESULTAAT, GEODYN_EINDRESULTAAT):
    """Eindresultaat importeren naar Oracle"""

    print_log("\ttruncate Oracle tabel '{}'...".format(GEODYN_EINDRESULTAAT), "i")
    arcpy.TruncateTable_management(GEODYN_EINDRESULTAAT)

    print_log("\tvul Oracle tabel '{}'...".format(GEODYN_EINDRESULTAAT), "i")
    arcpy.Append_management(INP_EINDRESULTAAT, GEODYN_EINDRESULTAAT, "NO_TEST")


if __name__ == '__main__':

    INP_EINDRESULTAAT = sys.argv[1]

    # load from settings
    gdb                  = settings.gdb
    log_dir              = settings.log_dir      # log_dir
    GEODYN_EINDRESULTAAT = settings.GEODYN_EINDRESULTAAT_ORACLE

    # set env
    arcpy.env.overwriteOutput = True

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
    print_log("logfile = {}\n".format(logFile),"i")

    # run main
    main(INP_EINDRESULTAAT, GEODYN_EINDRESULTAAT)

    # end timer
    end_timer(fTimeStart)