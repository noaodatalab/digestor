# Licensed under a MIT style license - see LICENSE.rst
# -*- coding: utf-8 -*-
"""Test digestor.sdss.
"""
import unittest
import unittest.mock as mock
from tempfile import NamedTemporaryFile

from ..sdss import SDSS, get_options
from .utils import DigestorCase

class TestSDSS(DigestorCase):
    """Test digestor.sdss.
    """

    def setUp(self):
        super().setUp()
        self.schema = 'sdss'
        self.table = 'spectra'
        self.description = 'sdss spectra'
        self.sdss = SDSS(self.schema, self.table,
                         description=self.description)

    def test_get_options(self):
        """Test command-line arguments.
        """
        with mock.patch('sys.argv', ['sdss2dl', '-r', 'plug_ra', '-t', 'specobjall',
                                     'specObj-dr14.fits', 'specobjall.sql']):
            self.options = get_options()
        self.assertEqual(self.options.sql, 'specobjall.sql')
        self.assertFalse(self.options.verbose)
        self.assertEqual(self.options.table, 'specobjall')
        self.assertEqual(self.options.schema, 'sdss_dr14')
        self.assertIsNone(self.options.output_sql)
        self.assertIsNone(self.options.output_json)
        self.assertIsNone(self.options.merge_json)

    def test_parse_sql(self):
        """Test parsing a whole SQL file.
        """
        sql = r"""CREATE TABLE specObjAll(
--/H This is a description.
  foo real NOT NULL, --/D this is a column
)
"""
        with NamedTemporaryFile('w+') as f:
            f.write(sql)
            f.seek(0)
            self.sdss.parseSQL(f.name)

    def test_parse_line(self):
        """Test parsing single SQL lines.
        """
        self.sdss.parseLine(r'CREATE TABLE specObjAll  (  ')
        self.sdss.parseLine('--')
        self.sdss.parseLine('--/H This is the short description')
        self.assertEqual(self.sdss.tapSchema['tables'][0]['description'], 'This is the short description')
        self.sdss.parseLine('--/T This is the long description')
        # self.assertEqual(self.sdss.tapSchema['tables'][0]['description'], 'This is the long description\nThis is the long description\n')
        self.sdss.parseLine('   column int NOT NULL, --/U mm --/D Column description --/F MY_COLUMN')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['column_name'], 'column')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['datatype'], 'integer')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['unit'], 'mm')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['description'], 'Column description')
        self.assertEqual(self.sdss.mapping['column'], 'MY_COLUMN')
        self.sdss.parseLine('   column2 real NOT NULL, --/U deg --/D Column description --/F RA')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['column_name'], 'column2')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['datatype'], 'real')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['unit'], 'deg')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['description'], 'Column description')
        self.assertEqual(self.sdss.mapping['column2'], 'RA')
        self.sdss.parseLine('   column3 varchar(16) NOT NULL, --/K UCD --/D Column description --/F RA')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['column_name'], 'column3')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['datatype'], 'character')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['size'], 16)
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['unit'], '')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['ucd'], 'UCD')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['description'], 'Column description')
        self.sdss.parseLine('   column4 float NOT NULL, --/K UCD --/D Column description --/F DEC')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['column_name'], 'column4')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['datatype'], 'double')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['size'], 1)
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['unit'], '')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['ucd'], 'UCD')
        self.assertEqual(self.sdss.tapSchema['columns'][-1]['description'], 'Column description')
        self.sdss.parseLine('    loadVersion  int NOT NULL, --/D Load Version --/K ID_TRACER --/F NOFITS')
        # self.sdss.parseLine('    z real NOT NULL, --/D Redshift')
        self.sdss.parseLine('    snMedian_u real NOT NULL, --/D S/N --/F sn_median 0')
        self.assertEqual(self.sdss.mapping['snmedian_u'], 'SN_MEDIAN[0]')
        self.sdss.parseLine('  ); ')

    def test_parse_column_metadata(self):
        """Test parsing metadata of individual columns.
        """
        d, r = self.sdss.parseColumnMetadata('foo', '--/U mm --/D Random column.')
        self.assertEqual(d['unit'], 'mm')
        self.assertEqual(d['description'], 'Random column.')
        d, r = self.sdss.parseColumnMetadata('foo', '--/F bar --/K ID_CATALOG --/D Random column.')
        self.assertEqual(d['ucd'], 'ID_CATALOG')
        self.assertEqual(d['description'], 'Random column.')
        self.assertEqual(r, 'BAR')
        d, r = self.sdss.parseColumnMetadata('mag_g', '--/F mag 1 --/D Random column.')
        self.assertEqual(d['description'], 'Random column.')
        self.assertEqual(r, 'MAG[1]')
        d, r = self.sdss.parseColumnMetadata('extra', '--/F NOFITS --/D Random column. --/U arcsec')
        self.assertEqual(d['unit'], 'arcsec')
        self.assertEqual(d['description'], 'Random column.')
        d, r = self.sdss.parseColumnMetadata('flux_u', '--/U nanomaggies --/D Random column.')
        self.assertEqual(d['unit'], 'nanomaggies')
        self.assertEqual(d['description'], 'Random column.')

    def test_map_columns(self):
        """Test mapping of FITS columns to SQL columns.
        """
        self.sdss.tapSchema['columns'] += [{"table_name": self.table,
                                            "column_name": "mag_u",
                                            "description": "u Magnitude",
                                            "unit": "", "ucd": "", "utype": "",
                                            "datatype": "real", "size": 1,
                                            "principal": 0, "indexed": 0, "std": 0},
                                           {"table_name": self.table,
                                            "column_name": "mag_g",
                                            "description": "g Magnitude",
                                            "unit": "", "ucd": "", "utype": "",
                                            "datatype": "real", "size": 1,
                                            "principal": 0, "indexed": 0, "std": 0},
                                           {"table_name": self.table,
                                            "column_name": "magivar_u",
                                            "description": "u ivar",
                                            "unit": "", "ucd": "", "utype": "",
                                            "datatype": "real", "size": 1,
                                            "principal": 0, "indexed": 0, "std": 0},
                                           {"table_name": self.table,
                                            "column_name": "magivar_g",
                                            "description": "g ivar",
                                            "unit": "", "ucd": "", "utype": "",
                                            "datatype": "real", "size": 1,
                                            "principal": 0, "indexed": 0, "std": 0}]
        self.sdss.mapping = {'mag_u': 'MAG[0]', 'mag_g': 'MAG[1]',
                             'magivar_u': 'MAGIVAR[0]', 'magivar_g': 'MAGIVAR[1]'}
        self.sdss.FITS = {'e_lon': 'D', 'e_lat': 'D',
                          'g_lon': 'D', 'g_lat': 'D',
                          'HTM9': 'J', 'ring256': 'J',
                          'nest4096': 'J', 'MAG': '2E',
                          'MAG_IVAR': '2E',
                          'FOOBAR': '16A'}
        self.sdss.mapColumns()
        final_mapping = {'mag_u': 'MAG[0]', 'mag_g': 'MAG[1]',
                         'magivar_u': 'MAG_IVAR[0]', 'magivar_g': 'MAG_IVAR[1]',
                         'htm9': 'HTM9', 'ring256': 'ring256', 'nest4096': 'nest4096',
                         'glon': 'g_lon', 'glat': 'g_lat',
                         'elon': 'e_lon', 'elat': 'e_lat'}
        self.assertDictEqual(self.sdss.mapping, final_mapping)
        self.assertLog(-1, 'FITS column FOOBAR will be dropped from SQL!')
        self.sdss.tapSchema['columns'] += [{"table_name": self.table,
                                            "column_name": "flux_u",
                                            "description": "u flux",
                                            "unit": "", "ucd": "", "utype": "",
                                            "datatype": "real", "size": 1,
                                            "principal": 0, "indexed": 0, "std": 0},
                                           {"table_name": self.table,
                                            "column_name": "flux_g",
                                            "description": "g flux",
                                            "unit": "", "ucd": "", "utype": "",
                                            "datatype": "real", "size": 1,
                                            "principal": 0, "indexed": 0, "std": 0},]
        self.sdss.mapping = {'mag_u': 'MAG[0]', 'mag_g': 'MAG[1]',
                             'magivar_u': 'MAGIVAR[0]', 'magivar_g': 'MAGIVAR[1]',
                             'flux_u': 'FLUX[0]', 'flux_g': 'FLUX[1]'}
        with self.assertRaises(KeyError) as e:
            self.sdss.mapColumns()
        self.assertEqual(e.exception.args[0], 'Could not find a FITS column corresponding to flux_u!')
        self.sdss.FITS['FLUX'] = '2E'
        self.sdss.tapSchema['columns'] += [{"table_name": self.table,
                                            "column_name": "z",
                                            "description": "z",
                                            "unit": "", "ucd": "", "utype": "",
                                            "datatype": "real", "size": 1,
                                            "principal": 0, "indexed": 0, "std": 0},]
        self.sdss.mapping = {'mag_u': 'MAG[0]', 'mag_g': 'MAG[1]',
                             'magivar_u': 'MAGIVAR[0]', 'magivar_g': 'MAGIVAR[1]',
                             'flux_u': 'FLUX[0]', 'flux_g': 'FLUX[1]'}
        with self.assertRaises(KeyError) as e:
            self.sdss.mapColumns()
        self.assertEqual(e.exception.args[0], 'Could not find a FITS column corresponding to z!')


def test_suite():
    """Allows testing of only this module with the command::

        python setup.py test -m <modulename>
    """
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
