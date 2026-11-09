from tests.helper.idn_labels import a_label, replace_idn_placeholders, u_label


def test_a_label_has_the_ace_prefix_and_is_ascii():
    label = a_label("bücher-t1", "1a2b")

    assert label.startswith("xn--")
    assert label.isascii()


def test_placeholders_name_the_same_label_in_both_forms():
    value = replace_idn_placeholders("{alabel:bücher-t1}.example and {ulabel:bücher-t1}.example", "1a2b")

    assert value == f"{a_label('bücher-t1', '1a2b')}.example and bücher-t1-1a2b.example"
    assert u_label("bücher-t1", "1a2b") == "bücher-t1-1a2b"


def test_the_a_label_decodes_to_the_u_label():
    label = a_label("Bücher-t1", "1a2b")

    assert label[4:].encode("ascii").decode("punycode") == "bücher-t1-1a2b"
