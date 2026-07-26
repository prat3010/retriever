"""Tests for OCR fallback and vision extraction in worker tasks."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# ── _ocr_with_tesseract ────────────────────────────────────────────────────
# ponytail: pytesseract and PIL may not be installed in API venv — mock via sys.modules


@pytest.fixture
def mock_ocr_modules():
    pytesseract = MagicMock()
    pil = MagicMock()
    pil.Image = MagicMock()
    sys.modules["pytesseract"] = pytesseract
    sys.modules["PIL"] = pil
    sys.modules["PIL.Image"] = pil.Image
    yield pytesseract
    for k in ["pytesseract", "PIL", "PIL.Image"]:
        sys.modules.pop(k, None)


def test_ocr_with_tesseract_image(mock_ocr_modules) -> None:
    from workers.src.tasks import _ocr_with_tesseract

    mock_ocr_modules.image_to_string.return_value = "extracted text"

    result = _ocr_with_tesseract("/path/img.png", "image/png")

    assert result == "extracted text"
    mock_ocr_modules.image_to_string.assert_called_once()


def test_ocr_with_tesseract_pdf_pages(mock_ocr_modules) -> None:
    from workers.src.tasks import _ocr_with_tesseract

    mock_ocr_modules.image_to_string.return_value = "page text"

    with patch("pdfplumber.open") as mock_pdfplumber:
        mock_page = MagicMock()
        mock_page.to_image.return_value = MagicMock()
        mock_pdfplumber.return_value.__enter__.return_value.pages = [mock_page]

        result = _ocr_with_tesseract("/path/doc.pdf", "application/pdf")

    assert "page text" in result
    assert mock_ocr_modules.image_to_string.call_count == 1


def test_ocr_with_tesseract_pdf_multi_page(mock_ocr_modules) -> None:
    from workers.src.tasks import _ocr_with_tesseract

    mock_ocr_modules.image_to_string.side_effect = ["page 1 text", "page 2 text"]

    with patch("pdfplumber.open") as mock_pdfplumber:
        mock_page_1 = MagicMock()
        mock_page_2 = MagicMock()
        mock_pdfplumber.return_value.__enter__.return_value.pages = [mock_page_1, mock_page_2]

        result = _ocr_with_tesseract("/path/doc.pdf", "application/pdf")

    assert "page 1 text" in result
    assert "page 2 text" in result
    assert mock_ocr_modules.image_to_string.call_count == 2


def test_ocr_with_tesseract_no_import() -> None:
    from workers.src.tasks import _ocr_with_tesseract

    with patch.dict("sys.modules", {"pytesseract": None, "PIL": None}):
        result = _ocr_with_tesseract("/path/img.png", "image/png")

    assert result == ""


def test_ocr_with_tesseract_exception_returns_empty(mock_ocr_modules) -> None:
    from workers.src.tasks import _ocr_with_tesseract

    mock_ocr_modules.image_to_string.side_effect = RuntimeError("OCR failed")

    result = _ocr_with_tesseract("/path/img.png", "image/png")

    assert result == ""


# ── _describe_with_vision ──────────────────────────────────────────────────


def test_describe_with_vision_empty_api_key() -> None:
    from workers.src.tasks import _describe_with_vision

    with patch.dict("os.environ", {}, clear=True):
        result = _describe_with_vision("/path/img.png", "image/png", {}, tenant_id="11111111-1111-1111-1111-111111111111")

    assert result == ""


@patch("openai.OpenAI")
def test_describe_with_vision_image(mock_openai_cls) -> None:
    from workers.src.tasks import _describe_with_vision

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = "a cat"

    config = {"ai_provider": {"api_key": "sk-test", "vision_model": "gpt-4o"}}

    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = b"fake_image_bytes"
        result = _describe_with_vision("/path/cat.png", "image/png", config)

    assert result == "a cat"


@patch("openai.OpenAI")
@patch("pdfplumber.open")
def test_describe_with_vision_pdf_multi_page(mock_pdfplumber, mock_openai_cls) -> None:
    from workers.src.tasks import _describe_with_vision

    mock_page_1 = MagicMock()
    mock_page_2 = MagicMock()
    mock_pdfplumber.return_value.__enter__.return_value.pages = [mock_page_1, mock_page_2]

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = "page content"

    config = {"ai_provider": {"api_key": "sk-test", "vision_model": "gpt-4o"}}

    result = _describe_with_vision("/path/doc.pdf", "application/pdf", config)

    assert "Page 1" in result
    assert "Page 2" in result
    assert mock_client.chat.completions.create.call_count == 2


@patch("openai.OpenAI")
def test_describe_with_vision_api_failure(mock_openai_cls) -> None:
    from workers.src.tasks import _describe_with_vision

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.side_effect = RuntimeError("API error")

    config = {"ai_provider": {"api_key": "sk-test"}}

    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = b"fake_bytes"

        with pytest.raises(RuntimeError):
            _describe_with_vision("/path/img.png", "image/png", config)


@patch("openai.OpenAI")
def test_describe_with_vision_env_api_key_fallback(mock_openai_cls) -> None:
    from workers.src.tasks import _describe_with_vision

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = "vision result"

    with patch.dict("os.environ", {"OPENAI_API_KEY": "env-key"}):
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b"bytes"
            result = _describe_with_vision("/path/img.png", "image/png", {})

    assert result == "vision result"


# ── _ocr_with_rapidocr ─────────────────────────────────────────────────────


@pytest.fixture
def mock_rapidocr_module():
    rapidocr_mod = MagicMock()
    rapid_cls = MagicMock()
    rapidocr_mod.RapidOCR = rapid_cls
    sys.modules["rapidocr_onnxruntime"] = rapidocr_mod
    yield rapid_cls
    sys.modules.pop("rapidocr_onnxruntime", None)


def test_ocr_with_rapidocr_image(mock_rapidocr_module) -> None:
    from workers.src.tasks import _ocr_with_rapidocr

    engine_instance = MagicMock()
    mock_rapidocr_module.return_value = engine_instance
    engine_instance.return_value = ([
        [None, "RapidOCR extracted line 1", 0.99],
        [None, "RapidOCR extracted line 2", 0.98],
    ], None)

    result = _ocr_with_rapidocr("/path/sample.png", "image/png")

    assert "RapidOCR extracted line 1" in result
    assert "RapidOCR extracted line 2" in result


def test_ocr_with_rapidocr_pdf_multi_page(mock_rapidocr_module) -> None:
    from workers.src.tasks import _ocr_with_rapidocr

    engine_instance = MagicMock()
    mock_rapidocr_module.return_value = engine_instance
    engine_instance.return_value = ([
        [None, "Page content line", 0.99]
    ], None)

    with patch("pdfplumber.open") as mock_pdfplumber:
        mock_page = MagicMock()
        mock_page.to_image.side_effect = Exception("no image render in mock")
        mock_pdfplumber.return_value.__enter__.return_value.pages = [mock_page]

        result = _ocr_with_rapidocr("/path/sample.pdf", "application/pdf")

    assert "Page content line" in result


def test_ocr_with_rapidocr_no_import() -> None:
    from workers.src.tasks import _ocr_with_rapidocr

    with patch.dict("sys.modules", {"rapidocr_onnxruntime": None}):
        result = _ocr_with_rapidocr("/path/sample.png", "image/png")

    assert result == ""


def test_ocr_with_rapidocr_exception_returns_empty(mock_rapidocr_module) -> None:
    from workers.src.tasks import _ocr_with_rapidocr

    engine_instance = MagicMock()
    mock_rapidocr_module.return_value = engine_instance
    engine_instance.side_effect = RuntimeError("RapidOCR internal failure")

    result = _ocr_with_rapidocr("/path/sample.png", "image/png")

    assert result == ""

