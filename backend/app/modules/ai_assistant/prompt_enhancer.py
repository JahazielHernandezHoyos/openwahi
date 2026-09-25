"""
Prompt enhancement - mejora automáticamente malos prompts.
"""

from typing import Optional


class PromptEnhancer:
    """Mejora automáticamente el system prompt para mejores respuestas."""

    DEFAULT_ENHANCEMENTS = """
Directrices para responder bien por WhatsApp: sé claro y directo, mantén coherencia con el historial, usa un tono amigable pero profesional, responde en el idioma del usuario, y admite cuando no sabes algo en vez de inventar.
"""

    WHATSAPP_SPECIFIC = """
Esto es WhatsApp: mensajes cortos, conversacionales. Usa emojis con moderación (máximo 1-2 por mensaje). Evita listas largas y formato tipo email — una idea por mensaje es suficiente.
"""

    CONVERSATION_GUIDELINES = """
Recuerda lo que se dijo antes en la conversación y úsalo para dar respuestas consistentes y contextualizadas.
"""

    @classmethod
    def enhance_prompt(cls, original_prompt: Optional[str]) -> str:
        """
        Mejora un prompt original agregando mejores prácticas.

        Args:
            original_prompt: El prompt original del usuario (puede ser None o malo)

        Returns:
            Un prompt mejorado con mejores prácticas incorporadas
        """

        if not original_prompt or len(original_prompt.strip()) < 10:
            # Si el prompt es muy corto o vacío, usa uno genérico bueno
            base_prompt = (
                "Eres un asistente útil de WhatsApp. "
                "Tu objetivo es ayudar al usuario de la mejor manera posible."
            )
        else:
            base_prompt = original_prompt.strip()

        # Agregar mejoras
        enhanced = f"""{base_prompt}

{cls.DEFAULT_ENHANCEMENTS}

{cls.WHATSAPP_SPECIFIC}

{cls.CONVERSATION_GUIDELINES}
"""

        return enhanced

    @classmethod
    def should_enhance(cls, prompt: Optional[str]) -> bool:
        """
        Determina si un prompt necesita mejora.

        Args:
            prompt: El prompt a evaluar

        Returns:
            True si el prompt necesita mejora
        """
        if not prompt:
            return True

        # Si el prompt es muy corto, probablemente necesita mejora
        if len(prompt.strip()) < 20:
            return True

        # Si no tiene estructura (sin puntos, muy simple)
        if "." not in prompt and "\n" not in prompt:
            return True

        # Si ya tiene las palabras clave de mejora, no necesita más
        enhancement_keywords = [
            "directrices",
            "guidelines",
            "claridad",
            "contexto",
            "tono",
        ]
        prompt_lower = prompt.lower()
        if any(keyword in prompt_lower for keyword in enhancement_keywords):
            return False

        return False  # Por defecto, no mejorar si parece bien estructurado

    @classmethod
    def create_default_prompt(cls) -> str:
        """
        Crea un prompt por defecto genérico pero efectivo.

        Returns:
            Un prompt por defecto bien estructurado
        """
        return cls.enhance_prompt(
            "Eres un asistente útil y amigable de WhatsApp. "
            "Ayuda al usuario con sus preguntas y necesidades."
        )

    @classmethod
    def create_customer_service_prompt(cls) -> str:
        """
        Crea un prompt específico para servicio al cliente.

        Returns:
            Un prompt optimizado para servicio al cliente
        """
        base = (
            "Eres un agente de servicio al cliente profesional y amable. "
            "Tu objetivo es ayudar a los clientes a resolver sus problemas y responder sus preguntas. "
            "Mantén un tono cortés, empático y resolutivo."
        )
        return cls.enhance_prompt(base)

    @classmethod
    def create_sales_prompt(cls) -> str:
        """
        Crea un prompt específico para ventas.

        Returns:
            Un prompt optimizado para ventas
        """
        base = (
            "Eres un asesor de ventas profesional y consultivo. "
            "Tu objetivo es entender las necesidades del cliente y ofrecer soluciones apropiadas. "
            "No seas agresivo, enfócate en construir relaciones y proporcionar valor."
        )
        return cls.enhance_prompt(base)

    @classmethod
    def create_technical_support_prompt(cls) -> str:
        """
        Crea un prompt específico para soporte técnico.

        Returns:
            Un prompt optimizado para soporte técnico
        """
        base = (
            "Eres un especialista en soporte técnico paciente y claro. "
            "Tu objetivo es ayudar a los usuarios a resolver problemas técnicos. "
            "Explica las cosas de forma simple, paso a paso, sin usar jerga innecesaria."
        )
        return cls.enhance_prompt(base)
