import os

import sqlalchemy.orm as orm
from nose.tools import assert_equal, assert_raises, assert_in
import datetime
from decimal import Decimal

from ckan.common import config
from ckan.tests import helpers, factories
import ckanext.datastore.backend.postgres as db
from ckanext.shift import loader
from ckanext.shift.job_exceptions import LoaderError

import ckan.plugins as p
import util

def get_sample_filepath(filename):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), 'samples',
                                        filename))


class TestLoadBase(util.PluginsMixin):
    _load_plugins = ['datastore']

    def setup(self):
        engine = db.get_write_engine()
        self.Session = orm.scoped_session(orm.sessionmaker(bind=engine))
        helpers.reset_db()
        util.reset_datastore_db()

    def teardown(self):
        self.Session.close()

    def _get_records(self, table_name, limit=None,
                     exclude_full_text_column=True):
        c = self.Session.connection()
        if exclude_full_text_column:
            cols = self._get_column_names(table_name)
            cols = ', '.join('"{}"'.format(col) for col in cols
                             if col != '_full_text')
        else:
            cols = '*'
        sql = 'SELECT {cols} FROM "{table_name}"' \
            .format(cols=cols, table_name=table_name)
        if limit is not None:
            sql += ' LIMIT {}'.format(limit)
        results = c.execute(sql)
        return results.fetchall()

    def _get_column_names(self, table_name):
        # SELECT column_name FROM information_schema.columns WHERE table_name='test1';
        c = self.Session.connection()
        sql = "SELECT column_name FROM information_schema.columns " \
              "WHERE table_name='{}';".format(table_name)
        results = c.execute(sql)
        records = results.fetchall()
        return [r[0] for r in records]

    def _get_column_types(self, table_name):
        c = self.Session.connection()
        sql = "SELECT udt_name FROM information_schema.columns " \
              "WHERE table_name='{}';".format(table_name)
        results = c.execute(sql)
        records = results.fetchall()
        return [r[0] for r in records]


