# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeodynGem
                                 A QGIS plugin
 Geodyn voor gemeenten
                              -------------------
        begin                : 2018-03-09
        git sha              : $Format:%H$
        copyright            : (C) 2018 by BKGIS
        email                : b.kropf@bkgis.nl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
from qgis.core import QgsMessageLog, QgsMapLayerRegistry, QgsVectorFileWriter, QgsVectorLayer
from qgis.gui import QgsMessageBar

# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from geodyn_gem_dialog import GeodynGemDialog
import os.path
from app import settings
from app import m1_OvernemenGegevensGEM as m1
from app import m2_BerekenResultaten as m2
from app.utl import print_log, blokje_log, get_d_velden, get_d_velden_csv
from app.settings import keyword_1, keyword_2, keyword_3, keyword_4, keyword_5, keyword_6, keyword_7, result_dir

# for backward compatibility with older QGIS versions (without QgsWKBTypes)
try:
    from qgis.core import QgsWKBTypes
    b_QgsWKBTypes = True
except ImportError:
    b_QgsWKBTypes = False

class GeodynGem:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GeodynGem_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Geodyn gemeente')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'GeodynGem')
        self.toolbar.setObjectName(u'GeodynGem')

        # iface.messageBar().pushMessage("Error", "I'm sorry Dave, I'm afraid I can't do that",
        #                                level=QgsMessageBar.CRITICAL)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GeodynGem', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = GeodynGemDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        #self.dlg.lineEdit.clear()
        self.dlg.lineEdit.setText(result_dir)
        self.dlg.lineEdit.setToolTip("Om een vaste waarde in te stellen: ga naar local_settings.py in app directory van plugin.")
        self.dlg.pushButton.clicked.connect(self.select_output_folder)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/GeodynGem/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'geografische afvalwater prognose tool voor gemeenten'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Geodyn gemeente'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def move_to_front(self, l, txt):
        """searches for txt in layer.name() if match: move to front of list"""
        index = [l.index(i) for i in l if txt.lower() in i.name().lower()]
        if len(index) > 0:
            l.insert(0, l.pop(index[0]))
        if txt in [keyword_4, keyword_6]: # VE's en verhard opp zijn optioneel dus 'no data' toevoegen
            if len(index) == 0:
                l.insert(0, QgsVectorLayer(baseName="no data")) # geen keyword dus 'no data' als bovenste optie in keuzelijst
            else:
                l.append(QgsVectorLayer(baseName="no data")) # wel keyword dus 'no data' als laatste optie in keuzelijst
        return l

    def remove_result_layers(self, remove_all=False, delete_source=False):
        layers_to_remove = [layer for layer, flag in settings.l_result_layers_to_remove if remove_all or flag]
        ins = QgsMapLayerRegistry.instance()
        ##layers = ins.mapLayersByName()
        layers = self.iface.legendInterface().layers()
        for layer in layers:
            source = layer.source()
            if layer.name() in layers_to_remove:
                print_log("remove layer {}".format(layer.name()), "d")
                ins.removeMapLayer(layer.id())
                if delete_source:
                    pass # not sure if necessary
                    result = QgsVectorFileWriter.deleteShapeFile(source)
                    if not result:
                        print_log("Tool afgebroken! Kan resultaat ({}) niet verwijderen!".format(source), "e", self.iface)
                        return


    def select_output_folder(self):
        # filename = QFileDialog.getSaveFileName(self.dlg, "Select output folder ", "", '*.txt')
        # outputFolder = QFileDialog.getExistingDirectory(self.dlg, "Select Output Folder", QDir.currentPath())
        outputFolder = QFileDialog.getExistingDirectory(self.dlg, 'Select Output Folder')
        self.dlg.lineEdit.setText(outputFolder)

    def run(self):
        """Run method that performs all the real work"""

        self.remove_result_layers(remove_all=True, delete_source=True)

        layers = self.iface.legendInterface().layers()
        if not layers:
            print_log("Tool afgebroken! Geen layers gevonden. Voeg eerst layers toe", "e", self.iface)
            return
        layer_points, layer_lines, layer_polygons = [], [], []

        if b_QgsWKBTypes:
            for i, layer in enumerate(layers):
                if hasattr(layer, "wkbType"):
                    # qgis.core.QgsWKBTypes.displayString(int(vl.wkbType()))
                    if "point" in QgsWKBTypes.displayString(int(layer.wkbType())).lower(): ## QGis.WKBPoint:
                        layer_points.append(layer)
                    elif "line" in QgsWKBTypes.displayString(int(layer.wkbType())).lower(): ##QGis.WKBLineString:
                        layer_lines.append(layer)
                    elif "polygon" in QgsWKBTypes.displayString(int(layer.wkbType())).lower(): ##QGis.WKBPolygon:
                        layer_polygons.append(layer)
                    else:
                        pass
            layer_1 = layer_points[:] # more on slicing: https://www.afternerd.com/blog/python-copy-list/
            layer_2 = layer_lines[:]
            layer_3 = layer_points[:]
            layer_4 = layer_points[:]
            layer_5 = layer_polygons[:]
            layer_6 = layer_polygons[:]
            layer_7 = layer_polygons[:]

        else:
            print_log("ImportError for QgsWKBTypes. Kan geen geometrie herkennen voor layer inputs. \
                        Controleer of juiste layers zijn geselecteerd of upgrade QGIS.",
                "w", self.iface)
            layer_points = layer_lines = layer_polygons = layers
            layer_1 = layers[:]
            layer_2 = layers[:]
            layer_3 = layers[:]
            layer_4 = layers[:]
            layer_5 = layers[:]
            layer_6 = layers[:]
            layer_7 = layers[:]

        self.dlg.comboBox_1.clear()
        self.dlg.comboBox_2.clear()
        self.dlg.comboBox_3.clear()
        self.dlg.comboBox_4.clear()
        self.dlg.comboBox_5.clear()
        self.dlg.comboBox_6.clear()
        self.dlg.comboBox_7.clear()
        self.dlg.comboBox_1.addItems([i.name() for i in self.move_to_front(layer_points, keyword_1)])  # knooppunt
        self.dlg.comboBox_2.addItems([i.name() for i in self.move_to_front(layer_lines, keyword_2)])  # afvoerrelatie
        self.dlg.comboBox_3.addItems([i.name() for i in self.move_to_front(layer_points, keyword_3)])  # drinkwater BAG
        self.dlg.comboBox_4.addItems([i.name() for i in self.move_to_front(layer_points, keyword_4)])  # VE's
        self.dlg.comboBox_5.addItems([i.name() for i in self.move_to_front(layer_polygons, keyword_5)])  # plancap
        self.dlg.comboBox_6.addItems([i.name() for i in self.move_to_front(layer_polygons, keyword_6)])  # verhard opp
        self.dlg.comboBox_7.addItems([i.name() for i in self.move_to_front(layer_polygons, keyword_7)])  # bemalingsgebieden
        msg_tooltip = "Kaartlagen met '{}' in naam komen bovenaan de keuzelijst te staan.\
            \nVoor het instellen van een eigen zoekterm: ga naar local_settings.py in de app directory van de plugin."
        self.dlg.comboBox_1.setToolTip(msg_tooltip.format(keyword_1))
        self.dlg.comboBox_2.setToolTip(msg_tooltip.format(keyword_2))
        self.dlg.comboBox_3.setToolTip(msg_tooltip.format(keyword_3))
        self.dlg.comboBox_4.setToolTip(msg_tooltip.format(keyword_4))
        self.dlg.comboBox_5.setToolTip(msg_tooltip.format(keyword_5))
        self.dlg.comboBox_6.setToolTip(msg_tooltip.format(keyword_6))
        self.dlg.comboBox_7.setToolTip(msg_tooltip.format(keyword_7))

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:

            ##QgsMessageLog.logMessage("sel_index = {}".format(sel_index, level=QgsMessageLog.INFO))
            ##QgsMessageLog.logMessage("layer_index 4 = {}".format(self.move_to_front(layer_points, "VE")[self.dlg.comboBox_4.currentIndex()].name()), level=QgsMessageLog.INFO)
            ##QgsMessageLog.logMessage("layer4 = {}".format([i.name() for i in l4]), level=QgsMessageLog.INFO)

            sel_layers = [
                self.move_to_front(layer_1, keyword_1)[self.dlg.comboBox_1.currentIndex()],
                self.move_to_front(layer_2, keyword_2)[self.dlg.comboBox_2.currentIndex()],
                self.move_to_front(layer_3, keyword_3)[self.dlg.comboBox_3.currentIndex()],
                self.move_to_front(layer_4, keyword_4)[self.dlg.comboBox_4.currentIndex()],
                self.move_to_front(layer_5, keyword_5)[self.dlg.comboBox_5.currentIndex()],
                self.move_to_front(layer_6, keyword_6)[self.dlg.comboBox_6.currentIndex()],
                self.move_to_front(layer_7, keyword_7)[self.dlg.comboBox_7.currentIndex()],
            ]

            for i, layer in enumerate(sel_layers):
                print_log("input {}:\t{}".format(i, layer.name()), "i")

            gdb = self.dlg.lineEdit.text() #
            if not gdb or not os.path.exists(gdb):
                print_log("Script afgebroken! Geen geldige output map opgegeven ({}...)".format(gdb), "e", self.iface)
                return

            qgis_warnings_log = settings.qgis_warnings_log
            with open(qgis_warnings_log, 'w') as logfile:
                import time
                logfile.write('{level}: date {time}'.format(level="INFO", time=time.asctime()))

            blokje_log("Veld-info ophalen...", "i")
            INP_FIELDS_XLS = settings.INP_FIELDS_XLS
            INP_FIELDS_CSV = settings.INP_FIELDS_CSV
            try:
                ##raise ImportError # for testing csv
                from xlrd import open_workbook
                d_velden = get_d_velden(INP_FIELDS_XLS, 0, open_workbook)
            except ImportError:     # for compatibility with iMac
                print_log("import error 'xlrd': inp_fields.csv wordt gebruikt als input in plaats van inp_fields.xls",
                          "w", self.iface)
                d_velden = get_d_velden_csv(INP_FIELDS_CSV)
            for fld in d_velden:
                print_log("{}\n{}".format(fld, d_velden[fld]), "d")

            # check for required fields
            vl = sel_layers[0] # knooppunt
            if vl.fieldNameIndex('VAN_KNOOPN') == -1:
                print_log("Script afgebroken! Verplicht veld 'VAN_KNOOPN' niet gevonden in kaartlaag '{}'".format(vl.name()), "e", self.iface)
                return
            vl = sel_layers[1]  # afvoerrelatie
            if vl.fieldNameIndex('VAN_KNOOPN') == -1:
                print_log("Script afgebroken! Verplicht veld 'VAN_KNOOPN' niet gevonden in kaartlaag '{}'".format(vl.name()), "e", self.iface)
                return

            # run module 1
            d_K_ONTV_VAN, inp_polygon_layer = m1.main(self.iface, sel_layers, gdb, d_velden)

            # run module 2
            m2.main(self.iface, sel_layers, gdb, d_velden, d_K_ONTV_VAN, inp_polygon_layer)

            self.remove_result_layers(remove_all=False, delete_source=False)

            ##self.iface.mainWindow().statusBar().showMessage("dit is de mainWindow")
            warnings = []
            with open(qgis_warnings_log, 'r') as log_file:
                for line in log_file.readlines():
                    if "WARNING" in line:
                        warnings.append(line)

            msg = QMessageBox()
            if len(warnings) > 0:
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Script completed")
                msg.setText("{} warnings were encountered when running script".format(len(warnings)))
                msg.setInformativeText("For more information see details below or view log panel")
                detailedText = "The details are as follows:"
                detailedText += "\n" + "".join(warnings)
                detailedText += "\nlogfile: {}".format(settings.logFile)
                msg.setDetailedText(detailedText)
                msg.setStyleSheet("QLabel{min-width: 300px;}")
            else:
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("Script completed")
                msg.setText("No problems were encountered when running script!")
            retval = msg.exec_()
            ##QMessageBox.information(msg, "Info", "Script completed!")
            QgsMessageLog.logMessage("Script completed!", level=QgsMessageLog.INFO)
