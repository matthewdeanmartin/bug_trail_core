from bug_trail_core.exceptions import get_exception_hierarchy


def test_get_exception_hierarchy():
    # ZeroDivisionError has an interesting hierarchy
    result = get_exception_hierarchy(ZeroDivisionError())
    assert len(result) == 5
