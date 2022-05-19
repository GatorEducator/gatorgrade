"""Generate the code reference pages."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

for path in sorted(Path("gatorgrade").rglob("*.py")):
    module_path = path.relative_to("gatorgrade").with_suffix("")
    doc_path = path.relative_to("gatorgrade").with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = list(module_path.parts)

    if parts[-1] == "__init__":
        continue
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        fd.write(f"::: gatorgrade.{'.'.join(parts)}")

    mkdocs_gen_files.set_edit_path(full_doc_path, path)

# Generate navigation
with mkdocs_gen_files.open("reference/Summary.md", "w") as nav_file:
    # Generate code reference navigation
    nav_file.writelines(nav.build_literate_nav())
