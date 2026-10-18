"""Command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .advice import get_advice
from .config import Paths
from .model import ModelNotReady, PlantDiseaseModel

app = typer.Typer(add_completion=False, help="Offline crop-disease diagnosis for smallholder farmers.")
console = Console()


@app.callback(invoke_without_command=True)
def _root(
    version: bool = typer.Option(False, "--version", is_eager=True, help="Show the version and exit."),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()



def _load_model(model_path: Path | None) -> PlantDiseaseModel:
    try:
        return PlantDiseaseModel(model_path=model_path, config_path=None)
    except ModelNotReady as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc


@app.command()
def diagnose(
    image: Path = typer.Argument(..., exists=True, readable=True, help="Leaf photo (JPG/PNG)."),
    top_k: int = typer.Option(3, min=1, max=5, help="How many candidates to show."),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
    model_path: Path | None = typer.Option(None, help="Override the ONNX model path."),
) -> None:
    """Diagnose a leaf photo and print a treatment plan."""
    model = _load_model(model_path)
    predictions = model.predict(Image.open(image), top_k=top_k)
    best = predictions[0]
    advice = get_advice(best)

    if as_json:
        payload = {
            "predictions": [p.as_dict() for p in predictions],
            "advice": advice,
        }
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    table = Table(title=f"shamba · {image.name}", show_lines=False)
    table.add_column("Rank", justify="right")
    table.add_column("Crop")
    table.add_column("Disease")
    table.add_column("Confidence", justify="right")
    for rank, prediction in enumerate(predictions, start=1):
        table.add_row(
            str(rank),
            prediction.info.crop,
            prediction.info.disease,
            f"{prediction.confidence:.1%}",
        )
    console.print(table)

    if advice.get("confidence_note"):
        console.print(Panel(advice["confidence_note"], title="Low confidence", border_style="yellow"))

    console.print(Panel(advice["summary"], title=f"{advice['crop']} · {advice['disease']}", border_style="green"))
    for section, label in (
        ("act_now", "Do now"),
        ("organic", "Low-cost / organic"),
        ("chemical", "Chemical (only if needed)"),
        ("prevent", "Prevent next season"),
    ):
        items = advice.get(section) or []
        if items:
            console.print(f"\n[bold]{label}[/bold]")
            for item in items:
                console.print(f"  • {item}")
    if advice.get("escalate"):
        console.print(Panel(advice["escalate"], title="When to escalate", border_style="red"))
    console.print(f"\n[dim]{advice['disclaimer']}[/dim]")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind address."),
    port: int = typer.Option(8787, help="Port."),
) -> None:
    """Start the local web UI."""
    import uvicorn

    uvicorn.run("shamba.server:app", host=host, port=port, log_level="info")


@app.command()
def doctor() -> None:
    """Check that the model and runtime are ready."""
    import onnxruntime as ort

    paths = Paths.default()
    console.print(f"onnxruntime: [bold]{ort.__version__}[/bold]")
    console.print(f"model: {paths.model} ({'found' if paths.model.exists() else 'missing'})")
    console.print(f"config: {paths.config} ({'found' if paths.config.exists() else 'missing'})")
    if not paths.model.exists():
        console.print("\nRun: [bold]python scripts/download_model.py[/bold]")
        raise typer.Exit(code=1)
    model = PlantDiseaseModel()
    console.print(f"labels: [bold]{len(model.labels)}[/bold]")
    console.print("[green]ready[/green]")


if __name__ == "__main__":
    app()
