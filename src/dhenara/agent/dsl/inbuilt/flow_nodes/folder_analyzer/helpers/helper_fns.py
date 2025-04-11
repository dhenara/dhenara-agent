from pathlib import Path


def extract_python_structure(file_path: Path) -> dict:
    """Extract key structural elements from Python files using standard ast module."""

    import ast

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    tree = ast.parse(content)

    imports = []
    classes = []
    functions = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            imports.extend([f"import {name.name}" for name in node.names])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.extend([f"from {module} import {name.name}" for name in node.names])
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    return {
        "docstring": ast.get_docstring(tree),
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


def get_code_structure_pygments(file_path: Path) -> dict:
    """Get basic code structure using Pygments (works for multiple languages)."""

    from pygments.lexers import get_lexer_for_filename
    from pygments.token import Token

    try:
        with open(file_path, encoding="utf-8") as f:
            code = f.read()

        lexer = get_lexer_for_filename(file_path.name)
        tokens = list(lexer.get_tokens(code))

        # Extract classes, functions, etc.
        classes = []
        functions = []
        imports = []

        for i, (token_type, value) in enumerate(tokens):
            # Different languages have different token types
            if token_type in Token.Name.Class:
                classes.append(value)
            elif token_type in Token.Name.Function:
                functions.append(value)
            elif token_type in Token.Keyword and value in ("import", "from", "require", "include"):
                # Collect import statements
                import_stmt = value
                j = i + 1
                while j < len(tokens) and tokens[j][0] not in Token.Text.Whitespace.newline:
                    import_stmt += tokens[j][1]
                    j += 1
                imports.append(import_stmt.strip())

        return {
            "classes": classes,
            "functions": functions,
            "imports": imports,
        }
    except Exception as e:
        return {"error": str(e)}


# TODO_FUTURE: Evalute this
def optimize_for_llm_context(
    path: Path,
    settings,  #: FolderAnalyzerSettings,
) -> str:
    """Optimize code for LLM context using langchain's text splitters."""
    try:
        # This requires: pip install langchain
        from langchain.text_splitter import Language, RecursiveCharacterTextSplitter

        with open(path, encoding="utf-8") as f:
            content = f.read()

        # Map file extension to language for better chunking
        ext = path.suffix.lower()
        language_map = {
            ".py": Language.PYTHON,
            ".js": Language.JS,
            ".ts": Language.TS,
            ".java": Language.JAVA,
            ".go": Language.GO,
            ".rb": Language.RUBY,
            ".rust": Language.RUST,
            ".cpp": Language.CPP,
            ".c": Language.CPP,  # Using C++ for C as well
        }

        language = language_map.get(ext)

        if language:
            # Use language-aware text splitter
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=settings.max_words_per_file * 5 if settings.max_words_per_file else 2000,
                chunk_overlap=50,
            )
        else:
            # Fallback for unknown languages
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.max_words_per_file * 5 if settings.max_words_per_file else 2000, chunk_overlap=50
            )

        # Split content into semantic chunks
        chunks = splitter.split_text(content)

        # If we need to limit total words
        if settings.max_total_words:
            total_chars = 0
            selected_chunks = []
            char_limit = settings.max_total_words * 5  # Approximate chars per word

            for chunk in chunks:
                if total_chars + len(chunk) <= char_limit:
                    selected_chunks.append(chunk)
                    total_chars += len(chunk)
                else:
                    break

            return "\n\n".join(selected_chunks)

        return "\n\n".join(chunks)
    except ImportError:
        # Fallback if langchain is not installed
        with open(path, encoding="utf-8") as f:
            content = f.read()

        if settings.max_words_per_file:
            words = content.split()
            if len(words) > settings.max_words_per_file:
                return " ".join(words[: settings.max_words_per_file]) + "\n... [truncated]"

        return content
