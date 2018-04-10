# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2018 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ###########################################################################*/
"""This module provides selection interaction for with :class:`PlotWidget`.
"""

__authors__ = ["T. Vincent"]
__license__ = "MIT"
__date__ = "22/03/2018"


import numpy

from ....third_party import enum
from ....utils.weakref import WeakList
from ... import qt, icons
from .. import PlotWidget
from .. import items
from ..Colors import rgba


class _Selection(qt.QObject):
    """Object describing a selection in a plot.

    :param QObject parent: The selector that created this selection
    :param str kind: The kind of selection represented by this object
    """

    sigChanged = qt.Signal()  # TODO
    """Signal emitted when this selection has changed"""

    def __init__(self, parent, kind):
        assert isinstance(parent, InteractiveSelection)
        super(_Selection, self).__init__(parent)
        self._color = rgba('red')
        self._items = WeakList()
        self._points = None
        self._label = ''
        self._kind = str(kind)

    def __del__(self):
        # Clean-up plot items
        self._removePlotItems()

    def _removedFromSelector(self):
        """Remove this selection from the selector that created it"""
        self._removePlotItems()
        self.setParent(None)

    def getKind(self):
        """Return kind of selection

        :rtype: str
        """
        return self._kind

    def getColor(self):
        """Returns the color of this selection

        :rtype: QColor
        """
        return qt.QColor.fromRgbF(*self._color)

    def setColor(self, color):
        """Set the color used for this selection.

        :param color: The color to use for selection shape as
           either a color name, a QColor, a list of uint8 or float in [0, 1].
        """
        color = rgba(color)
        if color != self._color:
            self._color = color

            # Update color of selection items in the plot
            for item in self._items:
                if isinstance(item, items.ColorMixIn):
                    item.setColor(rgba(color))

    def getLabel(self):
        """Returns the label displayed for this selection.

        :rtype: str
        """
        return self._label

    def setLabel(self, label):
        """Set the label displayed with this selection.

        :param str label: The text label to display
        """
        label = str(label)
        if label != self._label:
            self._label = label
            for item in self._items:
                if isinstance(item, items.Marker):
                    item.setText(self._label)

    def getControlPoints(self):
        """Returns the current selection control points.

        It returns an empty tuple if there is currently no selection.

        :return: Array of (x, y) position in plot coordinates
        :rtype: numpy.ndarray
        """
        return None if self._points is None else numpy.array(self._points)

    def setControlPoints(self, points):
        """Set this selection control points.

        :param points: Iterable of (x, y) control points
        """
        points = numpy.array(points)
        assert points.ndim == 2
        assert points.shape[1] == 2

        if (self._points is None or
                not numpy.all(numpy.equal(points, self._points))):
            kind = self.getKind()

            if kind in ('point', 'hline', 'vline'):
                assert len(points) == 1
                markerPos = points[0]

            elif kind == 'rectangle':
                assert len(points) == 2
                markerPos = points.min(axis=0)
            elif kind == 'line':
                assert len(points) == 2
                markerPos = points[numpy.argmin(points[:, 0])]
            elif kind == 'polygon':
                markerPos = points[numpy.argmin(points[:, 1])]

                # Makes sure first and last points are different
                if numpy.all(numpy.equal(points[0], points[-1])):
                    points = points[:-1]
                assert len(points) > 2

            else:
                raise RuntimeError('Unsupported selection kind: %s' % kind)

            if self._items:  # Update plot items
                for item in self._items:
                    if isinstance(item, items.Shape):
                        item.setPoints(points)
                    elif isinstance(item, items.Marker):
                        item.setPosition(*markerPos)

            else:  # Create plot items
                self._createPlotItems(points, markerPos)

            self._points = points

    def _createPlotItems(self, points, markerPos):
        """Create items displaying the selection in the plot.

        :param numpy.ndarray points: Control points as a 2D array of (x, y)
        :param markerPos: (x, y) position of the label marker
        """
        selector = self.parent()
        plot = selector.parent()

        x, y = points.T
        kind = self.getKind()
        legend = "__Selection-%d__" % id(self)

        if kind == 'point':
            plot.addMarker(
                x[0], y[0],
                legend=legend,
                text=self.getLabel(),
                color=rgba(self.getColor()),
                draggable=False)
            item_list = [plot._getItem(kind='marker', legend=legend)]

        elif kind == 'hline':
            plot.addYMarker(
                y[0],
                legend=legend,
                text=self.getLabel(),
                color=rgba(self.getColor()),
                draggable=False)
            item_list = [plot._getItem(kind='marker', legend=legend)]

        elif kind == 'vline':
            plot.addXMarker(
                x[0],
                legend=legend,
                text=self.getLabel(),
                color=rgba(self.getColor()),
                draggable=False)
            item_list = [plot._getItem(kind='marker', legend=legend)]

        else:  # rectangle, line, polygon
            plot.addItem(x, y,
                         legend=legend,
                         shape='polylines' if kind == 'line' else kind,
                         color=rgba(self.getColor()),
                         fill=False)

            plot.addMarker(*markerPos,
                           legend=legend + '-name',
                           text=self.getLabel(),
                           color=rgba(self.getColor()),
                           symbol='',
                           draggable=False)
            item_list = [plot._getItem(kind='item', legend=legend),
                         plot._getItem(kind='marker', legend=legend + '-name')]

        self._items = WeakList(item_list)

    def _removePlotItems(self):
        """Remove items from their plot."""
        for item in list(self._items):
            plot = item.getPlot()
            if plot is not None:
                plot._remove(item)
        self._items = WeakList()


