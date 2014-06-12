# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from contextlib import contextmanager
import MySQLdb
@contextmanager
def sqlSession(toRead,whichDb='cs277',host='127.0.0.1'):#'128.200.36.136'):
    cnxn = MySQLdb.connect(host=host, port=3306,user='cs277read' if toRead else 'cs277write', passwd='LoveTaiwan2014',db=whichDb)
    print('connection established')
    yield cnxn #return an opened connection, and execute what's contained in the with statement
    cnxn.commit() # commit all changes
    cnxn.close()
    print('connection closed')
