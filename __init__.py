# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeodynGem
                                 A QGIS plugin
 Geodyn voor gemeenten
                             -------------------
        begin                : 2018-03-09
        copyright            : (C) 2018 by BKGIS
        email                : b.kropf@bkgis.nl
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load GeodynGem class from file GeodynGem.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .geodyn_gem import GeodynGem
    return GeodynGem(iface)
