#-------------------------------------------------------------------------------
# Name:        utl
# Purpose:     standaard utilities
#
# Author:      bkropf
#
# Created:     02-02-2017
# Copyright:   (c) bkropf 2017
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# import system modules
import sys, os, logging, time
from datetime import datetime, date
from settings import qgis_warnings_log
##import pandas ##arcpy
##import numpy as np


# QGIS
from qgis.gui import QgsMessageBar, QgisInterface
from qgis.core import * #QgsMessageLog, QgsVectorJoinInfo, QgsExpression, QgsField, QgsVectorLayer, QgsFeatureRequest
from PyQt4.QtCore import QVariant

def start_timer():
    '''Start timer'''
    fTimeStart = time.time()
    sBericht = '\nStarting ... (%s)\n' % time.asctime(time.localtime(fTimeStart))
    print_log (sBericht,"i")
    return fTimeStart

def end_timer(fTimeStart):
    '''End timer'''
    fTimeEnd = time.time()
    sBericht = '\nEnding ..... (%s)' % time.asctime(time.localtime(fTimeEnd))
    print_log (sBericht,"i")
    fTimePassed = round(fTimeEnd - fTimeStart) # in gehele secs
    tTimePassed = time.gmtime(fTimePassed) # as a tuple
    if tTimePassed.tm_hour >= 1:
        sBericht = time.strftime('(%H hrs, %M mins, %S secs have passed)\n', tTimePassed)
    elif tTimePassed.tm_min >= 1:
        sBericht = time.strftime('(%M mins, %S secs have passed)\n', tTimePassed)
    else:
        sBericht = time.strftime('(%S secs have passed)\n', tTimePassed)
    print_log (sBericht,"i")

def blokje_log(txt,logType):
    print_log("\n" + \
             "---------------------------------------------------------------------------------------------------------\n" + \
             "------ " + str(txt) + "\t\t" + time.asctime() + "\n" + \
             "---------------------------------------------------------------------------------------------------------\n" + \
             "\n", logType)

def print_log(message, logType="i", iface=False, **kwargs):

    # if args:
    #     iface = args[0] if isinstance(args[0], QgisInterface) else False
    # else:
    #     iface = False

    try:
        print (message)  # print mag niet in QGIS?
    except IOError:
        pass

    ##QgsMessageLog.logMessage("log_lvl = {}".format(logging.getLogger().getEffectiveLevel()),level=QgsMessageLog.INFO)
    if logType == "d" and logging.getLogger().getEffectiveLevel() == logging.DEBUG:
        # alleen als logging level op DEBUG is ingesteld printen!
        logging.debug(message)
        QgsMessageLog.logMessage("debug: {}".format(message), level=QgsMessageLog.INFO)
    elif logType == "i": # info
        QgsMessageLog.logMessage(message, level=QgsMessageLog.INFO)
        logging.info(message)
    elif logType == "w": # warning
        QgsMessageLog.logMessage("WARNING: {}".format(message), level=QgsMessageLog.WARNING)
        if iface: iface.messageBar().pushMessage("Warning", message, level=QgsMessageBar.WARNING)
        logging.warning(message)
        with open(qgis_warnings_log, 'a') as logfile:
            logfile.write('\n({level}): {message}'.format(level="WARNING", message=message))

    elif logType == "e": # error
        logging.error(message)
        QgsMessageLog.logMessage(message, level=QgsMessageLog.CRITICAL)
        if iface: iface.messageBar().pushMessage("Error", message, level=QgsMessageBar.CRITICAL)
    elif logType == "c": # critical
        logging.critical(message)
        ##iface.messageBar().pushMessage("Error", txt, level=QgsMessageBar.CRITICAL)


def get_count(fc):
    result = arcpy.GetCount_management(fc)
    return int(result.getOutput(0))

def fld_exists(fc,fld_name):
    """return True if field exists"""
    if len(arcpy.ListFields(fc,fld_name)) > 0:
        return True
    else:
        return False