class TestLoadCsv(TestLoadBase):

    def test_simple(self):
        csv_filepath = get_sample_filepath('simple.csv')
        resource_id = 'test1'
        factories.Resource(id=resource_id)
        loader.load_csv(csv_filepath, resource_id=resource_id,
                        mimetype='text/csv', logger=loader.PrintLogger())

        assert_equal(self._get_records(
            'test1', limit=1, exclude_full_text_column=False),
                     [(1, "'-01':2,3 '1':4 '2011':1 'galway':5", u'2011-01-01', u'1', u'Galway')])
        assert_equal(self._get_records('test1'),
                     [(1, u'2011-01-01', u'1', u'Galway'),
                      (2, u'2011-01-02', u'-1', u'Galway'),
                      (3, u'2011-01-03', u'0', u'Galway'),
                      (4, u'2011-01-01', u'6', u'Berkeley'),
                      (5, u'2011-01-02', u'8', u'Berkeley'),
                      (6, u'2011-01-03', u'5', u'Berkeley')])
        assert_equal(
            self._get_column_names('test1'),
            [u'_id', u'_full_text', u'date', u'temperature', u'place'])
        assert_equal(
            self._get_column_types('test1'),
            [u'int4', u'tsvector', u'text', u'text', u'text'])

    def test_boston_311(self):
        csv_filepath = get_sample_filepath('boston_311_sample.csv')
        resource_id = 'test1'
        factories.Resource(id=resource_id)
        loader.load_csv(csv_filepath, resource_id=resource_id,
                        mimetype='text/csv', logger=loader.PrintLogger())

        records = self._get_records('test1')
        print records
        assert_equal(
            records,
            [(1, u'101002153891', u'2017-07-06 23:38:43', u'2017-07-21 08:30:00', None, u'ONTIME', u'Open', u' ', u'Street Light Outages', u'Public Works Department', u'Street Lights', u'Street Light Outages', u'PWDx_Street Light Outages', u'PWDx', None, None, u'480 Harvard St  Dorchester  MA  02124', u'8', u'07', u'4', u'B3', u'Greater Mattapan', u'9', u'Ward 14', u'1411', u'480 Harvard St', u'02124', u'42.288', u'-71.0927', u'Citizens Connect App'),
             (2, u'101002153890', u'2017-07-06 23:29:13', u'2017-09-11 08:30:00', None, u'ONTIME', u'Open', u' ', u'Graffiti Removal', u'Property Management', u'Graffiti', u'Graffiti Removal', u'PROP_GRAF_GraffitiRemoval', u'PROP', u' https://mayors24.cityofboston.gov/media/boston/report/photos/595f0000048560f46d94b9fa/report.jpg', None, u'522 Saratoga St  East Boston  MA  02128', u'1', u'09', u'1', u'A7', u'East Boston', u'1', u'Ward 1', u'0110', u'522 Saratoga St', u'02128', u'42.3807', u'-71.0259', u'Citizens Connect App'),
             (3, u'101002153889', u'2017-07-06 23:24:20', u'2017-09-11 08:30:00', None, u'ONTIME', u'Open', u' ', u'Graffiti Removal', u'Property Management', u'Graffiti', u'Graffiti Removal', u'PROP_GRAF_GraffitiRemoval', u'PROP', u' https://mayors24.cityofboston.gov/media/boston/report/photos/595efedb048560f46d94b9ef/report.jpg', None, u'965 Bennington St  East Boston  MA  02128', u'1', u'09', u'1', u'A7', u'East Boston', u'1', u'Ward 1', u'0112', u'965 Bennington St', u'02128', u'42.386', u'-71.008', u'Citizens Connect App')]
            )
        print self._get_column_names('test1')
        assert_equal(
            self._get_column_names('test1'),
            [u'_id', u'_full_text', u'CASE_ENQUIRY_ID', u'open_dt', u'target_dt', u'closed_dt', u'OnTime_Status', u'CASE_STATUS', u'CLOSURE_REASON', u'CASE_TITLE', u'SUBJECT', u'REASON', u'TYPE', u'QUEUE', u'Department', u'SubmittedPhoto', u'ClosedPhoto', u'Location', u'Fire_district', u'pwd_district', u'city_council_district', u'police_district', u'neighborhood', u'neighborhood_services_district', u'ward', u'precinct', u'LOCATION_STREET_NAME', u'LOCATION_ZIPCODE', u'Latitude', u'Longitude', u'Source'])
        print self._get_column_types('test1')
        assert_equal(self._get_column_types('test1'),
                     [u'int4', u'tsvector'] +
                     [u'text'] * (len(records[0]) - 1))

    def test_reload(self):
        csv_filepath = get_sample_filepath('simple.csv')
        resource_id = 'test1'
        factories.Resource(id=resource_id)
        loader.load_csv(csv_filepath, resource_id=resource_id,
                        mimetype='text/csv', logger=loader.PrintLogger())

        # Load it again unchanged
        loader.load_csv(csv_filepath, resource_id=resource_id,
                        mimetype='text/csv', logger=loader.PrintLogger())

        assert_equal(len(self._get_records('test1')), 6)
        assert_equal(
            self._get_column_names('test1'),
            [u'_id', u'_full_text', u'date', u'temperature', u'place'])
        assert_equal(
            self._get_column_types('test1'),
            [u'int4', u'tsvector', u'text', u'text', u'text'])

    def test_reload_with_overridden_types(self):
        csv_filepath = get_sample_filepath('simple.csv')
        resource_id = 'test1'
        factories.Resource(id=resource_id)
        loader.load_csv(csv_filepath, resource_id=resource_id,
                        mimetype='text/csv', logger=loader.PrintLogger())
        # Change types, as it would be done by Data Dictionary
        rec = p.toolkit.get_action('datastore_search')(None, {
            'resource_id': resource_id,
            'limit': 0})
        fields = [f for f in rec['fields'] if not f['id'].startswith('_')]
        fields[0]['info'] = {'type_override': 'timestamp'}
        fields[1]['info'] = {'type_override': 'numeric'}
        p.toolkit.get_action('datastore_create')({'ignore_auth': True}, {
            'resource_id': resource_id,
            'force': True,
            'fields': fields
            })
        # [{
        #         'id': f['id'],
        #         'type': f['type'],
        #         'info': fi if isinstance(fi, dict) else {}
        #         } for f, fi in izip_longest(fields, info)]

        # Load it again with new types
        loader.load_csv(csv_filepath, resource_id=resource_id,
                        mimetype='text/csv', logger=loader.PrintLogger())

        assert_equal(len(self._get_records('test1')), 6)
        assert_equal(
            self._get_column_names('test1'),
            [u'_id', u'_full_text', u'date', u'temperature', u'place'])
        assert_equal(
            self._get_column_types('test1'),
            [u'int4', u'tsvector', u'timestamp', u'numeric', u'text'])


