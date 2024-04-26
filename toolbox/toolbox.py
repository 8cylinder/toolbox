from pprint import pprint as pp

import click

from toolbox.config import Action
from toolbox.config import project
from toolbox.output import l
from toolbox.transfer import Transfer
from pathlib import Path

__version__ = "2.0.0"


def get_servers(ctx, args, incomplete):
    servers = [i.name for i in config.servers() if i.name.startswith(incomplete)]
    return servers


class NaturalOrderGroup(click.Group):
    """Display commands sorted by order in file.

    When using -h, display the commands in the order
    they are in the file where they are defined.

    https://github.com/pallets/click/issues/513
    """

    def list_commands(self, ctx):
        return self.commands.keys()


CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}


# fmt: off
@click.group(context_settings=CONTEXT_SETTINGS, cls=NaturalOrderGroup)
@click.option("-s", "--suppress-commands", is_flag=True,
    help="Don't display the bash commands used.")
@click.version_option()
# fmt: on
def toolbox(suppress_commands):
    """🛠  Tools to manage projects.

    Dev commands:

    \b
    poetry run tb --help
    """
    # print(">>>", project.in_project)
    #
    # l.cmd("This is a command message.")
    # l.error("This is an error message.")
    # x = {
    #     "a": 111111111,
    #     "b": [11111, 222222, 333333],
    #     "casdf asfdadfds": {"d adf adf afd asdf": 4, "e": 5},
    # }
    # l.warning(x)


# --------------------------------- DB ---------------------------------
# fmt: off
@toolbox.command("db", context_settings=CONTEXT_SETTINGS)
@click.argument("action", type=click.Choice([i.value for i in Action]))
# @click.argument('server', type=click.Choice(get_server_choices()), shell_complete=get_servers)
@click.argument("server", type=click.STRING, shell_complete=get_servers)
@click.argument("sql-gz", type=click.Path(exists=True), required=False)
@click.option("--tag", "-t", type=click.STRING,
    help="Add a tag to the generated filename when pulling.")
@click.option("-q", "--quiet", count=True,
    help="-q: Output only the filename, -qq: output nothing.")
@click.option("--real", "-r", is_flag=True,
    help="Run the command for real.")
@click.pass_context
# fmt: on
def database(action, sql_gz, server, quiet, real, tag):
    """Overwrite a db with a gzipped sql file.

    \b
    ACTION: pull or put.
    SERVER: server name (defined in toolbox.yaml).
    SQL-GZ: if put, gzipped sql file to upload.

    When pulling, a gzipped file name is created using the project
    name, the server name, the date and time.  It is created in the
    pulls_dir.  eg:

    \b
    pulls_dir/projectname-servername-20-01-01_01-01-01.sql.gz
    """

    if not project.in_project:
        l.error("Not in a project.", exit=True)
    else:
        l.info(f"Project: {project.name}")

    # pp(project.model_dump())

    print("-" * 80)

    try:
        x = project.get_server_by_name("prod")
    except IndexError as e:
        l.error(e, exit=True)
    except TypeError as e:
        l.error(e, exit=True)

    print(x.name, x.root)

    # db = DB(real=real, quiet=quiet)
    #
    # if action == Action.PULL.value:
    #     db.pull(server, tag=tag)
    # elif action == Action.PUT.value:
    #     if not sql_gz:
    #         ui.error('When action is "put", SQL-GZ is required.')
    #     db.put(server, sql_gz)


# ------------------------------- Files -------------------------------
# fmt: off
@toolbox.command('file', context_settings=CONTEXT_SETTINGS)
@click.argument('action', type=click.Choice([str(i.value) for i in Action]))
@click.argument('server', shell_complete=get_servers)
@click.argument('filename', type=click.Path(), required=False)
@click.option('--real', '-r', is_flag=True)
@click.option("-q", "--quiet", count=True,
    help="-q: Output only the filename, -qq: output nothing.")
@click.option('--extra-flags',
    help='extra flags to pass to rsync.')
# fmt: on
def files(action, filename, server, real, quiet, extra_flags):
    """Send files to and fro.
    Push or pull a single file or directory from a remote server.
    \b
    ACTION: pull or put
    SERVER: server name, if not specified sink will use the default server.
    FILENAME: file/dir to be transferred."""

    if not project.in_project:
        l.error("Not in a project.", exit=True)
    else:
        l.info(f"Project: {project.name}")

    # if it's a put action and the local file does not exist, error out
    if filename and action == Action.PUT.value and not os.path.exists(filename):
        l.error(f"File '{filename}' does not exist.", exit=True)

    if filename:
        f = Path(os.path.abspath(filename))
    else:
        f = Path(project.root)

    transfer = Transfer(real, server_name=server, quiet=quiet)
    transfer.transfer(action, f, extra_flags)

    # if action == Action.PULL.value:
    #     xfer.pull(f, extra_flags)
    # elif action == Action.PUT.value:
    #     xfer.put(f, extra_flags)
