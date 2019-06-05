import pytest
from sqlite3 import IntegrityError

from restomatic.json_sql_compositor import SQLiteDB, SQLQuery, SQLCompositorBadInput, SQLCompositorBadResult

table_mappers = {
    'test': ['id', 'description', 'value']
}


def test_basic_queries():
    db = SQLiteDB(':memory:', table_mappers)

    db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, description TEXT, value REAL)')

    result = db.insert_mapped('test', {'description': 'test 1', 'value': 0.5})

    db.commit()

    assert result.lastrowid() == 1

    assert db.select_all('test').where(['id', 'isnotnull']).all_mapped() == [{'id': 1, 'description': 'test 1', 'value': 0.5}]

    assert db.select_all('test').where(['id', 'eq', 1]).one() == (1, 'test 1', 0.5)

    assert db.select_all('test').where(['id', 'gt', 1]).one_or_none() is None

    with pytest.raises(SQLCompositorBadResult):
        assert db.select_all('test').where(['id', 'gte', 2]).one()

    db.insert('test', ('description', 'value')).values(('test 2', 1.5))

    db.commit()

    assert db.select_all('test').where(['description', 'like', '%2%']).one_mapped() == {'id': 2, 'description': 'test 2', 'value': 1.5}

    assert db.select_all('test').where(['value', 'lt', 1.3]).one_or_none_mapped() == {'id': 1, 'description': 'test 1', 'value': 0.5}

    db.update_mapped('test', {'value': 2.0}).where(('id', 'eq', 1)).run()

    assert db.select_all('test').where(['id', 'lte', 1]).all() == [(1, 'test 1', 2.0)]

    assert db.select_all('test').count().scalar() == 2

    assert db.select_all('test').limit(1).one() == (1, 'test 1', 2.0)

    assert db.select_all('test').limit(1).offset(1).one() == (2, 'test 2', 1.5)

    assert db.select('test', '*').limit(1).one() == (1, 'test 1', 2.0)

    assert db.select_all('test').order_by('value').all() == [(2, 'test 2', 1.5), (1, 'test 1', 2.0)]

    with pytest.raises(SQLCompositorBadResult):
        assert db.select_all('test').where(['id', 'gte', 2]).scalar()

    assert db.select_all('test').where(['id', 'gte', 3]).one_or_none_mapped() is None

    db.insert_mapped('test', ({'description': 'test 3', 'value': 3.0}, {'description': 'test 4', 'value': 4.4}), autorun=False).run()

    db.commit()

    assert db.select_all('test').all_mapped() == [
        {'id': 1, 'description': 'test 1', 'value': 2.0},
        {'id': 2, 'description': 'test 2', 'value': 1.5},
        {'id': 3, 'description': 'test 3', 'value': 3.0},
        {'id': 4, 'description': 'test 4', 'value': 4.4}
    ]

    with pytest.raises(SQLCompositorBadResult):
        db.select_all('test').where(['id', 'gte', 2]).one()

    assert db.select_all('test').where({'and': [['id', 'gte', 2], ['id', 'lt', 3]]}).one() == (2, 'test 2', 1.5)

    assert db.select_all('test').where(['value', 'isnull']).one_or_none() is None

    assert db.select_all('test').where(['description', 'in', ('test 1', 'test 5')]).one() == (1, 'test 1', 2.0)

    assert db.select_all('test').where(['description', 'not_in', ('test 1', 'test 2', 'test 3')]).one() == (4, 'test 4', 4.4)

    with pytest.raises(RuntimeError):
        db.commit()

    db.commit(no_changes_ok=True)

    db.delete('test').where(('id', 'eq', 4)).run()

    assert db.select_all('test').count().scalar() == 3

    db.delete('test').run()

    db.rollback()

    with pytest.raises(RuntimeError):
        db.commit()

    assert db.select_all('test').get_id(1).one() == (1, 'test 1', 2.0)

    db.close()

    # Should be safe to call multiple times
    db.close()


def description_validator(description, **context):
    assert isinstance(context['db'], SQLiteDB)
    assert context['mode'] in ('WHERE', 'UPDATE', 'INSERT INTO')

    if description.startswith('bogus'):
        raise RuntimeError('Invalid description!')
    return description


def value_preprocessor(value, **context):
    assert isinstance(context['db'], SQLiteDB)
    assert context['mode'] in ('WHERE', 'UPDATE', 'INSERT INTO')

    return value - 1


def value_postprocessor(value, **context):
    return value + 1


