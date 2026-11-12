import math
import re
from difflib import SequenceMatcher
from typing import List, Union


try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except Exception:
    RAPIDFUZZ_AVAILABLE = False


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    return 0.0 if norm1 == 0 or norm2 == 0 else dot / (norm1 * norm2)


def fuzzy_match_keyword(keyword: str, text: str, threshold: float = 65.0,
                        formal: bool = False) -> bool:
    if not keyword or not text:
        return False
    keyword_lower, text_lower = keyword.lower().strip(), text.lower()
    threshold = float(threshold)
    if keyword_lower in text_lower:
        return True
    is_formal = formal and (
        len(keyword_lower) >= 6 or ' ' in keyword_lower or '-' in keyword_lower
    )
    effective = max(threshold, 85.0) if is_formal else threshold
    words = re.findall(r'\b\w+\b', text_lower)
    for word in words:
        if RAPIDFUZZ_AVAILABLE:
            score = fuzz.ratio(keyword_lower, word)
        else:
            score = SequenceMatcher(None, keyword_lower, word).ratio() * 100
        if score >= effective:
            return True
    if is_formal:
        return False
    if RAPIDFUZZ_AVAILABLE:
        score = fuzz.partial_ratio(keyword_lower, text_lower)
    else:
        score = SequenceMatcher(None, keyword_lower, text_lower).ratio() * 100
    return score >= effective


def keyword_match_ratio(student_text: str, reference_text: str,
                        keywords: List[str] = None, threshold: float = 65.0,
                        formal: bool = False) -> float:
    if not reference_text and not keywords:
        return 0.0
    reference_words = set()
    if keywords:
        for k in keywords:
            if k and k.strip():
                reference_words.add(k.strip().lower())
    if reference_text:
        reference_words.update(re.findall(r'\b\w{4,}\b', reference_text.lower()))
    if not reference_words:
        if reference_text:
            reference_words = set(re.findall(r'\b\w+\b', reference_text.lower()))
        if not reference_words:
            return 0.0
    matches = sum(
        1 for ref_word in reference_words
        if fuzzy_match_keyword(ref_word, student_text, threshold=threshold,
                               formal=formal)
    )
    return matches / len(reference_words)


def get_embeddings(texts: Union[str, List[str]], model: str = "nomic-embed-text:latest") -> List[List[float]]:
    try:
        import ollama
        if isinstance(texts, str):
            texts = [texts]
        try:
            response = ollama.embed(model=model, input=texts)
            if hasattr(response, 'embeddings'):
                return response.embeddings
            elif isinstance(response, dict):
                if 'embeddings' in response:
                    return response.embeddings
                elif 'embedding' in response:
                    return [response['embedding']] if len(texts) == 1 else response['embedding']
            if isinstance(response, list):
                return response
        except Exception:
            pass
        try:
            embeddings = []
            for text in texts:
                response = ollama.embeddings(model=model, prompt=text)
                if isinstance(response, dict) and 'embedding' in response:
                    embeddings.append(response['embedding'])
                elif hasattr(response, 'embedding'):
                    embeddings.append(response.embedding)
                else:
                    embeddings.append([])
            return embeddings
        except Exception:
            pass
    except Exception:
        pass
    if isinstance(texts, str):
        texts = [texts]
    return [[] for _ in texts]


def _dedupe_labels(labels: List[str]) -> List[str]:
    result, seen = [], set()
    for label in labels:
        text = str(label or '').strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            result.append(text)
    return result


def _normalize_label_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        labels = []
        for field in ('labels', 'labels_present', 'label', 'text_labels',
                      'annotations', 'detected_labels',
                      'required_diagram_labels'):
            labels.extend(_normalize_label_list(value.get(field)))
        return _dedupe_labels(labels)
    if isinstance(value, (list, tuple, set)):
        labels = []
        for item in value:
            labels.extend(_normalize_label_list(item))
        return _dedupe_labels(labels)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]
    if not isinstance(value, str):
        return []
    raw = value.strip()
    if not raw:
        return []
    if raw.startswith('['):
        try:
            import json
            decoded = json.loads(raw)
            if isinstance(decoded, list):
                return _normalize_label_list(decoded)
        except (TypeError, ValueError):
            pass
    labels = []
    for part in re.split(r'[,;\n|]+', raw):
        label = re.sub(r'^\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s*', '',
                       part).strip()
        if label:
            labels.append(label)
    return _dedupe_labels(labels)


