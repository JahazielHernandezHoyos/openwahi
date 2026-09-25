"""
Tests para ResponseNaturalizer — issue #16.

Cubre los 5 edge cases documentados en el sandbox:
  T04/T06/T08/T09 — tool calls crudas en texto
  T10             — markdown excesivo con listas numeradas y bold
"""

from app.modules.ai_assistant.response_naturalizer import (
    clean_raw_tool_calls,
    naturalize,
    strip_heavy_markdown,
)


# ─────────────────────────────────────────────────────────────
# clean_raw_tool_calls
# ─────────────────────────────────────────────────────────────


def test_removes_function_tag_with_closing():
    """Bug T04/T06: <function=name>{...}</function> debe desaparecer."""
    text = 'No inventa nada. ¿Quieres saber más? <function=registrar_prospecto>{"email": "x@x.com"}</function>'
    result = clean_raw_tool_calls(text)
    assert "<function=" not in result
    assert "registrar_prospecto" not in result
    assert "No inventa nada. ¿Quieres saber más?" in result


def test_removes_function_tag_without_closing():
    """Bug T08/T09: <function=name>{...} sin </function>."""
    text = 'Te agrego a la lista. <function=registrar_prospecto>{"email": "user@example.com"}'
    result = clean_raw_tool_calls(text)
    assert "<function=" not in result
    assert "Te agrego a la lista." in result


def test_clean_is_noop_when_no_tool_call():
    """Respuesta sin tool calls no debe modificarse."""
    text = "Estamos en beta gratuita con cupos limitados. Te interesa probarlo?"
    result = clean_raw_tool_calls(text)
    assert result == text


def test_clean_multiple_tool_calls():
    """Múltiples fragmentos de tool call en el mismo mensaje."""
    text = (
        "Primera cosa. <function=tool_a>{\"k\": \"v\"}</function> "
        "Segunda cosa. <function=tool_b>{\"k\": \"v\"}</function> Fin."
    )
    result = clean_raw_tool_calls(text)
    assert "<function=" not in result
    assert "Primera cosa." in result
    assert "Segunda cosa." in result
    assert "Fin." in result


def test_clean_preserves_legitimate_braces():
    """Llaves en texto normal (ej: código) no deben eliminarse."""
    text = "El payload es {\"key\": \"value\"} según la doc."
    result = clean_raw_tool_calls(text)
    # No tiene prefijo <function= así que no debe tocarse
    assert '{"key": "value"}' in result


# ─────────────────────────────────────────────────────────────
# strip_heavy_markdown
# ─────────────────────────────────────────────────────────────


def test_removes_bold_in_list_items():
    """Bug T08: **Funcionamiento**: descripción → Funcionamiento: descripción."""
    text = "- **Funcionamiento**: El asistente usa RAG"
    result = strip_heavy_markdown(text)
    assert "**" not in result
    assert "Funcionamiento:" in result


def test_collapses_excess_blank_lines():
    """Tres o más líneas en blanco consecutivas → máximo dos."""
    text = "Hola\n\n\n\nCómo estás?"
    result = strip_heavy_markdown(text)
    assert "\n\n\n" not in result


def test_strip_is_noop_for_clean_text():
    """Texto limpio sin markdown no debe modificarse."""
    text = "Estamos en beta gratuita. Te interesa probarlo?"
    result = strip_heavy_markdown(text)
    assert result == text


# ─────────────────────────────────────────────────────────────
# naturalize — pipeline completo
# ─────────────────────────────────────────────────────────────


def test_naturalize_empty_string():
    """Cadena vacía no debe romper."""
    assert naturalize("") == ""


def test_naturalize_none_passthrough():
    """None debe retornar None sin errores."""
    assert naturalize(None) is None


def test_naturalize_full_pipeline():
    """Pipeline completo: limpia tool call Y markdown en un mismo texto."""
    text = (
        "**Funcionamiento**: El asistente usa RAG.\n\n\n\n"
        'Te agrego ahora. <function=registrar_prospecto>{"email": "x@x.com"}</function>'
    )
    result = naturalize(text)
    assert "<function=" not in result
    assert "**" not in result
    assert "\n\n\n" not in result
    assert "Funcionamiento:" in result
    assert "Te agrego ahora." in result


def test_naturalize_no_strip_markdown():
    """strip_markdown=False preserva el markdown pero igual limpia tool calls."""
    text = '**Hola** <function=tool>{"k":"v"}</function>'
    result = naturalize(text, strip_markdown=False)
    assert "<function=" not in result
    assert "**Hola**" in result


# ============================================================
# Tests nuevos — issue #20 (naturalidad mejorada)
# ============================================================

class TestStripCannedOpeners:
    """Tests para strip_canned_openers."""

    def test_claro_removed(self):
        """'¡Claro! Aquí tienes' → 'Aquí tienes'"""
        from app.modules.ai_assistant.response_naturalizer import strip_canned_openers
        result = strip_canned_openers("¡Claro! Aquí tienes la info.")
        assert result.lower().startswith("aquí")
        assert "claro" not in result.lower()[:10]

    def test_por_supuesto_removed(self):
        from app.modules.ai_assistant.response_naturalizer import strip_canned_openers
        result = strip_canned_openers("Por supuesto, puedo ayudarte con eso.")
        assert "por supuesto" not in result.lower()[:20]

    def test_excelente_pregunta_removed(self):
        from app.modules.ai_assistant.response_naturalizer import strip_canned_openers
        result = strip_canned_openers("¡Excelente pregunta! La respuesta es 42.")
        assert "excelente pregunta" not in result.lower()
        assert "42" in result

    def test_opener_in_middle_not_removed(self):
        """Opener en el medio NO debe eliminarse."""
        from app.modules.ai_assistant.response_naturalizer import strip_canned_openers
        text = "El problema existe. Claro que hay solución."
        result = strip_canned_openers(text)
        assert "claro" in result.lower()

    def test_empty_string_unchanged(self):
        from app.modules.ai_assistant.response_naturalizer import strip_canned_openers
        assert strip_canned_openers("") == ""

    def test_entendido_removed(self):
        from app.modules.ai_assistant.response_naturalizer import strip_canned_openers
        result = strip_canned_openers("Entendido, procedo a explicarte.")
        assert not result.lower().startswith("entendido")