def test_pre_and_post_processors():
    db = SQLiteDB(':memory:', table_mappers, preprocessors={
        'test': {
            'description': description_validator,
            'value': value_preprocessor,
        },
    }, postprocessors={
        'test': {
            'value': value_postprocessor,
        }
    })

    db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, description TEXT, value INTEGER)')

    db.insert_mapped('test', {'description': 'test 1', 'value': 1})

    db.commit()

    with pytest.raises(RuntimeError):
        db.insert_mapped('test', {'description': 'bogus', 'value': 2})

    # Returns as list, as it needs to be mutable for the postprocessors to run
    assert db.select_all('test').where(['id', 'eq', 1]).one() == [1, 'test 1', 1]

    # Bypassing the postprocessors
    assert db.select_all('test').where(['id', 'eq', 1]).result().fetchone() == (1, 'test 1', 0)

    db.insert('test', ('description', 'value')).values([['test 2', 2], ['test 3', -3]], autorun=False).run()

    # Bypassing the postprocessors
    assert db.select_all('test').where(['id', 'eq', 2]).result().fetchall() == [(2, 'test 2', 1)]

    result = db.select_all('test').where(['id', 'eq', 3]).result()
    for r in result:
        assert r == [3, 'test 3', -3]

    db.update_mapped('test', {'value': 2}).where(('id', 'eq', 1)).run()

    assert db.select_all('test').where(['id', 'eq', 1]).one() == [1, 'test 1', 2]

    # Bypassing the postprocessors
    assert db.select_all('test').where(['id', 'eq', 1]).result().fetchmany() == [(1, 'test 1', 1)]
    assert db.select_all('test').where(['id', 'eq', 1]).result().fetchmany(1) == [(1, 'test 1', 1)]

    assert db.select_all('test').where(['value', 'eq', -3]).one() == [3, 'test 3', -3]

    assert db.select_all('test').where(['value', 'in', [1, 2]]).all() == [[1, 'test 1', 2], [2, 'test 2', 2]]


def test_foreign_keys():
    db = SQLiteDB(':memory:', table_mappers, enable_foreign_key_constraints=True)

    # Should be safe to call before any transaction has started
    db.rollback()

    db.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, description TEXT, value INTEGER, '
               'CONSTRAINT fk_self FOREIGN KEY (value) REFERENCES test(id) ON DELETE CASCADE)')

    db.insert_mapped('test', {'description': 'test 1'})

    assert db.select_all('test').where(['id', 'eq', 1]).one() == (1, 'test 1', None)

    with pytest.raises(IntegrityError):
        db.insert_mapped('test', {'description': 'test 2', 'value': 5})

    db.insert_mapped('test', {'description': 'test 2', 'value': 1})
    db.insert_mapped('test', {'description': 'test 3', 'value': None})

    # Test cascade delete
    db.delete('test').where(('id', 'eq', 1)).run()

    assert db.select_all('test').where(['id', 'isnotnull']).one() == (3, 'test 3', None)


def test_bad_input_handling():
    db = SQLiteDB(':memory:', table_mappers)

    with pytest.raises(SQLCompositorBadInput):
        db.select_all('bogus')

    with pytest.raises(SQLCompositorBadInput):
        db.select_all('test').count().count()

    with pytest.raises(SQLCompositorBadInput):
        db.insert_mapped('test', {'bogus': 5})

    with pytest.raises(SQLCompositorBadInput):
        db.select('test', ['bogus'])

    with pytest.raises(SQLCompositorBadInput):
        db.select('test', 'bogus')

    with pytest.raises(SQLCompositorBadInput):
        db.insert('test', ('description', 'value')).values(5)

    with pytest.raises(SQLCompositorBadInput):
        db.insert('test', ('description', 'value')).values_mapped(5)

    with pytest.raises(SQLCompositorBadInput):
        db.insert('test', ('description', 'value')).values([5])

    with pytest.raises(SQLCompositorBadInput):
        db.insert('test', ('description', 'value')).values(([5], ))

    with pytest.raises(SQLCompositorBadInput):
        db.update('test').set_values(5)

    with pytest.raises(SQLCompositorBadInput):
        db.update('test').set_values({'bogus': 5})

    with pytest.raises(SQLCompositorBadInput):
        db.select('test', ['description']).values(5)

    with pytest.raises(SQLCompositorBadInput):
        db.select('test', ['description']).limit(5).limit(6)

    with pytest.raises(SQLCompositorBadInput):
        db.select('test', ['description']).where(['id', 'eq'])

    with pytest.raises(SQLCompositorBadInput):
        db.select('test', ['description']).where(['id', 'is_bogus'])

    with pytest.raises(SQLCompositorBadInput):
        db.select('test', ['description']).where({'and': [['id', 'eq', 1]], 'or': [['id', 'eq', 2]]})

    with pytest.raises(SQLCompositorBadInput):
        db.select_all('test').order_by('not_a_column')

    with pytest.raises(SQLCompositorBadInput):
        db.select_all('test').order_by([])

    with pytest.raises(SQLCompositorBadInput):
        SQLQuery('INSERT INTO', 'test', db).values(5)

    with pytest.raises(SQLCompositorBadInput):
        SQLQuery('INSERT INTO', 'test', db).values_mapped(5)

    with pytest.raises(SQLCompositorBadInput):
        SQLiteDB(':memory:', None)

    with SQLiteDB(':memory:', table_mappers) as db2:
        assert db2.in_transaction() is False


def test_exceptions():
    bad_input = SQLCompositorBadInput('message', 401, {'found exception': 'here'})

    assert bad_input.status_code == 401
    assert bad_input.to_dict() == {'found exception': 'here', 'message': 'message'}

    bad_result = SQLCompositorBadResult('message', 401, {'found exception': 'here'})

    assert bad_result.status_code == 401
    assert bad_result.to_dict() == {'found exception': 'here', 'message': 'message'}
