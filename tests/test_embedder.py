"""Tests for the embedding module (mocked OpenAI API calls)."""

from unittest.mock import MagicMock

from src.config import settings
from src.ingest.chunker import Chunk
from src.ingest.embedder import embed_chunks, embed_texts


def _make_mock_embedding(dim: int = 1536) -> list[float]:
    """Create a fake embedding vector of the specified dimension."""
    return [0.01 * i for i in range(dim)]


def _make_mock_response(texts: list[str], dim: int = 1536) -> MagicMock:
    """Create a mock OpenAI embeddings response."""
    mock_response = MagicMock()
    mock_items = []
    for i, _ in enumerate(texts):
        item = MagicMock()
        item.embedding = _make_mock_embedding(dim)
        mock_items.append(item)
    mock_response.data = mock_items
    return mock_response


class TestEmbedTexts:
    """Tests for the embed_texts function."""

    def test_returns_correct_number_of_embeddings(self) -> None:
        mock_client = MagicMock()
        texts = ["hello", "world", "test"]
        mock_client.embeddings.create.return_value = _make_mock_response(texts)

        result = embed_texts(texts, client=mock_client)

        assert len(result) == 3
        mock_client.embeddings.create.assert_called_once()

    def test_returns_correct_dimension(self) -> None:
        mock_client = MagicMock()
        texts = ["hello"]
        mock_client.embeddings.create.return_value = _make_mock_response(texts)

        result = embed_texts(texts, client=mock_client)

        assert len(result[0]) == settings.embedding_dimension

    def test_empty_input_returns_empty(self) -> None:
        result = embed_texts([])
        assert result == []

    def test_batching_for_large_input(self) -> None:
        mock_client = MagicMock()
        texts = [f"text {i}" for i in range(150)]

        # First batch: 100 items, second batch: 50 items
        mock_client.embeddings.create.side_effect = [
            _make_mock_response(texts[:100]),
            _make_mock_response(texts[100:]),
        ]

        result = embed_texts(texts, client=mock_client)

        assert len(result) == 150
        assert mock_client.embeddings.create.call_count == 2

    def test_calls_correct_model(self) -> None:
        mock_client = MagicMock()
        texts = ["test"]
        mock_client.embeddings.create.return_value = _make_mock_response(texts)

        embed_texts(texts, client=mock_client)

        call_kwargs = mock_client.embeddings.create.call_args
        assert call_kwargs.kwargs["model"] == settings.embedding_model


class TestEmbedChunks:
    """Tests for the embed_chunks function."""

    def test_attaches_embeddings_to_chunks(self) -> None:
        mock_client = MagicMock()
        chunks = [
            Chunk(text="chunk one", source_name="test.pdf"),
            Chunk(text="chunk two", source_name="test.pdf"),
        ]
        mock_client.embeddings.create.return_value = _make_mock_response(
            [c.text for c in chunks]
        )

        result = embed_chunks(chunks, client=mock_client)

        assert len(result) == 2
        for chunk in result:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == settings.embedding_dimension

    def test_empty_chunks_returns_empty(self) -> None:
        result = embed_chunks([])
        assert result == []

    def test_preserves_chunk_metadata(self) -> None:
        mock_client = MagicMock()
        chunks = [
            Chunk(
                text="test text",
                source_name="report.pdf",
                document_type="gao_report",
                materials=["tungsten"],
                section_title="Overview",
                chunk_index=0,
                page_numbers=[1, 2],
            ),
        ]
        mock_client.embeddings.create.return_value = _make_mock_response([chunks[0].text])

        result = embed_chunks(chunks, client=mock_client)

        assert result[0].source_name == "report.pdf"
        assert result[0].document_type == "gao_report"
        assert result[0].materials == ["tungsten"]
        assert result[0].section_title == "Overview"
        assert result[0].page_numbers == [1, 2]
