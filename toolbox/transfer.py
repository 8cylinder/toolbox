import os
import sys
from pathlib import Path
from plumbum import local
from plumbum.cmd import rsync
from typing import List

from toolbox.config import project
from toolbox.config import Action
from toolbox.output import l


class Transfer:

    def __init__(self, real: bool, server_name: str, quiet: object = False) -> None:
        """Initialize the Transfer class.

        :param real: true to actually do the transfer, else just print the command.
        :param server_name: the name of the server to transfer to or from.
        :param quiet:
        """
        self.server = project.get_server_by_name(server_name)
        self.real = real
        self.quiet = quiet

    def transfer(
        self, action: Action, filename: os.PathLike, extra_flags: List = None
    ) -> None:
        """Transfer a file to or from a remote server.

        :param action: Action.PULL or Action.PUT
        :param filename:  the local file name to transfer
        :param extra_flags: additional flags to pass to rsync
        """
        remote = self._get_matching_remote(filename)
        self._rsync(action, filename, remote, extra_flags)

    def _get_matching_remote(self, filename: os.PathLike) -> os.PathLike:
        """Get the remote path that matches the local path."""
        remote = str(filename)
        # remove the local project root from the file
        remote = remote.replace(str(project.root.absolute()), ".")
        # add the server root
        try:
            remote = Path(self.server.root, remote)
        except TypeError:
            l.error(f"Server has no root ({self.server.servername}).")
        return remote

    def _rsync(
        self,
        action: Action,
        local_file: os.PathLike,
        remote: os.PathLike,
        extra_flags: List = None,
    ) -> None:

        args = []

        if not self.real:
            args += ["--dry-run"]

        ssh = self.server.ssh[0]
        if ssh.key:
            args += ["--rsh", f'"ssh -i {ssh.key}"']

        args += ["--links", "--compress", "--checksum", "--itemize-changes"]

        if extra_flags:
            args += extra_flags

        if ssh.port:
            # https://stackoverflow.com/a/4630407
            args += ["-e", f'"-p {ssh.port}"']

        # if transferring a dir, add the recursive flag, any excludes and
        # end the dirs with trailing slashes.
        if local_file.is_dir():
            args += ["--recursive"]

            project_excludes = [] if not project.exclude else project.exclude
            server_excludes = [] if not self.server.exclude else self.server.exclude
            if excludes := list(set(project_excludes + server_excludes)):
                excludes = ",".join(f'"{i}"' for i in excludes)
                args += ["--exclude", f"'{{{excludes}}}'"]

            local_file = os.path.join(
                local_file, ""
            )  # append a slash to the end of the path
            remote = os.path.join(remote, "")  # append a slash to the end of the path

        if action == Action.PUT and (s.group or s.user):
            # To have rsync change owner or group, the '--group' and
            # '--owner' flags have to be used as well as '--chown'
            # otherwise they will be ignored.
            args += [
                "--group" if self.server.group else "",
                "--owner" if self.server.user else "",
                "--chown",
                f"{self.server.group}:{self.server.user}",
            ]

        if action == Action.PUT.value:
            args += [local_file, f"{ssh.username}@{ssh.server}:{remote}"]
        else:
            args += [f"{ssh.username}@{ssh.server}:{remote}", local_file]

        rsync_cmd = "rsync"
        if custom_rsync_cmd := project.rsync_binary[sys.platform]:
            rsync_cmd = custom_rsync_cmd
        rsync = local[rsync_cmd]
        rsync = rsync[args]
        print(str(rsync))
