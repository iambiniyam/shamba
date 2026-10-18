from shamba.labels import RAW_LABELS, parse_label


def test_label_count():
    assert len(RAW_LABELS) == 38


def test_every_label_parses():
    for raw in RAW_LABELS:
        info = parse_label(raw)
        assert info.crop
        assert info.disease
        assert info.key


def test_maize_rust():
    info = parse_label("Corn (Maize) with Common Rust")
    assert info.crop == "Maize"
    assert info.disease == "Common Rust"
    assert info.key == "maize_common_rust"
    assert not info.healthy


def test_healthy_apple():
    info = parse_label("Healthy Apple")
    assert info.crop == "Apple"
    assert info.healthy
    assert info.key == "apple_healthy"


def test_bell_pepper_alias():
    info = parse_label("Bell Pepper with Bacterial Spot")
    assert info.crop == "Pepper"
    assert info.key == "pepper_bacterial_spot"