class InteractiveSelection(qt.QObject):
    """Class handling a selection interaction on a :class:`PlotWidget`

    It supports the selection of multiple points, rectangles, polygons,
    lines, horizontal and vertical lines.

    Example:

    .. code-block:: python

       from silx import sx
       from silx.gui.plot.tools import InteractiveSelection

       plot = sx.PlotWindow()  # Create a PlotWindow
       plot.show()

       # Create object controlling interactive selection
       selector = InteractiveSelection(plot)

       # Add the selection mode action to the PlotWindow toolbar
       toolbar = plot.getInteractiveModeToolBar()
       toolbar.addAction(selector.getSelectionModeAction())

       # Connect InteractiveSelection messages to PlotWindow status bar
       statusBar = plot.statusBar()
       selector.sigMessageChanged.connect(statusBar.showMessage)

       # Start a selection of 3 points
       selector.start(count=3, kind='point')

    :param PlotWidget parent: The plot widget the selection is done on
    """

    sigSelectionStarted = qt.Signal(str)
    """Signal emitted whenever a selection has started.

    It provides the shape used for the selection.
    """

    sigSelectionChanged = qt.Signal(tuple)
    """Signal emitted whenever the selection has changed.

    It provides the selection.
    """

    sigSelectionFinished = qt.Signal(tuple)
    """Signal emitted when selection is terminated.

    It provides the selection.
    If the selection was cancelled, the returned selection is empty.
    """

    sigMessageChanged = qt.Signal(str)
    """Signal emitted when a new message should be displayed to the user

    It provides the message as a str.
    """

    def __init__(self, parent):
        assert isinstance(parent, PlotWidget)
        super(InteractiveSelection, self).__init__(parent)
        self._selection = []
        self._isStarted = False
        self._isInteractiveModeStarted = False
        self._nbSelection = 0

        self._validationMode = self.ValidationMode.ENTER
        self._statusMessage = ''

        self._shapeKind = 'point'
        self._color = rgba('red')

        self._label = "selector-%d" % id(parent)

        self._eventLoop = None

        self._action = qt.QAction(self)
        self._action.setEnabled(False)
        self._action.setCheckable(True)
        self._action.setChecked(False)
        self._action.setIcon(icons.getQIcon('normal'))
        self._action.setText('Selection Mode')
        self._action.setToolTip('Selection mode')

        self._action.changed.connect(self._actionChanged)
        self._action.triggered.connect(self._actionTriggered)

        parent.sigInteractiveModeChanged.connect(
            self._plotInteractiveModeChanged)

    # Associated QAction

    def getSelectionModeAction(self):
        """Returns a QAction for the selection interaction mode

        :rtype: QAction
        """
        return self._action

    def _actionChanged(self):
        """Handle action enabled state changed and sync selector"""
        # Makes sure action is only enabled while a selection is running
        action = self.getSelectionModeAction()
        action.setEnabled(self.isStarted())

    def _actionTriggered(self, checked=False):
        """Handle action triggered by user"""
        self._startSelectionInteraction()
        self._updateStatusMessage()

    # PlotWidget eventFilter and listeners

    def _plotInteractiveModeChanged(self, source):
        """Handle change of interactive mode in the plot"""
        action = self.getSelectionModeAction()
        action.setChecked(source is self)

        if self.isStarted():
            if source is not self:
                self._stopSelectionInteraction(resetInteractiveMode=False)
                self._updateStatusMessage(extra='Use selection mode')
            else:
                self._startSelectionInteraction()
                self._updateStatusMessage()

    def eventFilter(self, obj, event):
        if event.type() == qt.QEvent.Hide:
            self.stop()

        elif event.type() == qt.QEvent.KeyPress:
            if event.key() in (qt.Qt.Key_Delete, qt.Qt.Key_Backspace) or (
                    event.key() == qt.Qt.Key_Z and
                    event.modifiers() & qt.Qt.ControlModifier):
                if self.undo():
                    # Stop further handling of keys if something was undone
                    return True

            elif (event.key() == qt.Qt.Key_Return and
                    self.getValidationMode() == self.ValidationMode.ENTER):
                self.stop()
                return True  # Stop further handling of those keys

        return super(InteractiveSelection, self).eventFilter(obj, event)

    # Handle selection interaction

    def _handleInteraction(self, event):
        """Handle mouse interaction for selection"""
        if self._shapeKind == 'point':
            if event['event'] == 'mouseClicked' and event['button'] == 'left':
                self._appendSelection(event['x'], event['y'], self._shapeKind)
        else:  # other shapes
            if (event['event'] == 'drawingFinished' and
                    event['parameters']['label'] == self._label):
                self._appendSelection(
                    event['xdata'], event['ydata'], self._shapeKind)

    def _stopSelectionInteraction(self, resetInteractiveMode):
        """Stop selection interaction if if was running

        :param bool resetInteractiveMode:
            True to reset interactive mode, False to avoid
        """
        if self._isInteractiveModeStarted:
            self._isInteractiveModeStarted = False
            if self.isStarted():
                plot = self.parent()

                plot.sigPlotSignal.disconnect(self._handleInteraction)
                if resetInteractiveMode and self._shapeKind != 'point':
                    plot.setInteractiveMode(mode='select', source=self)

    def _startSelectionInteraction(self):
        """Start selection interaction if it was not running

        :return: True if interaction has changed, False otherwise
        :rtype: bool
        """
        if (not self._isInteractiveModeStarted and self.isStarted() and
                (self._nbSelection is None or
                 len(self.getSelections()) < self._nbSelection)):
            self._isInteractiveModeStarted = True
            plot = self.parent()

            if self._shapeKind == 'point':
                plot.setInteractiveMode(mode='select', source=self)
            else:
                plot.setInteractiveMode(mode='draw',
                                        source=self,
                                        shape=self._shapeKind,
                                        color=rgba(self.getColor()),
                                        label=self._label)

            plot.sigPlotSignal.connect(self._handleInteraction)
            return True

        else:
            return False

    # Selection API

    def getSelectionPoints(self):
        """Returns the current selection control points

        :return: Tuple of arrays of (x, y) points in plot coordinates
        :rtype: tuple of Nx2 numpy.ndarray
        """
        return tuple(s.getControlPoints() for s in self._selection)

    def getSelections(self):
        """Returns the list of current selection.

        It returns an empty tuple if there is currently no selection.

        :return: Tuple of arrays of objects describing the selection
        """
        return tuple(self._selection)

    def _appendSelection(self, x, y, kind):
        """Add a shape to the selection

        :param x: x coordinates
        :param y: y coordinates of the shape control points
        :param str kind: the kind of shape
        """
        selections = self.getSelections()
        assert self._nbSelection is None or len(selections) < self._nbSelection

        plot = self.parent()
        if plot is None:
            return

        # Create new selection object
        selection = _Selection(parent=self, kind=kind)
        selection.setColor(self.getColor())
        selection.setLabel('%d' % len(selections))
        if kind == 'point':
            points = numpy.array([(x, y)], dtype=numpy.float64)
        else:
            points = numpy.array((x, y), dtype=numpy.float).T
        selection.setControlPoints(points)

        self._selection.append(selection)
        self._selectionUpdated()

    def _selectionUpdated(self):
        """Handle update of the selection"""
        selections = self.getSelections()
        assert self._nbSelection is None or len(selections) <= self._nbSelection

        self.sigSelectionChanged.emit(selections)

        if self.isStarted():
            if self._nbSelection is None or len(selections) < self._nbSelection:
                self._startSelectionInteraction()
                self._updateStatusMessage()

            else:
                self._stopSelectionInteraction(resetInteractiveMode=True)
                validationMode = self.getValidationMode()
                if validationMode == self.ValidationMode.AUTO:
                    self.stop()
                elif validationMode == self.ValidationMode.ENTER:
                    self._updateStatusMessage(extra='Press Enter to confirm')
                else:
                    self._updateStatusMessage()

    def _removePlotItems(self, item_list):
        """Remove items from their plot.

        :param item_list: Iterable of plot items to remove
        """
        for item in item_list:
            plot = item.getPlot()
            if plot is not None:
                plot._remove(item)

    def clearSelections(self):
        """Reset current selections

        :return: True if selections were reset.
        :rtype: bool
        """
        if self.getSelections():  # Something to reset
            selections = self._selection
            self._selection = []
            for selection in selections:
                selection._removedFromSelector()
            self._selectionUpdated()
            return True

        else:
            return False

    def undo(self):
        """Remove last selection from the selection list.

        :return: True if a selection was undone.
        :rtype: bool
        """
        if self.getSelections():  # Something to undo
            selection = self._selection.pop()
            selection._removedFromSelector()
            self._selectionUpdated()
            return True

        else:
            return False

    # Selection parameters

    @enum.unique
    class ValidationMode(enum.Enum):
        """Mode of validation of the selection"""

        AUTO = 'auto'
        """Automatically ends the selection once the user terminates the last shape"""

        ENTER = 'enter'
        """Ends the selection when the *Enter* key is pressed"""

        NONE = 'none'
        """Do not provide the user a way to end the selection.

        The end of a selection must be done through :meth:`stop` or :meth:`cancel`.
        This is useful if the application is willing to provide its own way of
        ending the selection (e.g., a button).
        """

    def getValidationMode(self):
        """Returns the selection validation mode in use.

        :rtype: ValidationMode
        """
        return self._validationMode

    def setValidationMode(self, mode):
        """Set the way to perform selection validation.

        See :class:`ValidationMode` enumeration for the supported
        validation modes.

        :param ValidationMode mode: The mode of selection validation to use.
        """
        assert isinstance(mode, self.ValidationMode)
        if mode != self._validationMode:
            self._validationMode = mode
            if self.isStarted():
                self._updateStatusMessage()

    def getColor(self):
        """Return the color of the selections

        :rtype: QColor
        """
        return qt.QColor.fromRgbF(*self._color)

    def setColor(self, color):
        """Set the color to use for selections.

        Existing selections are not affected.

        :param color: The color to use for displaying selections as
           either a color name, a QColor, a list of uint8 or float in [0, 1].
        """
        self._color = rgba(color)

    # Status message

    def getStatusMessage(self):
        """Returns the current status message.

        This message is meant to be displayed in a status bar.

        :rtype: str
        """
        return self._statusMessage

    def _updateStatusMessage(self, message=None, extra=None):
        """Set the status message.

        :param str message: The main message or None to use default message
        :param str extra: Additional info to display after main message
        """
        if message is None:
            selections = self.getSelections()
            if self._nbSelection is None:
                message = 'Select %ss (%d selected)' % (
                    self._shapeKind, len(selections))

            elif self._nbSelection <= 1:
                message = 'Select a %s' % self._shapeKind
            else:
                message = 'Select %d/%d %ss' % (
                    len(selections), self._nbSelection, self._shapeKind)

            if self.getValidationMode() == self.ValidationMode.ENTER:
                message += ' - Press Enter to validate'

        else:
            message = str(message)

        if extra is not None:
            message += ' (' + str(extra) + ')'

        if self._statusMessage != message:
            self._statusMessage = message
            self.sigMessageChanged.emit(message)

    # Control selection

    def isStarted(self):
        """Returns True if the selection is requesting user input.

        :rtype: bool"""
        return self._isStarted

    def start(self, count=1, kind='point'):
        """Start an interactive selection.

        :param int count: The maximum number of selections to request
            If count is None, there is no limit of number of selection.
        :param str kind: The kind of shape to select in:
           'point', 'rectangle', 'line', 'polygon', 'hline', 'vline'
        """
        self.cancel()
        self.clearSelections()

        plot = self.parent()
        if plot is None:
            raise RuntimeError('No plot to perform selection')

        assert kind in ('point', 'rectangle', 'line',
                        'polygon', 'hline', 'vline')
        self._shapeKind = kind
        self._nbSelection = count

        self._isStarted = True
        self._startSelectionInteraction()

        self.getSelectionModeAction().setEnabled(True)

        plot.installEventFilter(self)

        self._updateStatusMessage()

        self.sigSelectionStarted.emit(kind)

    def _terminateSelection(self):
        """Terminate a selection.

        :return: True if a selection was running, False otherwise
        """
        if not self.isStarted():
            return False

        plot = self.parent()
        if plot is not None:
            plot.removeEventFilter(self)
            plot.setInteractiveMode('zoom')

        self._stopSelectionInteraction(resetInteractiveMode=False)

        self._isStarted = False
        self._nbSelection = 0

        self.getSelectionModeAction().setEnabled(False)

        if self._eventLoop is not None:
            self._eventLoop.quit()

        return True

    def cancel(self):
        """Cancel interactive selection.

        Current selections are reset.

        :return: True if a selection was actually cancelled
        :rtype: bool
        """
        if self._terminateSelection():
            self.clearSelections()
            self.sigSelectionFinished.emit(self.getSelectionPoints())
            self._updateStatusMessage('Selection cancelled')
            return True
        else:
            return False

    def stop(self):
        """Stop interactive selection

        :return: True if a selection was actually cancelled
        :rtype: bool
        """
        if self._terminateSelection():
            self.sigSelectionFinished.emit(self.getSelectionPoints())
            self._updateStatusMessage('Selection done')
            return True
        else:
            return False

    def exec_(self, count=1, kind='point', timeout=0):
        """Block until selection is done or timeout is elapsed.

        :param int count: The number of selection to request.
           Use None for an undefined number of selection.
        :param str kind: The kind of shape to select in:
           'point', 'rectangle', 'line', 'polygon', 'hline', 'vline'
        :param int timeout: Maximum duration in seconds to block.
            Default: No timeout
        :return: The current selection
        :rtype: tuple
        """
        self.start(count=count, kind=kind)

        plot = self.parent()
        plot.show()
        plot.raise_()

        self._eventLoop = qt.QEventLoop()
        if timeout != 0:
            timer = qt.QTimer()
            timer.timeout.connect(self._eventLoop.quit)
            timer.start(int(timeout) * 1000)
            self._eventLoop.exec_()
            timer.stop()

        else:
            self._eventLoop.exec_()
        self._eventLoop = None

        self.stop()

        selection = self.getSelectionPoints()
        self.clearSelections()
        return selection
