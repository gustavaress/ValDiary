"""Garante que todos os módulos do app ao menos importam (pega erros de sintaxe na interface,
que os outros testes não cobrem por não abrirem janelas)."""

import importlib
import pkgutil

import app


def test_todos_os_modulos_importam():
    for modulo in pkgutil.walk_packages(app.__path__, prefix="app."):
        importlib.import_module(modulo.name)
