from analyse_conf.data import Name


def test_is_initialed() -> None:
    assert Name("L. watts").is_initialed
    assert not Name("Liam Watts").is_initialed
    assert Name("Terence C. S. Tao").is_initialed  # test initialed middle names are also recognized
    assert not Name("Terence Chi-Shen Tao").is_initialed
    assert Name("Liam W.").is_initialed  # even last names can be initialed
    assert Name("Liam W").is_initialed
    assert not Name(" Liam ").is_initialed  # sanity check


def test_initialise_name() -> None:
    assert Name("liam watts").initialised() == ("l. watts", ["l."])
    assert Name("francis william watts").initialised() == ("f. w. watts", ["f.", "w."])
    assert Name("saul").initialised() == ("saul", [])
    assert Name("l. watts").initialised() == ("l. watts", ["l."])


def test_name_distance() -> None:
    assert Name("liam watts").distance(Name("liam watts")) == 0
    assert Name("liam watts").distance(Name("liAm WATts")) == 0, "name distance should not be case sensitive"
    assert Name("liam watts").distance(Name("lifm wftts")) == 2
    assert Name("liam watts").distance(Name("l. watts")) == 0
    assert Name("liam watts").distance(Name("L. watts")) == 0
    assert Name("Liam watts").distance(Name("l. watts")) == 0
    assert Name("liam watts").distance(Name("l watts")) == 0
    assert Name("liam watts").distance(Name("d. watts")) == 4, "incorrect initialisms don't have a high distance"
