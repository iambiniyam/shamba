from pathlib import Path

import pytest
from PIL import Image

from shamba.model import ModelNotReady, PlantDiseaseModel, preprocess

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def model():
    try:
        return PlantDiseaseModel()
    except ModelNotReady as exc:
        pytest.skip(str(exc))


def test_preprocess_shape():
    image = Image.new("RGB", (640, 480), "green")
    batch = preprocess(image)
    assert batch.shape == (1, 3, 224, 224)
    assert batch.dtype.name == "float32"


def test_maize_rust(model):
    predictions = model.predict(Image.open(FIXTURES / "maize_rust.jpg"))
    assert predictions[0].info.crop == "Maize"
    assert "rust" in predictions[0].info.disease.lower()


def test_tomato_late_blight(model):
    predictions = model.predict(Image.open(FIXTURES / "tomato_late_blight.jpg"))
    assert predictions[0].info.crop == "Tomato"
    assert "late blight" in predictions[0].info.disease.lower()
