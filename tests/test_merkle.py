import hashlib

from camf import canon


def test_domain_separation_between_leaf_and_raw_hash():
    assert canon.merkle_root([b""]) != hashlib.sha256(b"").digest()


def test_domain_separation_between_leaf_and_node():
    single = canon.merkle_root([b"x"])
    pair = canon.merkle_root([b"x", b"x"])
    assert single != pair


def test_odd_node_is_promoted_not_duplicated():
    # Duplicating the last leaf would make these two leaf sequences collide.
    assert canon.merkle_root([b"a", b"b", b"c"]) != \
        canon.merkle_root([b"a", b"b", b"c", b"c"])


def test_root_is_order_sensitive():
    assert canon.merkle_root([b"a", b"b"]) != canon.merkle_root([b"b", b"a"])


def test_root_is_deterministic():
    chunks = [bytes([i]) * 32 for i in range(37)]
    assert canon.merkle_root(chunks) == canon.merkle_root(list(chunks))


def test_chunk_size_is_part_of_the_specification():
    rows = [canon.encode_row([f"r{i}"], ["str"]) for i in range(10)]
    assert canon.table_root(rows, chunk_rows=2) != canon.table_root(rows, chunk_rows=5)


def test_package_root_binds_object_names():
    a, b = canon.blob_root(b"one"), canon.blob_root(b"two")
    assert canon.package_root({"x": a, "y": b}) != canon.package_root({"x": b, "y": a})


def test_package_root_ignores_dict_insertion_order():
    a, b = canon.blob_root(b"one"), canon.blob_root(b"two")
    assert canon.package_root({"x": a, "y": b}) == canon.package_root({"y": b, "x": a})


def test_package_root_detects_added_object():
    a = canon.blob_root(b"one")
    assert canon.package_root({"x": a}) != canon.package_root({"x": a, "y": a})
