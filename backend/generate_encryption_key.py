#!/usr/bin/env python3
"""
Script para generar una clave de encriptación para el módulo AI Assistant.

Esta clave se usa para encriptar de forma segura las API keys de los usuarios
en la base de datos.

Uso:
    python generate_encryption_key.py

La clave generada debe agregarse al archivo .env como AI_ENCRYPTION_KEY
"""

from cryptography.fernet import Fernet


def generate_key():
    """Genera una nueva clave de encriptación Fernet."""
    key = Fernet.generate_key()
    return key.decode()


def main():
    """Genera y muestra la clave de encriptación."""
    print("=" * 70)
    print("🔐 Generador de Clave de Encriptación para AI Assistant")
    print("=" * 70)
    print()

    encryption_key = generate_key()

    print("✅ Clave de encriptación generada exitosamente!")
    print()
    print("📋 Copia esta línea y agrégala a tu archivo .env del backend:")
    print()
    print("-" * 70)
    print(f"AI_ENCRYPTION_KEY={encryption_key}")
    print("-" * 70)
    print()
    print("⚠️  IMPORTANTE:")
    print("   • Guarda esta clave de forma segura")
    print("   • NO la compartas públicamente")
    print("   • NO la subas a git")
    print("   • Si la pierdes, tendrás que recrear todas las configuraciones")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
