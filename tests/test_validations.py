import pytest

from restomatic.validations import (type_pos_int, type_non_neg_int, expect_type, expect_in, expect_len,
                                    expect_len_range, expect_only_one_of, cast_expect_type, set_dict_data_only_once)


def test_types():
    assert type_pos_int('5') == 5
    assert type_non_neg_int('5') == 5

    assert type_pos_int(7) == 7
    assert type_non_neg_int(7) == 7

    with pytest.raises(ValueError):
        type_pos_int('0')

    assert type_non_neg_int('0') == 0

    with pytest.raises(ValueError):
        type_pos_int('-3')

    with pytest.raises(ValueError):
        type_pos_int('not_an_int')

    with pytest.raises(ValueError):
        type_non_neg_int('-3')

    with pytest.raises(ValueError):
        type_non_neg_int('not_an_int')

    assert cast_expect_type('5', int, 'test') == 5
    assert cast_expect_type(7, int, 'test') == 7

    with pytest.raises(TypeError):
        cast_expect_type('foo', int, 'test')


def test_expects():
    assert expect_type(5, int, 'test') is None
    assert expect_type(5, (int, float), 'test') is None

    with pytest.raises(TypeError):
        expect_type('foo', int, 'test')

    assert expect_in(7, [6, 7], 'test') is None

    with pytest.raises(ValueError):
        expect_in(4, [6, 7], 'test')

    assert expect_len([6, 7], 2, 'test') is None

    with pytest.raises(ValueError):
        expect_len([6, 7, 8], 2, 'test')

    assert expect_len_range([6, 7], 2, 3, 'test') is None
    assert expect_len_range([6, 7, 8], 2, 3, 'test') is None

    with pytest.raises(ValueError):
        expect_len_range([6, 7, 8], 1, 2, 'test')

    assert expect_only_one_of(['A', None, None], 'test') is None

    with pytest.raises(ValueError):
        expect_only_one_of(['A', None, 'B'], 'test')

    with pytest.raises(ValueError):
        expect_only_one_of([None, None, None], 'test')


def test_dict_set():
    data = {}

    set_dict_data_only_once(data, ['A', 'B'], 5, 'test')

    assert data == {'A': {'B': 5}}

    with pytest.raises(ValueError):
        set_dict_data_only_once(data, ['A', 'B'], 6, 'test')

    set_dict_data_only_once(data, ['A', 'C'], 7, 'test')

    assert data == {'A': {'B': 5, 'C': 7}}
