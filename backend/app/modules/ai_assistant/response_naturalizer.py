"""
ResponseNaturalizer — post-procesador de respuestas del agente para WhatsApp.

Problemas que resuelve (issue #16):
  1. Tool calls crudas (<function=...>{...}) que el LLM mete en el texto
  2. Markdown excesivo (**bold**, listas numeradas largas) inadecuado para WhatsApp

Mejoras adicionales (issue #20):
  3. Frases enlatadas de apertura ("Claro, ...", "Por supuesto, ...")
  4. Cierres sycophantic ("Espero haberte ayudado", "No dudes en contactarme")
  5. Exceso de emojis (más de 2 por defecto)
  6. Lenguaje formal/corporativo ("Procederé a", "Me permito informarle que")
"""

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patrones de tool calls que el LLM puede filtrar en texto
# ---------------------------------------------------------------------------
_TOOL_CALL_PATTERNS = [
    # <function=name>{"key": "val"}</function>
    re.compile(r"<function=[^>]+>\{[^}]*\}</function>", re.DOTALL),
    # <function=name>{"key": "val"}  (sin cierre)
    re.compile(r"<function=[^>]+>\{.*?\}", re.DOTALL),
    # [function_name({"key": "val"})]
    re.compile(r"\[[\w_]+\(\{[^}]*\}\)\]", re.DOTALL),
    # ```tool_call ... ``` bloques
    re.compile(r"```tool_call.*?```", re.DOTALL | re.IGNORECASE),
    # {"name": "tool", "parameters": {...}} standalone
    re.compile(r'\{"name":\s*"[\w_]+",\s*"parameters":\s*\{[^}]*\}\}', re.DOTALL),
]

# ---------------------------------------------------------------------------
# Markdown que no se ve bien en WhatsApp
# ---------------------------------------------------------------------------
_HEAVY_MARKDOWN_SUBS = [
    # **texto** → texto (negritas de listas)
    (re.compile(r"\*\*([^*]+)\*\*:"), r"\1:"),
    # Listas numeradas con bold header "1. **Título**: descripción" → "• Título: descripción"
    (re.compile(r"^\d+\.\s+\*\*([^*]+)\*\*", re.MULTILINE), r"• \1"),
    # Múltiples líneas en blanco → máximo una
    (re.compile(r"\n{3,}"), "\n\n"),
]