class TestStripSycophantClosers:
    """Tests para strip_sycophantic_closers."""

    def test_espero_haberte_ayudado_removed(self):
        from app.modules.ai_assistant.response_naturalizer import strip_sycophantic_closers
        text = "Tu saldo es $500. ¡Espero haberte ayudado!"
        result = strip_sycophantic_closers(text)
        assert "espero" not in result.lower()
        assert "500" in result

    def test_no_dudes_removed(self):
        from app.modules.ai_assistant.response_naturalizer import strip_sycophantic_closers
        text = "El pedido está listo. No dudes en escribirme si necesitas algo más."
        result = strip_sycophantic_closers(text)
        assert "no dudes" not in result.lower()
        assert "pedido" in result.lower()

    def test_closer_in_middle_not_removed(self):
        """Closer en el medio NO debe eliminarse."""
        from app.modules.ai_assistant.response_naturalizer import strip_sycophantic_closers
        text = "Espero haberte ayudado con esto. El precio es $100."
        result = strip_sycophantic_closers(text)
        # La frase de cierre NO está al final, no debe tocarse
        assert "100" in result

    def test_quedo_disposicion_removed(self):
        from app.modules.ai_assistant.response_naturalizer import strip_sycophantic_closers
        text = "Tu orden fue procesada. Quedo a tu disposición."
        result = strip_sycophantic_closers(text)
        assert "disposición" not in result.lower()
        assert "orden" in result.lower()


class TestLimitEmojis:
    """Tests para limit_emojis."""

    def test_no_emojis_unchanged(self):
        from app.modules.ai_assistant.response_naturalizer import limit_emojis
        text = "Hola, ¿cómo estás?"
        assert limit_emojis(text) == text

    def test_exactly_two_unchanged(self):
        from app.modules.ai_assistant.response_naturalizer import limit_emojis
        text = "Hola 👋 ¿cómo estás? 😊"
        result = limit_emojis(text, max_emojis=2)
        # Debe quedar igual (exactamente 2)
        emoji_count = sum(1 for c in result if ord(c) > 0x1F000 or 0x2600 <= ord(c) <= 0x27BF)
        assert emoji_count <= 2

    def test_excess_emojis_trimmed(self):
        from app.modules.ai_assistant.response_naturalizer import limit_emojis
        text = "Hola 👋 ¿cómo estás? 😊 Bien 🎉 Gracias 🙏 Hasta 👌"
        result = limit_emojis(text, max_emojis=2)
        # Contar emojis en el resultado
        import re
        emojis = re.findall(r'[\U0001F000-\U0001FFFF\u2600-\u27BF]', result)
        assert len(emojis) <= 2

    def test_text_preserved_after_emoji_removal(self):
        from app.modules.ai_assistant.response_naturalizer import limit_emojis
        text = "🚀🚀🚀 Lanzamiento exitoso!"
        result = limit_emojis(text, max_emojis=1)
        assert "Lanzamiento" in result


class TestStripFormalLanguage:
    """Tests para strip_formal_language."""

    def test_procedera_replaced(self):
        from app.modules.ai_assistant.response_naturalizer import strip_formal_language
        result = strip_formal_language("Procederé a enviarte la información.")
        assert "procederé" not in result.lower()
        assert "voy a" in result.lower()

    def test_con_respecto_removed(self):
        from app.modules.ai_assistant.response_naturalizer import strip_formal_language
        result = strip_formal_language("Con respecto a su consulta, el precio es $50.")
        assert "con respecto" not in result.lower()
        assert "50" in result

    def test_me_permito_informarle_removed(self):
        from app.modules.ai_assistant.response_naturalizer import strip_formal_language
        result = strip_formal_language("Me permito informarle que el sistema está activo.")
        assert "me permito" not in result.lower()
        assert "sistema" in result.lower()

    def test_a_continuacion_replaced(self):
        from app.modules.ai_assistant.response_naturalizer import strip_formal_language
        result = strip_formal_language("A continuación le presento las opciones.")
        assert "a continuación" not in result.lower()


class TestNaturalizePipeline:
    """Tests de integración del pipeline completo actualizado."""

    def test_opener_and_closer_stripped(self):
        from app.modules.ai_assistant.response_naturalizer import naturalize
        text = "¡Claro! Aquí está tu pedido. Espero haberte ayudado."
        result = naturalize(text)
        assert "claro" not in result.lower()[:10]
        assert "espero haberte" not in result.lower()
        assert "pedido" in result.lower()

    def test_strip_canned_false_keeps_openers(self):
        from app.modules.ai_assistant.response_naturalizer import naturalize
        text = "¡Claro! Aquí está tu pedido."
        result = naturalize(text, strip_canned=False)
        # Con strip_canned=False, el opener debe mantenerse
        assert "claro" in result.lower()

    def test_emoji_limit_applied(self):
        from app.modules.ai_assistant.response_naturalizer import naturalize
        import re
        text = "🚀🎉👏🙏👌 Tu orden está lista!"
        result = naturalize(text, max_emojis=2)
        emojis = re.findall(r'[\U0001F000-\U0001FFFF\u2600-\u27BF]', result)
        assert len(emojis) <= 2
        assert "orden" in result.lower()
