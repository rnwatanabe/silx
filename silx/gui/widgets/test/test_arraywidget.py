# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2016 European Synchrotron Radiation Facility
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
__authors__ = ["P. Knobel"]
__license__ = "MIT"
__date__ = "05/12/2016"

import unittest
import numpy
import tempfile
import os

from .. import ArrayTableWidget
from ...test.utils import TestCaseQt
from silx.gui import qt

try:
    import h5py
except ImportError:
    h5py = None


class TestArrayWidget(TestCaseQt):
    """Basic test for ArrayTableWidget with a numpy array"""
    def setUp(self):
        super(TestArrayWidget, self).setUp()
        self.aw = ArrayTableWidget.ArrayTableWidget()

    def tearDown(self):
        del self.aw
        super(TestArrayWidget, self).tearDown()

    def testShow(self):
        """test for errors"""
        self.aw.show()
        self.qWaitForWindowExposed(self.aw)

    def testSetData0D(self):
        a = 1
        self.aw.setArrayData(a)
        b = self.aw.getData(copy=True)

        self.assertTrue(numpy.array_equal(a, b))

        # scalar/0D data has no frame index
        self.assertEqual(len(self.aw.model._index), 0)
        # and no perspective
        self.assertEqual(len(self.aw.model._perspective), 0)

    def testSetData1D(self):
        a = [1, 2]
        self.aw.setArrayData(a)
        b = self.aw.getData(copy=True)

        self.assertTrue(numpy.array_equal(a, b))

        # 1D data has no frame index
        self.assertEqual(len(self.aw.model._index), 0)
        # and no perspective
        self.assertEqual(len(self.aw.model._perspective), 0)

    def testSetData4D(self):
        """test for errors"""
        a = numpy.reshape(numpy.linspace(0.213, 1.234, 1250),
                          (5, 5, 5, 10))
        self.aw.setArrayData(a)

        # default perspective (0, 1)
        self.assertEqual(list(self.aw.model._perspective),
                         [0, 1])
        self.aw.setPerspective((1, 3))
        self.assertEqual(list(self.aw.model._perspective),
                         [1, 3])

        b = self.aw.getData(copy=True)
        self.assertTrue(numpy.array_equal(a, b))

        # 4D data has a 2-tuple as frame index
        self.assertEqual(len(self.aw.model._index), 2)
        # default index is (0, 0)
        self.assertEqual(list(self.aw.model._index),
                         [0, 0])
        self.aw.setFrameIndex((3, 1))

        self.assertEqual(list(self.aw.model._index),
                         [3, 1])

    def testDefaultFlagNotEditable(self):
        """editable should be False by default, in setArrayData"""
        self.aw.setArrayData([[0]])
        idx = self.aw.model.createIndex(0, 0)
        # model is editable
        self.assertFalse(
                self.aw.model.flags(idx) & qt.Qt.ItemIsEditable)

    def testFlagEditable(self):
        self.aw.setArrayData([[0]], editable=True)
        idx = self.aw.model.createIndex(0, 0)
        # model is editable
        self.assertTrue(
                self.aw.model.flags(idx) & qt.Qt.ItemIsEditable)

    def testFlagNotEditable(self):
        self.aw.setArrayData([[0]], editable=False)
        idx = self.aw.model.createIndex(0, 0)
        # model is editable
        self.assertFalse(
                self.aw.model.flags(idx) & qt.Qt.ItemIsEditable)

    def testReferenceReturned(self):
        """when setting the data with copy=False and
        retrieving it with getData(copy=False), we should recover
        the same original object.
        """
        # n-D (n >=2)
        a0 = numpy.reshape(numpy.linspace(0.213, 1.234, 1000),
                           (10, 10, 10))
        self.aw.setArrayData(a0, copy=False)
        a1 = self.aw.getData(copy=False)

        self.assertIs(a0, a1)

        # 1D
        b0 = numpy.linspace(0.213, 1.234, 1000)
        self.aw.setArrayData(b0, copy=False)
        b1 = self.aw.getData(copy=False)
        self.assertIs(b0, b1)


