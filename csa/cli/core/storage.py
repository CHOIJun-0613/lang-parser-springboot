import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import click


def _candidate_mmdc_paths() -> Sequence[str]:
    """Mermaid CLI 실행 파일 후보 경로를 반환합니다."""
    candidates: List[str] = []

    env_path = os.getenv("MMDC_PATH")
    if env_path:
        candidates.append(env_path)

    for name in ("mmdc", "mmdc.cmd"):
        resolved = shutil.which(name)
        if resolved:
            candidates.append(resolved)

    return candidates


def convert_to_image(diagram_content: str, output_file: str, image_format: str, width: Optional[int] = None, height: Optional[int] = None) -> bool:
    """Mermaid 다이어그램을 이미지로 변환합니다."""
    mmdc_cmd = None
    for cmd in _candidate_mmdc_paths():
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True, timeout=5)
            mmdc_cmd = cmd
            break
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue

    if not mmdc_cmd:
        click.echo(
            "Error: Mermaid CLI (mmdc) not found. Install it via 'npm install -g @mermaid-js/mermaid-cli' "
            "or set MMDC_PATH to the executable."
        )
        return False

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".mmd", encoding="utf-8") as temp_file:
        temp_file_name = temp_file.name
        temp_file.write(diagram_content)

    try:
        cmd = [
            mmdc_cmd,
            "-i",
            temp_file_name,
            "-o",
            str(output_path),
            "-t",
            "forest",
            "-b",
            "transparent",
        ]

        if image_format:
            cmd.extend(["-f", image_format])
        if width:
            cmd.extend(["-w", str(width)])
        if height:
            cmd.extend(["-H", str(height)])

        subprocess.run(cmd, check=True)
        click.echo(f"Diagram saved as {output_file}")
        return True
    except subprocess.CalledProcessError as exc:
        click.echo(f"Error generating diagram: {exc}")
        return False
    finally:
        os.unlink(temp_file_name)


def _save_crud_matrix_as_excel(matrix: Iterable[dict], project_name: str, output_path: str) -> bool:
    """CRUD 매트릭스를 Excel 파일로 저장합니다."""
    try:
        import pandas as pd
        from openpyxl.styles import Alignment, Font, PatternFill

        df_data = []
        for row in matrix:
            df_data.append(
                {
                    "Package": row["package_name"] or "N/A",
                    "Class Name": row["class_name"],
                    "Method": row["method_name"],
                    "Schema": row["schema"] or "unknown",
                    "Table": row["table_name"],
                    "Operations": ", ".join(row["operations"]) if row["operations"] else "None",
                }
            )

        df = pd.DataFrame(df_data)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="CRUD Matrix", index=False)

            worksheet = writer.sheets["CRUD Matrix"]

            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")

            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                worksheet.column_dimensions[column_letter].width = min(max_length + 2, 50)

        return True

    except ImportError as exc:
        click.echo(f"Error: Required library not found: {exc}")
        click.echo("Please install required libraries: pip install pandas openpyxl")
        return False
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(f"Error creating Excel file: {exc}")
        return False


def _save_crud_matrix_as_image(matrix: Iterable[dict], project_name: str, output_path: str, image_format: str) -> bool:
    """CRUD 매트릭스를 Mermaid 다이어그램으로 변환해 이미지로 저장합니다."""
    try:
        diagram_lines = ["```mermaid", "classDiagram"]

        class_data = {}
        for row in matrix:
            class_name = row["class_name"]
            if class_name not in class_data:
                class_data[class_name] = {
                    "package_name": row["package_name"],
                    "methods": [],
                }

            schema = row["schema"] if row["schema"] and row["schema"] != "unknown" else None
            table_display = f"{schema}.{row['table_name']}" if schema else row["table_name"]
            operations = ", ".join(row["operations"]) if row["operations"] else "None"

            class_data[class_name]["methods"].append(
                {
                    "method_name": row["method_name"],
                    "table": table_display,
                    "operations": operations,
                }
            )

        for class_name, data in class_data.items():
            package_name = data["package_name"] or "N/A"
            clean_class_name = class_name.replace(".", "_").replace("-", "_").replace(" ", "_")

            diagram_lines.append(f"    class {clean_class_name} {{")
            diagram_lines.append(f"        <<{package_name}>>")

            methods = data["methods"][:10]
            for method_info in methods:
                method_line = (
                    f"        +{method_info['method_name']}() {method_info['table']} [{method_info['operations']}]"
                )
                diagram_lines.append(method_line)

            if len(data["methods"]) > 10:
                diagram_lines.append(f"        ... ({len(data['methods']) - 10} more)")

            diagram_lines.append("    }")

        table_nodes = set()
        for row in matrix:
            schema = row["schema"] if row["schema"] and row["schema"] != "unknown" else None
            table_display = f"{schema}.{row['table_name']}" if schema else row["table_name"]
            table_key = table_display.replace(".", "_").replace("-", "_").replace(" ", "_")

            if table_key not in table_nodes:
                diagram_lines.append(f"    class {table_key} {{")
                diagram_lines.append("        <<Database Table>>")
                diagram_lines.append(f"        {table_display}")
                diagram_lines.append("    }")
                table_nodes.add(table_key)

        for class_name, data in class_data.items():
            clean_class_name = class_name.replace(".", "_").replace("-", "_").replace(" ", "_")
            for method_info in data["methods"][:10]:
                schema = method_info["table"].split(".")[0] if "." in method_info["table"] else None
                table_name = method_info["table"].split(".")[-1]
                table_key = (
                    f"{schema}_{table_name}".replace(".", "_").replace("-", "_").replace(" ", "_")
                    if schema
                    else table_name.replace(".", "_").replace("-", "_").replace(" ", "_")
                )
                diagram_lines.append(f"    {clean_class_name} --> {table_key}")

        diagram_lines.append("```")
        diagram_content = "\n".join(diagram_lines)

        return convert_to_image(diagram_content, output_path, image_format, width=1600, height=1200)
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(f"Error creating diagram: {exc}")
        return False


__all__ = ["convert_to_image", "_save_crud_matrix_as_excel", "_save_crud_matrix_as_image"]
