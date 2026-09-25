#!/usr/bin/env python3
"""
Script de verificación del setup del AI Assistant.

Este script verifica que todo esté configurado correctamente antes de usar el AI Assistant.
"""

import os
import sys
from pathlib import Path


def print_header(title: str):
    """Imprime un header bonito."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_success(message: str):
    """Imprime mensaje de éxito."""
    print(f"✅ {message}")


def print_error(message: str):
    """Imprime mensaje de error."""
    print(f"❌ {message}")


def print_warning(message: str):
    """Imprime mensaje de advertencia."""
    print(f"⚠️  {message}")


def print_info(message: str):
    """Imprime mensaje informativo."""
    print(f"ℹ️  {message}")


def check_env_file():
    """Verifica que exista el archivo .env."""
    print_header("1. Verificando archivo .env")

    env_path = Path(".env")
    if not env_path.exists():
        print_error("Archivo .env no encontrado")
        print_info("Crea un archivo .env en la carpeta backend/")
        return False

    print_success("Archivo .env encontrado")
    return True


def check_encryption_key():
    """Verifica que AI_ENCRYPTION_KEY esté configurado."""
    print_header("2. Verificando AI_ENCRYPTION_KEY")

    # Intentar cargar desde .env
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        print_warning("python-dotenv no instalado, intentando sin él...")

    encryption_key = os.getenv("AI_ENCRYPTION_KEY")

    if not encryption_key:
        print_error("AI_ENCRYPTION_KEY no encontrada en .env")
        print_info("Ejecuta: python generate_encryption_key.py")
        print_info("Luego agrega la clave al archivo .env")
        return False

    print_success(f"AI_ENCRYPTION_KEY configurada: {encryption_key[:20]}...")
    return True


def check_dependencies():
    """Verifica que las dependencias estén instaladas."""
    print_header("3. Verificando dependencias")

    required_packages = [
        "langchain_core",
        "langchain_groq",
        "cryptography",
        "sqlalchemy",
        "fastapi",
        "alembic",
    ]

    all_installed = True

    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} instalado")
        except ImportError:
            print_error(f"{package} NO instalado")
            all_installed = False

    if not all_installed:
        print_info("\nPara instalar dependencias faltantes:")
        print_info("  uv sync")
        print_info("  # o")
        print_info("  pip install -r requirements.txt")

    return all_installed


def check_module_import():
    """Verifica que el módulo ai_assistant se pueda importar."""
    print_header("4. Verificando módulo AI Assistant")

    try:
        from app.modules.ai_assistant.router import router

        print_success("Módulo ai_assistant importado correctamente")
        print_success(f"Prefijo del router: {router.prefix}")
        print_success(f"Tags: {router.tags}")
        return True
    except ImportError as e:
        print_error(f"Error al importar módulo: {e}")
        return False
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        return False


def check_database_connection():
    """Verifica conexión a base de datos."""
    print_header("5. Verificando conexión a base de datos")

    try:
        from app.config.settings import settings

        database_url = settings.get_database_url

        # Ocultar password en la URL para mostrar
        if database_url:
            safe_url = (
                database_url.split("@")[0].split(":")[0]
                + ":****@"
                + database_url.split("@")[1]
                if "@" in database_url
                else "****"
            )
            print_success(f"DATABASE_URL configurada")
            print_info(f"  Host: {safe_url}")
        else:
            print_warning("DATABASE_URL no configurada")
            return False

        return True
    except Exception as e:
        print_error(f"Error al verificar conexión: {e}")
        return False


def check_migration_status():
    """Verifica el estado de las migraciones."""
    print_header("6. Verificando migraciones de Alembic")

    try:
        import subprocess

        result = subprocess.run(
            ["uv", "run", "alembic", "current"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if "e4f5g6h7i8j9" in output:
                print_success("Migración de AI Assistant aplicada")
                print_info(f"  {output}")
                return True
            else:
                print_warning("Migración de AI Assistant NO aplicada")
                print_info("Ejecuta: uv run alembic upgrade head")
                return False
        else:
            print_error("Error al verificar migraciones")
            print_info(result.stderr)
            return False
    except FileNotFoundError:
        print_error("Comando 'alembic' no encontrado")
        print_info("Ejecuta: uv sync")
        return False
    except Exception as e:
        print_error(f"Error al verificar migraciones: {e}")
        return False


def check_provider_availability():
    """Verifica que los proveedores de IA estén configurados."""
    print_header("7. Verificando proveedores de IA")

    try:
        from app.modules.ai_assistant.provider import UnifiedAIProvider

        providers = UnifiedAIProvider.get_available_providers()
        print_success(f"Proveedores disponibles: {', '.join(providers)}")

        for provider in providers:
            models = UnifiedAIProvider.get_available_models(provider)
            print_info(f"  {provider}: {len(models)} modelos")
            for model in models[:3]:  # Mostrar solo los primeros 3
                print(f"    - {model}")
            if len(models) > 3:
                print(f"    ... y {len(models) - 3} más")

        return True
    except Exception as e:
        print_error(f"Error al verificar proveedores: {e}")
        return False


def print_summary(checks: dict):
    """Imprime resumen de las verificaciones."""
    print_header("RESUMEN")

    total = len(checks)
    passed = sum(1 for v in checks.values() if v)

    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")

    print()
    print(f"Total: {passed}/{total} verificaciones pasadas")
    print()

    if passed == total:
        print_success("¡TODO ESTÁ LISTO! 🎉")
        print()
        print("Próximos pasos:")
        print("1. Inicia el backend: uv run uvicorn app.main:app --reload")
        print("2. Ve a: http://localhost:8000/docs")
        print("3. Busca la sección 'AI Assistant'")
        print("4. Obtén una API key de Groq: https://console.groq.com/")
        print("5. Crea tu primera configuración desde el frontend")
    else:
        print_error("HAY PROBLEMAS QUE RESOLVER")
        print()
        print("Revisa los errores arriba y corrígelos antes de continuar.")
        print()
        print("Ayuda:")
        print("- Si falta AI_ENCRYPTION_KEY: python generate_encryption_key.py")
        print("- Si faltan dependencias: uv sync")
        print("- Si falta migración: uv run alembic upgrade head")

    print()


def main():
    """Función principal."""
    print_header("🤖 Verificación de Setup - AI Assistant")

    # Verificar que estamos en el directorio correcto
    if not Path("app").exists():
        print_error("Este script debe ejecutarse desde la carpeta backend/")
        print_info("Ejecuta: cd backend && python verify_setup.py")
        sys.exit(1)

    # Ejecutar verificaciones
    checks = {
        "Archivo .env existe": check_env_file(),
        "AI_ENCRYPTION_KEY configurada": check_encryption_key(),
        "Dependencias instaladas": check_dependencies(),
        "Módulo AI Assistant importable": check_module_import(),
        "Conexión a base de datos": check_database_connection(),
        "Migraciones aplicadas": check_migration_status(),
        "Proveedores de IA disponibles": check_provider_availability(),
    }

    # Mostrar resumen
    print_summary(checks)

    # Exit code basado en resultados
    if all(checks.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
