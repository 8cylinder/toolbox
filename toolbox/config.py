import os
from enum import Enum
from pathlib import Path
from pprint import pp
from typing import Union, Optional

# import IPython; IPython.embed()

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


class _Hosting(BaseModel):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    username: Optional[str] = None
    password: Optional[str] = None
    note: Optional[str] = None


class _Urls(BaseModel):
    url: Optional[HttpUrl] = None
    admin_url: Optional[HttpUrl] = None
    username: Optional[str] = None
    password: Optional[str] = None
    note: Optional[str] = None


class _Mysql(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    db: Optional[str] = None
    hostname: Optional[str] = None


class _ControlPanel(BaseModel):
    url: Optional[HttpUrl] = None
    username: Optional[str] = None
    password: Optional[str] = None
    note: Optional[str] = None


class _SSH(BaseModel):
    username: str
    password: Optional[str] = None
    # server: Union[IPvAnyAddress, AnyUrl]
    server: str
    key: Optional[FilePath] = None
    port: Optional[int] = 22


class _Server(BaseModel):
    name: str
    root: os.PathLike
    group: Optional[str] = None
    user: Optional[str] = None
    exclude: Optional[list] = None
    note: Optional[str] = None
    ssh: list[_SSH] = None
    control_panels: list[_ControlPanel] = None
    hosting: list[_Hosting] = None
    urls: list[_Urls] = None
    mysql: list[_Mysql] = None


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
            root = info.data["root"]
            return root / v
        return None

    def get_server_by_name(self, name: str) -> Optional[_Server]:
        try:
            return [i for i in self.servers if i.name == name][0]
        except IndexError:
            raise IndexError(f"Server '{name}' does not exist.")


class _NoProject:
    in_project: bool = False


def load_yaml(config_file: os.PathLike) -> dict:
    """Load the yaml file, and handle any errors."""
    try:
        with open(config_file) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as ye:
        if hasattr(ye, "problem_mark"):
            msg = "There was an error while parsing the config file"
            if ye.context is not None:
                l.error(f"{msg}:\n{ye.problem_mark}\n{ye.problem} {ye.context}.")
            else:
                l.error(f"{msg}:\n{ye.problem_mark} {ye.problem}.")
        else:
            l.error("Something went wrong while parsing the yaml file.")

    return data


def find_config(config_file: os.PathLike, cur: os.PathLike) -> Union[bool, os.PathLike]:
    """Walk up the dir tree to find a config file"""
    if str(cur) == "/":
        return False
    elif str(config_file) in os.listdir(cur):
        config_file = Path(cur, config_file)
        return config_file
    else:
        cur = Path(cur / "..").resolve()
        return find_config(config_file, cur)


toolbox_config_file = find_config(Path(CONFIG_FILE), Path(os.curdir))
if toolbox_config_file:
    yaml_data = load_yaml(toolbox_config_file)
    project_root = toolbox_config_file.parent

    project = yaml_data["project"]

    servers = []
    for server_name in yaml_data.get("servers", []):

        sshes = []
        for ssh in yaml_data["servers"][server_name].get("ssh", []):
            if type(ssh) is dict:
                l.error("ssh fields must be a dictionary.", exit=True)
            ssh_fields = {
                "username": ssh["username"],
                "password": ssh.get("password"),
                "server": ssh["server"],
                "key": ssh.get("key"),
                "port": ssh.get("port"),
            }
            sshes.append(ssh_fields)

        control_panels = []
        for control_panel in yaml_data["servers"][server_name].get("control_panel", []):
            if type(control_panel) is dict:
                l.error("control_panel fields must be a dictionary.", exit=True)
            control_panel_fields = {
                "url": control_panel["url"],
                "username": control_panel.get("username"),
                "password": control_panel.get("password"),
                "note": control_panel.get("note"),
            }
            control_panels.append(control_panel_fields)

        hosting = []
        for host in yaml_data["servers"][server_name].get("hosting", []):
            if type(host) is dict:
                l.error("hosting fields must be a dictionary.", exit=True)
            hosting_fields = {
                "name": host.get("name"),
                "url": host.get("url"),
                "username": host.get("username"),
                "password": host.get("password"),
                "note": host.get("note"),
            }
            hosting.append(hosting_fields)

        urls = []
        for url in yaml_data["servers"][server_name].get("urls", []):
            if type(url) is dict:
                l.error("url fields must be a dictionary.", exit=True)
            url_fields = {
                "url": url.get("url"),
                "admin_url": url.get("admin_url"),
                "username": url.get("username"),
                "password": url.get("password"),
                "note": url.get("note"),
            }
            urls.append(url_fields)

        mysqls = []
        for mysql in yaml_data["servers"][server_name].get("mysql", []):
            if type(mysql) is dict:
                l.error("mysql fields must be a dictionary.", exit=True)
            mysql_fields = {
                "username": mysql.get("username"),
                "password": mysql.get("password"),
                "db": mysql.get("db"),
                "hostname": mysql.get("hostname"),
            }
            mysqls.append(mysql_fields)

        server = yaml_data["servers"][server_name]
        server_fields = {
            "name": server_name,
            "root": server["root"],
            "group": server.get("group"),
            "user": server.get("user"),
            "exclude": server.get("exclude"),
            "note": server.get("note"),
            "ssh": sshes,
            "mysql": mysqls,
            "hosting": hosting,
            "control_panels": control_panels,
            "urls": urls,
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
        l.error(e, exit=True)

else:
    project = _NoProject()

if __name__ == "__main__":
    pp(project)
    pp(project.raw)