# ---------------------------------------------------------------------------
# Frases enlatadas de apertura (issue #20)
# ---------------------------------------------------------------------------
# Cada entrada es un patrón que coincide SOLO al inicio del mensaje.
# Se incluye la coma/punto/espacio/signo de exclamación que pueda seguir al opener.
_CANNED_OPENER_RE = re.compile(
    r"""^(?:
        ¡\s*claro\s*!               # ¡Claro!
        | claro(?=\s*[,!]\s)        # Claro,  /  Claro!  — pero NO "Claro que sí"
        | por\s+supuesto             # Por supuesto
        | ¡\s*excelente\s+pregunta\s*!  # ¡Excelente pregunta!
        | excelente\s+pregunta       # Excelente pregunta
        | entendido                  # Entendido
        | con\s+gusto                # Con gusto
        | perfecto                   # Perfecto
        | desde\s+luego              # Desde luego
        | absolutamente              # Absolutamente
        | sin\s+duda                 # Sin duda
        | c[oó]mo\s+no               # Cómo no / Como no
        | of\s+course                # Of course
        | sure                       # Sure
        | great\s+question           # Great question
        | understood                 # Understood
        | my\s+pleasure              # My pleasure
        | ¡\s*hola\s*!               # ¡Hola!  (opener vacío)
        | buenas(?=\s*,)             # Buenas,  (solo seguido de coma)
    )
    # Consumir separadores que queden (¡!, coma, punto, espacios)
    [!¡,.\s]*
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Frases sycophantic de cierre (issue #20)
# ---------------------------------------------------------------------------
_SYCOPHANTIC_CLOSER_FRAGMENTS = [
    "espero haberte ayudado",
    "espero haber sido de ayuda",
    "no dudes en contactarme",
    "no dudes en escribirme",
    "quedo a tu disposición",
    "quedo a su disposición",
    "¿hay algo más en que pueda ayudarte",
    "¿tienes alguna otra pregunta",
    "estoy aquí para ayudarte",
    "estoy aquí para lo que necesites",
]

# ---------------------------------------------------------------------------
# Lenguaje formal/corporativo (issue #20)
# ---------------------------------------------------------------------------
_FORMAL_LANGUAGE_SUBS = [
    (re.compile(r"proceder[eé]\s+a\b", re.IGNORECASE), "Voy a"),
    (re.compile(r"con\s+respecto\s+a\s+su\s+consulta[,.]?\s*", re.IGNORECASE), ""),
    (re.compile(r"me\s+permito\s+informarle\s+que\s*", re.IGNORECASE), ""),
    (re.compile(r"a\s+continuaci[oó]n\s+le\s+presento\b", re.IGNORECASE), "Acá te va"),
    (re.compile(r"a\s+continuaci[oó]n\s+te\s+presento\b", re.IGNORECASE), "Acá te va"),
    (re.compile(r"le\s+informo\s+que\s*", re.IGNORECASE), ""),
    (re.compile(r"te\s+informo\s+que\s*", re.IGNORECASE), ""),
    (re.compile(r"estimado\s+usuario[,]?\s*", re.IGNORECASE), ""),
    (re.compile(r"con\s+mucho\s+gusto\s+le\b", re.IGNORECASE), "Te"),
    (re.compile(r"con\s+mucho\s+gusto\s+te\b", re.IGNORECASE), "Te"),
]


# ===========================================================================
# Funciones públicas
# ===========================================================================

def clean_raw_tool_calls(text: str) -> str:
    """
    Elimina fragmentos de tool calls crudas que el LLM a veces inyecta en el texto.

    El modelo llama la herramienta correctamente vía tool_calls, pero TAMBIÉN
    incluye el fragmento textual en el contenido de la respuesta. Este paso
    lo limpia antes de enviar al usuario de WhatsApp.
    """
    original = text
    for pattern in _TOOL_CALL_PATTERNS:
        text = pattern.sub("", text)

    # Limpiar espacios sobrantes al final de líneas y espacios dobles
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"  +", " ", text)
    text = text.strip()

    if text != original:
        logger.info("🧹 ResponseNaturalizer: removed raw tool call fragments from response")

    return text


def strip_heavy_markdown(text: str) -> str:
    """
    Suaviza markdown excesivo inadecuado para conversaciones de WhatsApp.

    WhatsApp renderiza *cursiva* y _cursiva_ pero no markdown de listas complejas
    ni cabeceras. Respuestas con muchos **bold** y listas numeradas largas
    suenan robóticas.
    """
    for pattern, replacement in _HEAVY_MARKDOWN_SUBS:
        text = pattern.sub(replacement, text)
    return text.strip()


def strip_canned_openers(text: str) -> str:
    """
    Elimina frases enlatadas de apertura SOLO cuando aparecen al inicio del mensaje.

    Ejemplos:
        '¡Claro! Aquí tienes...'        → 'Aquí tienes...'
        'Por supuesto, puedo ayudarte.' → 'Puedo ayudarte.'
        'Claro que sí, es importante'   → sin cambio  (no es solo la palabra)
        'Hola, ¿cómo estás?'            → sin cambio  (no es opener vacío)
    """
    match = _CANNED_OPENER_RE.match(text)
    if not match:
        return text

    remainder = text[match.end():]
    if not remainder:
        # El texto era SÓLO el opener — no lo borramos para no dejar vacío
        return text

    # Capitalizar la primera letra del resto si quedó en minúscula
    remainder = remainder[0].upper() + remainder[1:]
    logger.debug("✂️  ResponseNaturalizer: stripped canned opener %r", match.group())
    return remainder


def strip_sycophantic_closers(text: str) -> str:
    """
    Elimina la última oración del mensaje si es sycophantic (servilista).

    Solo afecta a la última oración; si la frase aparece en medio del texto,
    no se toca.

    Ejemplos:
        'Tu pedido llegará mañana. Espero haberte ayudado.'
            → 'Tu pedido llegará mañana.'
        'No dudes en contactarme si tienes alguna duda.'
            → ''  (era la única oración)
    """
    # Dividir en oraciones usando '.', '!' o '?' como delimitadores
    # Conservamos los delimitadores para poder reconstruir el texto
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    # Filtrar oraciones vacías manteniendo el índice de la última no-vacía
    last_idx = None
    for i in range(len(sentences) - 1, -1, -1):
        if sentences[i].strip():
            last_idx = i
            break

    if last_idx is None:
        return text

    last_sentence = sentences[last_idx].strip().lower()

    # Normalizar signos de apertura para la comparación
    last_sentence_normalized = last_sentence.lstrip("¿¡").strip()

    for fragment in _SYCOPHANTIC_CLOSER_FRAGMENTS:
        fragment_normalized = fragment.lstrip("¿¡").strip()
        if fragment_normalized in last_sentence_normalized:
            # Remover la última oración
            remaining = sentences[:last_idx]
            result = " ".join(s for s in remaining if s.strip()).strip()
            logger.debug(
                "✂️  ResponseNaturalizer: stripped sycophantic closer %r",
                sentences[last_idx],
            )
            return result

    return text


def limit_emojis(text: str, max_emojis: int = 2) -> str:
    """
    Limita la cantidad de emojis en el texto a max_emojis.

    Si hay más emojis que el límite, los que superen el máximo se eliminan
    del texto preservando el contenido circundante.

    El rango de detección cubre los bloques Unicode principales de emojis:
        U+1F000–U+1FFFF  (Emoticons, símbolos, etc.)
        U+2600–U+27BF    (Miscelánea de símbolos, Dingbats, etc.)
    """
    emoji_pattern = re.compile(
        r"[\U0001F000-\U0001FFFF"
        r"\u2600-\u27BF]",
        re.UNICODE,
    )

    found = emoji_pattern.findall(text)
    if len(found) <= max_emojis:
        return text

    # Conservar solo los primeros max_emojis, eliminar el resto
    count = 0

    def _replacer(match: re.Match) -> str:
        nonlocal count
        count += 1
        if count <= max_emojis:
            return match.group()
        return ""

    result = emoji_pattern.sub(_replacer, text)
    # Limpiar posibles dobles espacios que queden tras eliminar emojis
    result = re.sub(r"  +", " ", result).strip()
    logger.debug(
        "✂️  ResponseNaturalizer: limited emojis from %d to %d",
        len(found),
        max_emojis,
    )
    return result


def strip_formal_language(text: str) -> str:
    """
    Reemplaza lenguaje formal/corporativo por un tono más conversacional.

    Ejemplos:
        'Procederé a verificar tu pedido.'  → 'Voy a verificar tu pedido.'
        'Me permito informarle que ...'     → '...'
        'A continuación le presento ...'    → 'Acá te va ...'
    """
    for pattern, replacement in _FORMAL_LANGUAGE_SUBS:
        text = pattern.sub(replacement, text)

    # Limpiar doble espacio y oraciones que hayan quedado con minúscula inicial
    # después de una sustitución que eliminó el comienzo
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"(?<=[.!?]\s)([a-záéíóúüñ])", lambda m: m.group(1).upper(), text)
    text = text.strip()
    # Si el texto empieza con minúscula por una sustitución al inicio, capitalizar
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def naturalize(
    text: str,
    strip_markdown: bool = True,
    strip_canned: bool = True,
    max_emojis: int = 2,
) -> str:
    """
    Pipeline completo de naturalización.

    Args:
        text:           Respuesta cruda del agente.
        strip_markdown: Si True, suaviza markdown pesado además de limpiar tool calls.
        strip_canned:   Si True, elimina openers enlatados, cierres sycophantic
                        y lenguaje formal/corporativo.
        max_emojis:     Número máximo de emojis permitidos (0 = eliminar todos).

    Returns:
        Texto limpio listo para enviar por WhatsApp.
    """
    if not text:
        return text

    text = clean_raw_tool_calls(text)

    if strip_markdown:
        text = strip_heavy_markdown(text)

    if strip_canned:
        text = strip_canned_openers(text)
        text = strip_sycophantic_closers(text)
        text = strip_formal_language(text)

    text = limit_emojis(text, max_emojis)

    return text
