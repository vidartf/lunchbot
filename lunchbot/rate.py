
from datetime import date
from itertools import combinations
from functools import partial

from .use_historical import iter_menus

try:
    input = raw_input
except NameError: #Python 3
    pass


def all_menu_pairs():
    return combinations(iter_menus(), 2)


import sqlite3
_db = None

def _connect():
    global _db
    _db = sqlite3.connect('comparisons.sqlite')
    _db.execute('''
        CREATE TABLE IF NOT EXISTS
        comparison (
            a INTEGER NOT NULL,
            b INTEGER NOT NULL,
            cmp INTEGER,
            PRIMARY KEY(a, b)
        ) WITHOUT ROWID;
    ''')
    _db.execute('''
        CREATE TABLE IF NOT EXISTS
        rating (
            id INTEGER PRIMARY KEY,
            rating INTEGER
        ) WITHOUT ROWID;
    ''')

epoch = date(2010, 1, 1)

def _dbkey(e):
    d = e.date - epoch
    return 10 * d.days + (1 if e.floor == 'third' else 0)


def _previous(a, b):
    rows = _db.execute('''
        SELECT cmp FROM (
            SELECT * FROM comparison
            WHERE a = ? AND b = ?
        )
        LIMIT 1
    ''', (_dbkey(a), _dbkey(b)))
    for r in rows:
        return r[0]
    return None

def prompt_comparison(a, b):
    prev = _previous(a, b)
    if prev is not None:
        return prev
    print('Choose the best menu:') 
    print('=' * 60)
    print(a.menu)
    print('-' * 60)
    print(b.menu)
    print('-' * 60)
    res = 0
    while True:
        reply = input('[a/b]:')
        if reply == 'a':
            res = -1
            break
        elif reply == 'b':
            res = 1
            break
    _db.execute('''
        INSERT INTO comparison (a, b, cmp)
        VALUES (?, ?, ?)
    ''', (_dbkey(a), _dbkey(b), res))
    return res


try:
    from functools import cmp_to_key
    _sort_menus = partial(sorted, key=cmp_to_key(prompt_comparison))
except ImportError:
    _sort_menus = partial(sorted, cmp=prompt_comparison)


def prompt_sort(entries):
    return _sort_menus(entries)


def get_rate(entry):
    rows = _db.execute('''
        SELECT id, rating
        FROM rating
        WHERE id = ?
        LIMIT 1
    ''', (_dbkey(entry),))
    for r in rows:
        return r[1]
    return None

def rate(entry):
    prev = get_rate(entry)
    if prev is not None:
        return prev
    print('Rate the menu:')
    print(entry.menu)
    print('-' * 60)
    res = 0
    while True:
        reply = input('[0-100]:')
        try:
            res = int(reply)
            break
        except ValueError:
            pass
    _db.execute('''
        INSERT INTO rating (id, rating)
        VALUES (?, ?)
    ''', (_dbkey(entry), res))
    return res


if __name__ == '__main__':
    from .main import logger
    logger.setLevel('ERROR')
    _connect()
    try:
        for e in iter_menus():
            rate(e)
        print('All menus are rated!')
    except KeyboardInterrupt:
        pass
    finally:
        _db.commit()
        _db.close()