class TestLoadUnhandledTypes(TestLoadBase):

    def test_kml(self):
        filepath = get_sample_filepath('polling_locations.kml')
        resource_id = 'test1'
        factories.Resource(id=resource_id)
        with assert_raises(LoaderError) as exception:
            loader.load_csv(filepath, resource_id=resource_id,
                            mimetype='text/csv', logger=loader.PrintLogger())
        assert_in('Error with field definition',
                  str(exception.exception))
        assert_in('"<?xml version="1.0" encoding="utf-8" ?>" is not a valid field name',
                  str(exception.exception))

    def test_geojson(self):
        filepath = get_sample_filepath('polling_locations.geojson')
        resource_id = 'test1'
        factories.Resource(id=resource_id)
        with assert_raises(LoaderError) as exception:
            loader.load_csv(filepath, resource_id=resource_id,
                            mimetype='text/csv', logger=loader.PrintLogger())
        assert_in('Error with field definition',
                  str(exception.exception))
        assert_in('"{"type":"FeatureCollection"" is not a valid field name',
                  str(exception.exception))

    def test_shapefile_zip(self):
        filepath = get_sample_filepath('polling_locations.shapefile.zip')
        resource_id = 'test1'
        factories.Resource(id=resource_id)
        with assert_raises(LoaderError) as exception:
            loader.load_csv(filepath, resource_id=resource_id,
                            mimetype='text/csv', logger=loader.PrintLogger())
        assert_in('Error during the load into PostgreSQL: '
                  'unquoted carriage return found in data',
                  str(exception.exception))


class TestLoadXls(TestLoadBase):

    def test_simple(self):
        csv_filepath = get_sample_filepath('simple.xls')
        resource_id = 'test1'
        factories.Resource(id=resource_id)
        loader.load_table(csv_filepath, resource_id=resource_id,
                          mimetype='xls', logger=loader.PrintLogger())

        assert_equal(self._get_records(
            'test1', limit=1, exclude_full_text_column=False),
            [(1,
              "'-01':2,3 '00':4,5,6 '1':7 '2011':1 'galway':8",
              datetime.datetime(2011, 1, 1, 0, 0),
              Decimal('1'),
              u'Galway')])
        assert_equal(
            self._get_records('test1'),
            [(1, datetime.datetime(2011, 1, 1, 0, 0), Decimal('1'), u'Galway'),
             (2, datetime.datetime(2011, 1, 2, 0, 0), Decimal('-1'), u'Galway'),
             (3, datetime.datetime(2011, 1, 3, 0, 0), Decimal('0'), u'Galway'),
             (4, datetime.datetime(2011, 1, 1, 0, 0), Decimal('6'), u'Berkeley'),
             (5, datetime.datetime(2011, 1, 2, 0, 0), Decimal('8'), u'Berkeley'),
             (6, datetime.datetime(2011, 1, 3, 0, 0), Decimal('5'), u'Berkeley')])
        assert_equal(
            self._get_column_names('test1'),
            [u'_id', u'_full_text', u'date', u'temperature', u'place'])
        assert_equal(
            self._get_column_types('test1'),
            [u'int4', u'tsvector', u'timestamp', u'numeric', u'text'])
