import os
import glob
from pathlib import Path

def consolidate_folder(source_folder: str, output_file: str, skip_init: bool = True, extension: str = ".py") -> None:
    """
    Consolidates all Python files from a source folder into a single text file,
    adding a header comment with the original file path.

    Args:
        source_folder (str): Path to the folder to consolidate (e.g., "models").
        output_file (str): Path where the consolidated file will be saved.
        skip_init (bool): If True, skips __init__.py files.
        extension (str): File extension to look for (default ".py").
    """
    # Normalize paths
    source_path = Path(source_folder)
    print("Source path ", source_path)
    if not source_path.exists() or not source_path.is_dir():
        raise ValueError(f"La carpeta '{source_folder}' no existe o no es un directorio.")

    # Collect all files with the given extension recursively
    pattern = f"**/*{extension}"
    files = sorted(source_path.glob(pattern))  # sorted for consistency

    if not files:
        print(f"No se encontraron archivos {extension} en {source_folder}")
        return

    with open(output_file, "w", encoding="utf-8") as out_f:
        # Write a header comment
        out_f.write(f"# ==================================================\n")
        out_f.write(f"# Archivos consolidados desde: {source_folder}\n")
        out_f.write(f"# Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out_f.write(f"# Total de archivos: {len(files)}\n")
        out_f.write(f"# ==================================================\n\n")

        for file_path in files:
            # Skip __init__.py if requested
            if skip_init and file_path.name == "__init__.py":
                continue

            # Write a separator and the file origin
            relative_path = file_path.relative_to(source_path.parent)  # relative to the parent of source_folder
            out_f.write(f"\n# ==================================================\n")
            out_f.write(f"# ARCHIVO: {relative_path}\n")
            out_f.write(f"# ==================================================\n\n")

            try:
                with open(file_path, "r", encoding="utf-8") as in_f:
                    content = in_f.read()
                    out_f.write(content)
                    # Ensure there's a newline after each file
                    if not content.endswith("\n"):
                        out_f.write("\n")
            except Exception as e:
                out_f.write(f"# ERROR al leer el archivo: {e}\n")

    print(f"Consolidación completada. Archivo generado: {output_file}")

# Ejemplo de uso:
if __name__ == "__main__":
    from datetime import datetime  # for timestamp
    #directorio = os.()
    #print("Mi directorio ", directorio)
    # Consolidar modelos
    consolidate_folder("FASTAPI_IV/models", "consolidated_models.py")
 
    # Consolidar esquemas
    consolidate_folder("FASTAPI_IV/schemas", "consolidated_schemas.py")

    # Consolidar routers
    consolidate_folder("FASTAPI_IV/routers", "consolidated_routers.py")