@unittest.skipIf(h5py is None, "Could not import h5py")
class TestH5pyArrayWidget(TestCaseQt):
    """Basic test for ArrayTableWidget with a dataset.

    Test flags, for dataset open in read-only or read-write modes"""
    def setUp(self):
        super(TestH5pyArrayWidget, self).setUp()
        self.aw = ArrayTableWidget.ArrayTableWidget()
        self.data = numpy.reshape(numpy.linspace(0.213, 1.234, 1000),
                                  (10, 10, 10))
        # create an h5py file with a dataset
        self.tempdir = tempfile.mkdtemp()
        self.h5_fname = os.path.join(self.tempdir, "array.h5")
        h5f = h5py.File(self.h5_fname)
        h5f["my_array"] = self.data
        h5f["my_scalar"] = 3.14
        h5f["my_1D_array"] = numpy.array(numpy.arange(1000))
        h5f.close()

    def tearDown(self):
        del self.aw
        os.unlink(self.h5_fname)
        os.rmdir(self.tempdir)
        super(TestH5pyArrayWidget, self).tearDown()

    def testShow(self):
        self.aw.show()
        self.qWaitForWindowExposed(self.aw)

    def testReadOnly(self):
        """Open H5 dataset in read-only mode, ensure the model is not editable."""
        h5f = h5py.File(self.h5_fname, "r")
        a = h5f["my_array"]
        # ArrayTableModel relies on following condition
        self.assertTrue(a.file.mode == "r")

        self.aw.setArrayData(a, copy=False, editable=True)

        self.assertIsInstance(a, h5py.Dataset)   # simple sanity check
        # internal representation must be a reference to original data (copy=False)
        self.assertIsInstance(self.aw.model._array, h5py.Dataset)
        self.assertTrue(self.aw.model._array.file.mode == "r")

        b = self.aw.getData()
        self.assertTrue(numpy.array_equal(self.data, b))

        # model must have detected read-only dataset and disabled editing
        self.assertFalse(self.aw.model._editable)
        idx = self.aw.model.createIndex(0, 0)
        self.assertFalse(
                 self.aw.model.flags(idx) & qt.Qt.ItemIsEditable)

        # force editing read-only datasets raises IOError
        self.assertRaises(IOError, self.aw.model.setData,
                          idx, 123.4, role=qt.Qt.EditRole)
        h5f.close()

    def testReadWrite(self):
        h5f = h5py.File(self.h5_fname, "r+")
        a = h5f["my_array"]
        self.assertTrue(a.file.mode == "r+")

        self.aw.setArrayData(a, copy=False, editable=True)
        b = self.aw.getData(copy=False)
        self.assertTrue(numpy.array_equal(self.data, b))

        idx = self.aw.model.createIndex(0, 0)
        # model is editable
        self.assertTrue(
                self.aw.model.flags(idx) & qt.Qt.ItemIsEditable)
        h5f.close()

    def testSetData0D(self):
        h5f = h5py.File(self.h5_fname, "r+")
        a = h5f["my_scalar"]
        self.aw.setArrayData(a)
        b = self.aw.getData(copy=True)

        self.assertTrue(numpy.array_equal(a, b))

        h5f.close()

    def testSetData1D(self):
        h5f = h5py.File(self.h5_fname, "r+")
        a = h5f["my_1D_array"]
        self.aw.setArrayData(a)
        b = self.aw.getData(copy=True)

        self.assertTrue(numpy.array_equal(a, b))

        h5f.close()

    def testReferenceReturned(self):
        """when setting the data with copy=False and
        retrieving it with getData(copy=False), we should recover
        the same original object.

        This only works for array with at least 2D. For 1D and 0D
        arrays, a view is created at some point, which  in the case
        of an hdf5 dataset creates a copy."""
        h5f = h5py.File(self.h5_fname, "r+")

        # n-D
        a0 = h5f["my_array"]
        self.aw.setArrayData(a0, copy=False)
        a1 = self.aw.getData(copy=False)
        self.assertIs(a0, a1)

        # 1D
        b0 = h5f["my_1D_array"]
        self.aw.setArrayData(b0, copy=False)
        b1 = self.aw.getData(copy=False)
        self.assertIs(b0, b1)

        h5f.close()


def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestArrayWidget))
    test_suite.addTest(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestH5pyArrayWidget))
    return test_suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')