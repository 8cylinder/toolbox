import os
from enum import Enum
from pathlib import Path
from pprint import pp
from typing import Union, Optional

import yaml
from pydantic import (
    BaseModel,
    ValidationError,
    FilePath,
    DirectoryPath,
    HttpUrl,
    AnyUrl,
    IPvAnyAddress,
    field_validator,
    ValidationInfo,
)

from toolbox.output import l

CONFIG_FILE = "toolbox.yaml"


class Action(Enum):
    PUT = "put"
    PULL = "pull"
    # DIFF = 'diff'


class _ControlPanel(BaseModel):
    url: HttpUrl
    username: Optional[str] = None
    password: Optional[str] = None
    note: Optional[str] = None


class _SSH(BaseModel):
    username: str
    password: Optional[str] = None
    server: Union[IPvAnyAddress, AnyUrl]
    key: Optional[FilePath] = None
    port: Optional[int] = 22


class _Server(BaseModel):
    name: str
    root: os.PathLike
    group: Optional[str] = None
    user: Optional[str] = None
    exclude: Optional[list] = None
    note: Optional[str] = None
    # ssh: list[_SSH] = None


class _Project(BaseModel):
    in_project: bool = True
    root: DirectoryPath
    name: str
    pulls_dir: Optional[os.PathLike] = None
    rsync_binary: Optional[dict] = None
    difftool: Optional[str] = None
    exclude: Optional[list] = None
    servers: list[_Server] = None
    # raw: dict

    @field_validator("pulls_dir")
    @classmethod
    def make_absolute(cls, v: str, info: ValidationInfo):
        if v is not None:
            project_root = info.data["root"]
            return project_root / v
        return None

    def get_server_by_name(self, name: str) -> Optional[_Server]:
        try:
            return [i for i in self.servers if i.name == name][0]
        except IndexError:
            raise IndexError(f"Server '{name}' does not exist.")


class _NoProject:
    in_project: bool = False


def load_yaml(config_file):
    config_file = find_config(config_file, os.curdir)
    if not config_file:
        return False

    try:
        with open(config_file) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        if hasattr(e, "problem_mark"):
            msg = "There was an error while parsing the config file"
            if e.context is not None:
                l.error(f"{msg}:\n{e.problem_mark}\n{e.problem} {e.context}.")
            else:
                l.error(f"{msg}:\n{e.problem_mark} {e.problem}.")
        else:
            l.error("Something went wrong while parsing the yaml file.")

    return config_file, data


def find_config(config_file, cur):
    """Walk up the dir tree to find a config file"""
    if cur == "/":
        return False
    elif str(config_file) in os.listdir(cur):
        config_file = Path(cur, config_file)
        return config_file
    else:
        cur = os.path.abspath(os.path.join(cur, ".."))
        return find_config(config_file, cur)


if config_info := load_yaml(CONFIG_FILE):
    config_file = config_info[0]
    project_root = config_file.parent
    yaml_data = config_info[1]

    project = yaml_data["project"]

    servers = []
    for server_name in yaml_data.get("servers", []):
        server = yaml_data["servers"][server_name]
        server_fields = {
            "name": server_name,
            "root": server["root"],
            "group": server.get("group"),
            "user": server.get("user"),
            "exclude": server.get("exclude"),
            "note": server.get("note"),
            "ssh": server.get("ssh"),
        }
        servers.append(server_fields)

    project_fields = {
        "name": project.get("name"),
        "pulls_dir": project.get("pulls_dir"),
        "root": project_root,
        "rsync_binary": project.get("rsync_binary"),
        "difftool": project.get("difftool"),
        "exclude": project.get("exclude"),
        "raw": yaml_data,
        "servers": servers,
    }

    try:
        project = _Project(**project_fields)
    except ValidationError as e:
        l.error(e)

else:
    project = _NoProject()


if __name__ == "__main__":
    pp(project)
    pp(project.raw)