def add_field_from_dict(fc, fld_name, d_fld):
    """add field. dict must be like
        d_fld[fld_name] = {
            'field_alias'   : 'your alias',
            'field_length'  : '50', (optional)
            'field_type'    : 'TEXT',
            } """

    print_log("veld {} toevoegen".format(fld_name), "d")
    fld = d_fld[fld_name] # dict with field parameters
    if fld in [field.name() for field in fc.pendingFields()]:
        return
    if "field_length" in fld.keys():
        field_length = fld["field_length"]
    else:
        field_length = 10
    ##print_log("veld lengte = {}".format(field_length), "i")

    if not isinstance(fc, QgsVectorLayer): fc = QgsVectorLayer(fc, "layer", "ogr")

    fldtype_mapper = {
        "TEXT" : QVariant.String,
        "LONG" : QVariant.Int,
        "SHORT": QVariant.Int,
        "DOUBLE":QVariant.Double,
        "FLOAT": QVariant.Double,
        "DATE" : QVariant.DateTime,
    }

    if fc.fieldNameIndex(fld_name) == -1:
        fc.dataProvider().addAttributes([QgsField(prec=2, name=fld_name, type=fldtype_mapper.get(fld["field_type"],QVariant.String), len=field_length)])
        fc.updateFields()

def add_field_from_dict_label(fc, add_fld_value, d_fld):
    """velden toevoegen op basis van dict.keys 'add_fld', 'order' en 'fc' in d_fld
       maakt gebuikt van functie add_field_from_dict() maar dan voor een verzameling velden
       op basis van 'add_fld'. 'order' is optioneel voor het behouden van volgorde"""
    # select dict with "order" and "add_fld" keys
    d_fld_order = {k:v for (k,v) in d_fld.items() if "add_fld" in v.keys() and "order" in v.keys()}
    # subselect with "order" == add_fld_value
    d_fld_order = {k:v for (k,v) in d_fld_order.items() if v["add_fld"] == add_fld_value}
    if len(d_fld_order) > 0:
        print_log("velden met 'add_fld' : '{}' toevoegen op volgorde van 'order':".format(add_fld_value),"d")
        for fld, value in sorted(d_fld_order.iteritems(), key=lambda (k,v): (v["order"])): # sort by key "order"
            add_field_from_dict(fc, fld, d_fld)
    # select dict without "order" and "add_fld" keys
    d_fld_no_order = {k:v for (k,v) in d_fld.items() if "add_fld" in v.keys() and not "order" in v.keys()}
    # subselect with "order" == add_fld_value
    d_fld_no_order = {k:v for (k,v) in d_fld_no_order.items() if v["add_fld"] == add_fld_value}
    if len (d_fld_no_order) > 0:
        print_log("geen 'order' gevonden in d_velden, velden met 'add_fld' : '{}' toevoegen in willekeurige volgorde:".format(add_fld_value),"d")
        for fld in d_fld_no_order:
            add_field_from_dict(fc, fld, d_fld)

def bereken_veld(fc, fld_name, d_fld):
    """bereken veld m.b.v. 'expression' in dict
       als dict de key 'mag_niet_0_zijn' bevat, wordt een selectie gemaakt voor het opgegeven veld"""
    try:
        expression = d_fld[fld_name]["expression"]
        expression = expression.replace("[", '"').replace("]", '"')
        print_log("calculate {} = {}".format(fld_name, expression), "i")
        print_log(d_fld[fld_name], "d")
        if "mag_niet_0_zijn" in d_fld[fld_name]:
            l_fld = d_fld[fld_name]["mag_niet_0_zijn"]
            where_clause = " and ".join(
                ['"{}" <> 0'.format(fld) for fld in l_fld])  # [FLD1,FLD2] -> "FLD1 <> 0 and FLD2 <> 0"
            expr = QgsExpression(where_clause)
            print_log(where_clause, "d")
            it = fc.getFeatures(QgsFeatureRequest(expr))  # iterator object
            fc.setSelectedFeatures([i.id() for i in it])

        # calculate field
        e = QgsExpression(expression)
        e.prepare(fc.pendingFields())

        fc.startEditing()
        idx = fc.fieldNameIndex(fld_name)
        for f in fc.getFeatures():
            f[idx] = e.evaluate(f)
            fc.updateFeature(f)
        fc.commitChanges()
        fc.setSelectedFeatures([])

    except Exception as e:
        print_log("probleem bij bereken veld {}! {}".format(fld_name,e),"w")

def bereken_veld_label(fc, bereken, d_fld):
    """bereken velden op basis van label 'bereken' en fc in d_fld"""
    print_log("\nvelden met label 'bereken' : '{}' uitrekenen:".format(bereken),"i")
    for fld in d_fld:
        if not "bereken" in d_fld[fld].keys(): continue
        if bereken == d_fld[fld]["bereken"]: bereken_veld(fc, fld, d_fld)

