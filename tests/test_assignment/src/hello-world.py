"""Define a test file."""


def greet(person: str) -> None:
    """Say hello to someone."""
    if person:
        print(f"Hello, {person}")  # noqa: T201


greet("world")
