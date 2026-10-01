from scripts.validate_portfolio import validate_portfolio

def test_portfolio_registry_is_fail_closed():
    assert validate_portfolio() == []
