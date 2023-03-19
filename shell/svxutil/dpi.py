import os
import json
import sqlite3

pub_dpi_mark_file = "/usr/local/*/conf.d/pubdpi.json"
pri_dpi_mark_file = "/usr/local/*/conf.d/pridpi.json"

DPIDB = '/data/vppdpi/app_domain_ip.db'

class DB(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super(DB, cls).__new__(cls)
        return cls._instance

    def __init__(self, dbpath):
        self.db_name = dbpath
        self.connect = sqlite3.connect(self.db_name)
        self.cursor = self.connect.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connect.close()

    def execute_sql(self, sql):
        try:
            self.cursor.execute(sql)
            self.connect.commit()
        except Exception as e:
            self.connect.rollback()

    def executemany_sql(self, sql, data_list):
        try:
            self.cursor.executemany(sql, data_list)
            self.connect.commit()
        except Exception as e:
            self.connect.rollback()
            raise Exception("executemany failed")

class Domain(DB):
    def __init__(self,  table, dbname=DPIDB):
        super(Domain, self).__init__(dbname)
        self.db_name = dbname
        self.tname = table

    def query(self, sql):
        try:
            self.execute_sql(sql)
            domain_data = self.cursor.fetchall()
        except:
            pass
            domain_data = []

        return domain_data

    def insert(self, sql, data):
        inits = []
        inits.append('DELETE FROM %s;' % self.tname)
        # inits.append('DELETE FROM sqlite_sequence WHERE name = "%s";' % self.tname)
        inits.append('VACUUM')
        #清空
        for sql_init in inits:
            try:
                self.execute_sql(sql_init)
            except:
                pass
        try:
            self.executemany_sql(sql, data)
        except:
            pass

class Cidr(DB):
    def __init__(self, table, dbname=DPIDB):
        super(Cidr, self).__init__(dbname)
        self.db_name = dbname
        self.tname = table

    def query(self, sql):
        try:
            self.execute_sql(sql)
            cidr_data = self.cursor.fetchall()
        except:
            pass
            cidr_data = []

        return cidr_data

    def insert(self, sql, data):
        inits = []
        inits.append('DELETE FROM %s;' % self.tname)
        # inits.append('DELETE FROM sqlite_sequence WHERE name = "%s";' % self.tname)
        inits.append('VACUUM')
        #清空
        for sql_init in inits:
            try:
                self.execute_sql(sql_init)
            except:
                pass
        try:
            self.executemany_sql(sql, data)
        except:
            pass

#
def load_files_from_marks():
    dpi_marks = []
    for dpi_mark_file in [pub_dpi_mark_file, pri_dpi_mark_file]:
        if os.path.exists(dpi_mark_file):
            try:
                dpi_mark_confs = json.load(open(dpi_mark_file))
            except:
                dpi_mark_confs = []
            dpi_marks.extend(dpi_mark_confs)
    return dpi_marks

def get_mark_by_app(dpi_marks, app):
    for dpi_mark in dpi_marks:
        if app == dpi_mark.get("dpiKey").strip():
            return dpi_mark["markValue"]
        continue

    return ""
