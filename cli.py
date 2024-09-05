#!/Users/brianlaw/code/hp/venv/bin/python3

import http.server
import json
import pathlib
import shutil
import subprocess
import typing
import urllib.request

import pyperclip
import rich.console
import rich.markup
import typer

HOST = "127.0.0.1"
PORT = 10046

app = typer.Typer(add_completion=False)
console = rich.console.Console(highlight=False)

cp_dir = pathlib.Path.home() / "code" / "cpp"
bkup_dir = pathlib.Path.home() / ".backup"

cp_file = cp_dir / "main.cpp"
cp_smpls = cp_dir / "samples"

def compile_(file: pathlib.Path, sanitizer: bool = True) -> bool:

    console.print()

    args = [
        f"-I{pathlib.Path.home() / '.lib'}", "-O2", "-Wall", "-Wextra", "-Wfloat-equal",
        "-Wl,-stack_size", "-Wl,0x10000000", "-o", f"{cp_dir}/a.out", "-std=c++17"
    ]

    if sanitizer:
        args.append("-fsanitize=address,undefined")

    with console.status(f"Compiling [bold]{file}[/]") as status:
        process = subprocess.run([str(shutil.which("clang++"))] + args + [str(file)])
        if process.returncode:
            status.stop()
            console.print()
            console.print(f"[red]Failed to compile [bold]{file}[/][/]")
            return False

    return True

@app.command()
def bkup(name: typing.Annotated[str, typer.Argument(help="File name")] = "_") -> None:
    """
    Backup `cp_file`.
    """

    bkup_file = bkup_dir / (name + ".cpp")

    console.print()

    if bkup_file.exists() and name != "_":
        replace = input(f"Replace {bkup_file}? (y/N) ")
        if replace != "y":
            return
        console.print()

    shutil.copy(cp_file, bkup_file)

    console.print(f"[bold]{cp_file}[/] -> [bold]{bkup_file}[/]")

@app.command()
def cc() -> None:
    """
    Parse data from Competitive Companion.
    """

    data = {}

    class Handler(http.server.BaseHTTPRequestHandler):

        def do_POST(self) -> None:

            nonlocal data

            data = json.load(self.rfile)

    console.print()

    with console.status("Waiting for data"):
        with http.server.HTTPServer((HOST, PORT), Handler) as server:
            server.handle_request()

    if data["batch"]["size"] > 1:
        console.print("[bold][red]Use problem parser.[/][/]")
        return

    console.print(f"[bold]{data['name']}[/]")
    console.print(f"[blue]{data['url']}[/]")
    console.print()

    def comb(*strs: str) -> str:

        return " ".join(strs)

    data_i = data["input"]
    data_o = data["output"]
    smpls = len(data["tests"])

    name_i = "stdin" if data_i["type"] == "stdin" else data_i["fileName"]
    name_o = "stdout" if data_o["type"] == "stdout" else data_o["fileName"]
    quote_i = "" if data_i["type"] == "stdin" else '"'
    quote_o = "" if data_o["type"] == "stdout" else '"'

    console.print(
        comb(
            f"[bold][cyan]{data['timeLimit']}[/][/] ms",
            "[bold]|[/]",
            f"[bold][cyan]{data['memoryLimit']}[/][/] mb",
            "[bold]|[/]",
            f"[bold][cyan]{smpls}[/][/] {'samples' if smpls != 1 else 'sample'}",
            "[bold]|[/]",
            f"{quote_i}{name_i}{quote_i} -> {quote_o}{name_o}{quote_o}",
            "[bold]|[/]",
            "batch" if not data["interactive"] else "interactive"
        )
    )

    if cp_smpls.exists():
        shutil.rmtree(cp_smpls)

    cp_smpls.mkdir()

    for i in range(smpls):
        (cp_smpls / f"ex_{i + 1}.in").write_text(data["tests"][i]["input"])
        (cp_smpls / f"ex_{i + 1}.ans").write_text(data["tests"][i]["output"])

@app.command()
def cmpl(
    file: typing.Annotated[str, typer.Argument(help="File to compile")] = "",
    sanitizer: typing.Annotated[bool, typer.Option(help="Use sanitizers")] = True
) -> None:
    """
    Compile a file.
    """

    cmpl_file = cp_file if file == "" else pathlib.Path.cwd() / file

    if compile_(cmpl_file, sanitizer):
        console.print(f"Compiled [bold]{cmpl_file}[/]")

@app.command()
def cp(file: typing.Annotated[str, typer.Argument(help="File to copy")] = "") -> None:
    """
    Copy a file.
    """

    copy_file = cp_file if file == "" else pathlib.Path.cwd() / file

    pyperclip.copy(copy_file.read_text())

    console.print()
    console.print(f"[bold]{copy_file}[/] -> clipboard")

@app.command()
def qoj(prob: typing.Annotated[int, typer.Argument(help="Problem id")]) -> None:
    """
    Download attachments from QOJ.
    """

    headers = {"User-Agent": "curl/8.1.2"}
    url = f"https://qoj.ac/download.php?type=problem&id={prob}"
    zip_file = cp_dir / "qoj.zip"

    console.print()
    console.print(f"[bold]QOJ {prob}[/]")
    console.print(f"[blue]https://qoj.ac/problem/{prob}[/]")

    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as response:
        zip_file.write_bytes(response.read())

    if cp_smpls.exists():
        shutil.rmtree(cp_smpls)

    shutil.unpack_archive(zip_file, cp_smpls)

    zip_file.unlink()

@app.command()
def rstr(name: typing.Annotated[str, typer.Argument(help="File name")] = "_") -> None:
    """
    Restore `cp_file`.
    """

    bkup_file = bkup_dir / (name + ".cpp")

    shutil.copy(bkup_file, cp_file)

    console.print()
    console.print(f"[bold]{bkup_file}[/] -> [bold]{cp_file}[/]")

@app.command()
def test(custom: typing.Annotated[bool, typer.Option(help="Use custom input")] = False) -> None:
    """
    Run cases.
    """

    if not compile_(cp_file):
        return

    files = []

    if not custom:
        files = cp_smpls.glob("*.in")
    else:
        files = [cp_dir / "custom.in"]

    files = sorted(files)

    for x in files:
        if len(files) > 1:
            console.print(f"[bold]{x.name}[/]")
        if subprocess.run([str(cp_dir / "a.out")], input=x.read_text(), text=True).returncode:
            break
        if x != files[-1]:
            console.print()

@app.command()
def tmpl(name: typing.Annotated[str, typer.Argument(help="Name of template")] = "single") -> None:
    """
    Copy template to `cp_file`.
    """

    tmpl_dir = pathlib.Path.home() / "code" / "library" / "template"
    view_dir = pathlib.Path.home() / ".local" / "state" / "nvim" / "view"
    view_glob = "~=+code=+cpp=+*="

    for x in cp_dir.iterdir():
        if x.is_file():
            x.unlink()
        else:
            shutil.rmtree(x)

    for x in view_dir.glob(view_glob):
        x.unlink()

    tmpl_file = tmpl_dir / f"{name}.cpp"

    shutil.copy(tmpl_file, cp_file)

    console.print()
    console.print(f"[bold]{tmpl_file}[/] -> [bold]{cp_file}[/]")

@app.command()
def view() -> None:
    """
    View sample outputs.
    """

    files = sorted(cp_smpls.glob("*.ans"))

    for x in files:
        console.print()
        if len(files) > 1:
            console.print(f"[bold]{x.name}[/]")
        console.print(x.read_text(), end="")

if __name__ == "__main__":
    app()