def join_field(input_table, join_table, field_to_calc, field_to_copy, joinfield_input_table, joinfield_join_table):
    """Veld overnemen uit andere tabel o.b.v. tablejoin.
       Het veld wat gevuld moet worden (field_to_calc) moet al wel bestaan en wordt in deze functie alleen gevuld.
       Vul "pk" in bij joinfield_join_table om de primary key te laten bepalen of kies een ander veld"""
    # voorbeeld: join_field(input_table="", join_table="", field_to_calc="", field_to_copy="", joinfield_input_table="", joinfield_join_table="")
    if 1==1:

        print_log("joining field {} from {}...".format(field_to_calc, os.path.basename(join_table.name())), "d")

        input_table.setSelectedFeatures([])
        # add join
        joinObject = QgsVectorJoinInfo()
        joinObject.joinLayerId = join_table.id()
        joinObject.joinFieldName = joinfield_join_table
        joinObject.targetFieldName = joinfield_input_table
        input_table.addJoin(joinObject)

        # calculate field
        e = QgsExpression('"{}_{}"'.format(join_table.name(),field_to_copy))
        e.prepare(input_table.pendingFields())
        print_log("expression = {}".format('"{}_{}"'.format(join_table.name(),field_to_copy)), "d")

        input_table.startEditing()
        idx = input_table.fieldNameIndex(field_to_calc)
        for f in input_table.getFeatures():
            f[idx] = e.evaluate(f)
            input_table.updateFeature(f)
        input_table.commitChanges()

        input_table.removeJoin(joinObject.joinLayerId)

    # except Exception as e:
    #     print_log("problemen met join_field {}! {}".format(field_to_calc,e),"w")


def rename_fields(table_to_rename_field, d_rename):
    print_log("Hernoem velden van {}...".format(table_to_rename_field),"d")
    for f in d_rename:
        # f = field to rename
        try:
            in_table, new_field_name, new_field_alias = d_rename[f]
            if in_table == table_to_rename_field:
                print_log("\t{} -> {} ({})".format(f,new_field_name,new_field_alias),"d")
                # AlterField_management (in_table, field, {new_field_name}, {new_field_alias})
                arcpy.AlterField_management (in_table, f, new_field_name, new_field_alias)
        except Exception as e:
            print_log("kan veld {} niet hernoemen! {}".format(f,e),"w")


def parse_xlsx(INP_FIELDS_XLS, SHEETNR, open_workbook):

    workbook = open_workbook(INP_FIELDS_XLS)
    sheets = workbook.sheet_names()
    active_sheet = workbook.sheet_by_name(sheets[SHEETNR])
    num_rows = active_sheet.nrows
    num_cols = active_sheet.ncols
    header = [active_sheet.cell_value(0, cell).lower() for cell in range(num_cols)]
    for row_idx in xrange(1, num_rows):
        row_cell = [active_sheet.cell_value(row_idx, col_idx) for col_idx in range(num_cols)]
        yield dict(zip(header, row_cell))

def get_d_velden(INP_FIELDS_XLS, SHEETNR, open_workbook):
    """dictionary field-info ophalen uit excel zonder pandas met xlrd"""

    d_velden = {}

    for srow in parse_xlsx(INP_FIELDS_XLS, SHEETNR, open_workbook):
        fld = {}

        # verplichte keys
        fld["order"] = srow["order"]
        fld["field_type"] = srow["type"]
        fld["field_alias"] = srow["alias"]
        fld["add_fld"] = srow["stap_toevoegen"]
        # optionele keys
        if str(srow["mag_niet_0_zijn"]) != "nan": # np.nan, df.notna() werkt niet en np.isnan() not supported
            fld["mag_niet_0_zijn"] = str(srow["mag_niet_0_zijn"]).split(";")
        else:
            print (type(srow["mag_niet_0_zijn"]),srow["mag_niet_0_zijn"])
        if str(srow["lengte"]) not in ["nan", ""," "]:
            fld["field_length"] = int(srow["lengte"])
        if str(srow["expression"]) not in ["nan", ""," "]:
            fld["expression"] = srow["expression"]
        if str(srow["stap_bereken"]) not in ["nan", ""," "]:
            fld["bereken"] = srow["stap_bereken"]
        d_velden[srow["fieldname"]] = fld

    return d_velden