def _diagram_labels_from_payload(diagrams) -> List[str]:
    if diagrams is None:
        return []
    if isinstance(diagrams, dict):
        for field in ('diagrams', 'figures', 'visuals', 'detected_diagrams'):
            if field in diagrams:
                return _diagram_labels_from_payload(diagrams[field])
        for field in ('labels', 'labels_present', 'label', 'text_labels',
                      'annotations'):
            if field in diagrams:
                return _normalize_label_list(diagrams.get(field))
        diagrams = [diagrams]
    if isinstance(diagrams, str):
        raw = diagrams.strip()
        if not raw:
            return []
        try:
            import json
            return _diagram_labels_from_payload(json.loads(raw))
        except (TypeError, ValueError):
            return []
    if not isinstance(diagrams, (list, tuple, set)):
        return []
    labels = []
    for item in diagrams:
        if isinstance(item, str):
            labels.extend(_normalize_label_list(item))
        elif isinstance(item, dict):
            labels.extend(_normalize_label_list(
                item.get('labels') or item.get('labels_present')
                or item.get('label') or item.get('text_labels')
                or item.get('annotations') or item.get('detected_labels')
            ))
    return _dedupe_labels(labels)


def _strip_math_delimiters(expression: str) -> str:
    text = str(expression or '').strip()
    text = re.sub(r'^\s*\$\$?|\$\$?\s*$', '', text)
    text = re.sub(r'^\s*\\\[|\\\]\s*$', '', text)
    text = re.sub(r'^\s*\\\(|\\\)\s*$', '', text)
    return text.strip()


def _normalize_equation(expression: str) -> str:
    text = _strip_math_delimiters(expression)
    text = text.replace('−', '-').replace('×', '*').replace('÷', '/')
    text = text.replace('·', '*').replace('⋅', '*')
    text = text.replace('→', '->').replace('⇒', '->')
    text = re.sub(r'\\(left|right|displaystyle|limits|,|;|!)', '', text)
    text = re.sub(r'\\(?:mathrm|mathbf|mathit|mathsf|text|operatorname)\{([^{}]*)\}', r'\1', text)
    text = re.sub(r'\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\sqrt\s*\{([^{}]*)\}', r'sqrt(\1)', text)
    replacements = {
        r'\times': '*', r'\cdot': '*', r'\div': '/', r'\pm': '+-',
        r'\leq': '<=', r'\geq': '>=', r'\neq': '!=', r'\rightarrow': '->',
        r'\to': '->', r'\pi': 'pi', r'\theta': 'theta', r'\alpha': 'alpha',
        r'\beta': 'beta', r'\gamma': 'gamma', r'\Delta': 'delta',
        r'\delta': 'delta', r'\infty': 'inf',
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r'\\[a-zA-Z]+', '', text).replace('{', '').replace('}', '')
    text = text.replace('**', '^')
    return re.sub(r'\s+', '', text).lower().strip('.,;:')


def extract_equations(text: str) -> List[str]:
    """Extract LaTeX or plain-text equations from a transcription."""
    if not text or not isinstance(text, str):
        return []
    candidates = []
    math_pattern = re.compile(
        r'\$\$(.+?)\$\$|\\\[(.+?)\\\]|\\\((.+?)\\\)'
        r'|(?<!\\)\$(?!\$)(.+?)(?<!\\\$)\$'
        r'|\\begin\{(?:equation|align|gather|eqnarray)\*?\}(.+?)'
        r'\\end\{(?:equation|align|gather|eqnarray)\*?\}',
        re.DOTALL | re.IGNORECASE,
    )
    for match in math_pattern.finditer(text):
        candidates.append(next(g for g in match.groups() if g is not None))
    for line in text.splitlines():
        cleaned = re.sub(r'^\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s*', '', line).strip()
        if not cleaned or len(cleaned) > 300 or re.search(r'\$|\\\(|\\\[', cleaned):
            continue
        if '=' in cleaned or re.search(r'\\[a-zA-Z]+|[\^_]', cleaned):
            candidates.append(cleaned)
    equations, seen = [], set()
    for candidate in candidates:
        equation = _strip_math_delimiters(candidate).strip(' .,;:')
        if not equation or equation in ('.', '-', '—'):
            continue
        if '=' not in equation and not re.search(r'[\\^_]|[\d)]', equation):
            continue
        key = _normalize_equation(equation)
        if key and key not in seen:
            seen.add(key)
            equations.append(equation)
    return equations
