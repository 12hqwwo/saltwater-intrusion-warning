"""Offline checks. Database transaction/idempotence tests are in README."""
import csv
import io
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import etl_csv as etl

ROOT = Path(__file__).resolve().parents[2]
# Preserve support for the earlier flat fixture directory when explicitly set.
FIXTURE_DIR = os.environ.get("WEBGIS_TEST_DATA_DIR")
PROJECT_FILES = {
    "mrc_mytho.csv": ROOT / "data/raw/mrc_conductivity/Conductivity.Water Quality@VN_019805_[My Tho].csv",
    "mrc_tanchau.csv": ROOT / "data/raw/mrc_conductivity/Conductivity.Water Quality@VN_019803_[Tan Chau].csv",
    "master_timeseries.csv": ROOT / "data/processed/master_timeseries.csv",
}


def data_file(name):
    return Path(FIXTURE_DIR) / name if FIXTURE_DIR else PROJECT_FILES[name]


def encode(rows, headers):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.content = data_file('mrc_mytho.csv').read_bytes()
        self.row = list(csv.DictReader(io.StringIO(self.content.decode('utf-8-sig'))))[0]

    def test_source_counts_and_monthly_missing(self):
        for filename,station,n in [('mrc_mytho.csv','019805',463),('mrc_tanchau.csv','019803',464)]:
            rows,rejects,total=etl.validate(data_file(filename).read_bytes(),'raw',station)
            self.assertEqual((len(rows),len(rejects),total),(n,0,n))
        rows,rejects,total=etl.validate(data_file('master_timeseries.csv').read_bytes(),'master')
        self.assertEqual((len(rows),len(rejects),total),(1000,0,1000))
        self.assertEqual(sum(r['conductivity_ms_per_m'] is not None for r in rows),927)
        self.assertIsNone(rows[0]['conductivity_ms_per_m'])

    def test_negative_wrong_unit_and_naive_time(self):
        for field,value in [('Value','-1'),('Unit','g/L'),('Timestamp (UTC+07:00)','2020-01-01T00:00')]:
            with self.subTest(field=field):
                row={**self.row,field:value}
                rows,rejects,total=etl.validate(encode([row],etl.RAW_HEADERS),'raw','019805')
                self.assertEqual((len(rows),len(rejects)),(0,1))

    def test_nonfinite_ec_and_station_mismatch(self):
        for field,value in [('Value','nan'),('Value','inf'),('Station Code','019803')]:
            rows,rejects,total=etl.validate(encode([{**self.row,field:value}],etl.RAW_HEADERS),'raw','019805')
            self.assertEqual((len(rows),len(rejects)),(0,1))

    def test_all_duplicate_rows_rejected(self):
        rows,rejects,total=etl.validate(encode([self.row,self.row],etl.RAW_HEADERS),'raw','019805')
        self.assertEqual((len(rows),len(rejects),total),(0,2,2))

    def test_sql_literal_is_not_executable_data(self):
        value="O'Brien; DROP TABLE x; -- \\"
        self.assertEqual(etl.literal(value),"'O''Brien; DROP TABLE x; -- \\'")

    def test_database_identifier_rejected(self):
        with self.assertRaises(ValueError):
            etl.make_sql([], 'raw', '019805','x.csv','0'*64,'x;drop')

    def test_bad_month_and_humidity(self):
        data=data_file('master_timeseries.csv').read_text(encoding='utf-8-sig')
        original=next(csv.DictReader(io.StringIO(data)))
        for field,value in [('month_start','2020-01-02'),('humidity_mean','101')]:
            rows,rejects,total=etl.validate(encode([{**original,field:value}],etl.MASTER_HEADERS),'master')
            self.assertEqual((len(rows),len(rejects)),(0,1))


if __name__=='__main__':
    unittest.main()