def get_d_velden_csv(INP_FIELDS_CSV):
    """dictionary field-info ophalen uit excel zonder pandas met xlrd"""
    import csv
    d_velden = {}

    input_file = csv.DictReader(open(INP_FIELDS_CSV), delimiter=";")

    for srow in input_file:
        if not srow["fieldname"]:
            continue

        fld = {}

        # verplichte keys
        fld["order"] = srow["order"]
        fld["field_type"] = srow["type"]
        fld["field_alias"] = srow["alias"]
        fld["add_fld"] = srow["stap_toevoegen"]
        # optionele keys
        if str(srow["mag_niet_0_zijn"]) != "nan": # np.nan, df.notna() werkt niet en np.isnan() not supported
            fld["mag_niet_0_zijn"] = str(srow["mag_niet_0_zijn"]).split(";")
        else:
            print (type(srow["mag_niet_0_zijn"]),srow["mag_niet_0_zijn"])
        if str(srow["lengte"]) not in ["nan", ""," "]:
            fld["field_length"] = int(srow["lengte"])
        if str(srow["expression"]) not in ["nan", ""," "]:
            fld["expression"] = srow["expression"]
        if str(srow["stap_bereken"]) not in ["nan", ""," "]:
            fld["bereken"] = srow["stap_bereken"]
        d_velden[srow["fieldname"]] = fld

    return d_velden


def add_layer(layer, visible=True):
    ins = QgsMapLayerRegistry.instance()
    layers = ins.mapLayersByName(layer.name())
    for old_layer in layers:
        ##return old_layer
        print_log("remove layer {}".format(old_layer),"d")
        ins.removeMapLayer(old_layer.id())
    ##layer.setVisible = visible
    ins.addMapLayer(layer)
    return layer


def update_datetime(layer, fieldname):
    if layer.fieldNameIndex(fieldname) == -1:
        layer.dataProvider().addAttributes([QgsField(name=fieldname, type=QVariant.String, len=19)])
        layer.updateFields()
    field = layer.fieldNameIndex(fieldname)
    e = QgsExpression( " $now " )
    e.prepare( layer.pendingFields() )
    layer.startEditing()
    for feat in layer.getFeatures():
        feat[field] = e.evaluate( feat )
        layer.updateFeature( feat )
    layer.commitChanges()

# def pandas_get_d_velden(INP_FIELDS_XLS, INP_FIELDS_XLS_SHEET):
#     """dictionary field-info ophalen uit excel met pandas"""
#     df = pandas.read_excel(INP_FIELDS_XLS, sheet_name=INP_FIELDS_XLS_SHEET, header=0, skiprows=None, skip_footer=0, index_col=None,
#                       names=None, usecols=None, parse_dates=False, date_parser=None, na_values=None, thousands=None,
#                       convert_float=True, converters=None, dtype=None, true_values=None, false_values=None, engine=None,
#                       squeeze=False)
#
#     d_velden = {}
#
#     for i, srow in df.iterrows():
#         fld = {}
#
#         # verplichte keys
#         fld["order"] = srow["order"]
#         fld["field_type"] = srow["type"]
#         fld["field_alias"] = srow["alias"]
#         fld["add_fld"] = srow["stap_toevoegen"]
#         # optionele keys
#         if str(srow["mag_niet_0_zijn"]) != "nan": # np.nan, df.notna() werkt niet en np.isnan() not supported
#             fld["mag_niet_0_zijn"] = str(srow["mag_niet_0_zijn"]).split(";")
#         else:
#             print (type(srow["mag_niet_0_zijn"]),srow["mag_niet_0_zijn"])
#         if str(srow["expression"]) != "nan":
#             fld["expression"] = srow["expression"]
#         if str(srow["stap_bereken"]) != "nan":
#             fld["bereken"] = srow["stap_bereken"]
#         d_velden[srow["fieldname"]] = fld
#
#     return d_velden

# example fast calculate
# https://gis.stackexchange.com/questions/97344/how-to-change-attributes-with-qgis-python
# from qgis.utils import iface
# from PyQt4.QtCore import *
#
# layers = iface.legendInterface().layers()
#
# for layer in layers:
#     name = layer.name()
#     if name.endswith('x'):
#         provider = layer.dataProvider()
#         updateMap = {}
#         fieldIdx = p.fields().indexFromName( 'attr' )
#         features = provider.getFeatures()
#         for feature in features:
#             updateMap[feature.id()] = { fieldIdx: 'a' }
#
#         provider.changeAttributeValues( updateMap )

if __name__ == '__main__':

    print_log("test utl","i")